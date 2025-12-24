"""Signed webhooks, gateway_event_id dedupe, session-less return (Part 24)."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.config import Settings
from app.payments.service import PaymentService
from app.payments.signatures import verify_webhook_signature, webhook_signature
from app.problems import ProblemError


def _settings(**kwargs: object) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "redis_url": "redis://localhost:6379/0",
        "public_web_url": "http://localhost:3001",
        "payment_gateway_mode": "sandbox",
        "bkash_app_secret": "bk-secret",
        "sslcommerz_store_password": "ssl-secret",
        "jwt_secret": "jwt",
    }
    base.update(kwargs)
    return Settings(**base)  # type: ignore[arg-type]


def test_webhook_signature_roundtrip() -> None:
    body = b'{"paymentID":"BK1","status":"Completed"}'
    sig = webhook_signature(body, secret="bk-secret")
    assert sig.startswith("sha256=")
    assert verify_webhook_signature(body, sig, secret="bk-secret")
    assert not verify_webhook_signature(body, sig, secret="other")
    assert not verify_webhook_signature(body, None, secret="bk-secret")


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeInventory:
    async def release_for_order(self, *_a: object, **_k: object) -> int:
        return 0

    async def consume_for_order(self, *_a: object, **_k: object) -> int:
        return 0


class FakeOrderRepo:
    def __init__(self, order: SimpleNamespace) -> None:
        self.order = order

    async def require(self, order_id: object) -> SimpleNamespace:
        if self.order.id != order_id:
            raise ProblemError(404, "Not found", "Order not found.", "x")
        return self.order

    async def require_owned(self, order_id: object, user_id: object) -> SimpleNamespace:
        if self.order.id != order_id or self.order.user_id != user_id:
            raise ProblemError(404, "Not found", "Order not found.", "x")
        return self.order

    async def add_event(self, event: object) -> object:
        if getattr(event, "id", None) is None:
            event.id = uuid4()  # type: ignore[attr-defined]
        if getattr(event, "created_at", None) is None:
            event.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
        self.order.events.append(event)
        return event

    async def save(self, order: SimpleNamespace) -> SimpleNamespace:
        return order


class FakeEventRepo:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], SimpleNamespace] = {}

    async def get_by_gateway_event(
        self, *, gateway: str, gateway_event_id: str
    ) -> SimpleNamespace | None:
        return self.rows.get((gateway, gateway_event_id))

    async def list_by_status(self, status: str, *, limit: int = 100) -> list[SimpleNamespace]:
        return [r for r in self.rows.values() if r.status == status][:limit]

    async def try_insert(self, **kwargs: object) -> SimpleNamespace | None:
        key = (str(kwargs["gateway"]), str(kwargs["gateway_event_id"]))
        if key in self.rows:
            return None
        row = SimpleNamespace(**kwargs)
        self.rows[key] = row
        return row

    async def save(self, event: SimpleNamespace) -> SimpleNamespace:
        self.rows[(str(event.gateway), str(event.gateway_event_id))] = event
        return event


def _pending_order(*, method: str = "bkash") -> SimpleNamespace:
    user_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        order_number="SOL-WH-0001",
        user_id=user_id,
        status="pending_payment",
        currency="BDT",
        merchandise_subtotal_poisha=10000,
        shipping_poisha=6000,
        total_poisha=16000,
        shipping_zone_slug="dhaka-metro",
        shipping_zone_name="Dhaka metro",
        total_weight_grams=100,
        shipping_address={"line1": "12 Road", "city": "Dhaka", "country": "BD"},
        payment_method=method,
        payment_status="pending",
        reservation_expires_at=datetime.now(UTC) + timedelta(minutes=10),
        courier_name=None,
        tracking_number=None,
        packed_at=None,
        placed_at=datetime.now(UTC),
        confirmed_at=None,
        shipped_at=None,
        delivered_at=None,
        delivery_failed_at=None,
        returned_at=None,
        cancelled_at=None,
        items=[],
        events=[],
        user=SimpleNamespace(id=user_id, email="buyer@example.com"),
    )


def _service(order: SimpleNamespace) -> tuple[PaymentService, FakeEventRepo]:
    service = PaymentService(FakeSession(), settings=_settings())  # type: ignore[arg-type]
    service.orders.repo = FakeOrderRepo(order)  # type: ignore[assignment]
    service.orders.audit = FakeAudit()  # type: ignore[assignment]
    service.orders.inventory = FakeInventory()  # type: ignore[assignment]
    events = FakeEventRepo()
    service.events = events  # type: ignore[assignment]

    async def _always_email(_user_id: object) -> bool:
        return True

    service.orders.wants_order_emails = _always_email  # type: ignore[method-assign]
    return service, events


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature() -> None:
    order = _pending_order()
    service, _events = _service(order)
    body = json.dumps(
        {
            "paymentID": "BK1",
            "order_id": str(order.id),
            "amount": "160.00",
            "transactionStatus": "Completed",
        }
    ).encode()
    with pytest.raises(ProblemError) as exc:
        await service.process_webhook(
            "bkash",
            body=body,
            signature_header="sha256=deadbeef",
            payload=json.loads(body),
        )
    assert exc.value.status == 403
    assert order.status == "pending_payment"


@pytest.mark.asyncio
async def test_webhook_confirms_and_dedupes_by_event_id() -> None:
    order = _pending_order()
    service, events = _service(order)
    payload = {
        "paymentID": "BK-EVENT-1",
        "order_id": str(order.id),
        "amount": "160.00",
        "transactionStatus": "Completed",
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    sig = webhook_signature(body, secret="bk-secret")
    first = await service.process_webhook(
        "bkash", body=body, signature_header=sig, payload=payload
    )
    assert first.status == "confirmed"
    assert first.payment_status == "paid"
    assert order.status == "confirmed"
    assert ("bkash", "BK-EVENT-1") in events.rows

    # Replay must not error; stays idempotent.
    second = await service.process_webhook(
        "bkash", body=body, signature_header=sig, payload=payload
    )
    assert second.meta.get("idempotent") is True
    assert len(events.rows) == 1


@pytest.mark.asyncio
async def test_session_less_return_confirms() -> None:
    order = _pending_order(method="sslcommerz")
    service, events = _service(order)
    started = await service.start_pay(order.id, user_id=order.user_id)
    token = started.redirect_url.split("token=")[1].split("&")[0]
    out = await service.process_return(
        "sslcommerz", {"token": token, "status": "VALID"}
    )
    assert out.status == "confirmed"
    assert out.payment_status == "paid"
    assert out.meta.get("source") == "return"
    assert len(events.rows) == 1
