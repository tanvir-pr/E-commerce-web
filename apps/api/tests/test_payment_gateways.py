"""bKash / SSLCommerz sandbox adapters and payment service (Part 23)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.config import Settings
from app.payments.adapters.bkash import SandboxBkashGateway
from app.payments.adapters.sslcommerz import SandboxSslcommerzGateway
from app.payments.service import PaymentService
from app.payments.tokens import sign_payment_token, verify_payment_token
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


def test_sign_and_verify_token_roundtrip() -> None:
    token = sign_payment_token({"order_id": "x", "n": 1}, secret="s")
    assert verify_payment_token(token, secret="s") == {"order_id": "x", "n": 1}
    assert verify_payment_token(token, secret="other") is None
    assert verify_payment_token("not.a.token.x", secret="s") is None


def test_bkash_initiate_and_token_validate() -> None:
    gw = SandboxBkashGateway(_settings())
    order_id = uuid4()
    started = gw.initiate(
        order_id=order_id,
        order_number="SOL-1",
        amount_poisha=16000,
        currency="BDT",
        return_url="http://localhost:3001/en/orders/1",
        cancel_url="http://localhost:3001/en/orders/1",
    )
    assert "method=bkash" in started.redirect_url
    assert "token=" in started.redirect_url
    assert started.provider_ref.startswith("BK")
    token = started.redirect_url.split("token=")[1].split("&")[0]
    ok = gw.validate({"token": token, "status": "Completed"})
    assert ok.ok
    assert ok.order_id == order_id
    assert ok.amount_poisha == 16000
    assert ok.provider_ref == started.provider_ref
    bad = gw.validate({"token": token, "status": "Failed"})
    assert not bad.ok


def test_sslcommerz_classic_payload() -> None:
    gw = SandboxSslcommerzGateway(_settings())
    order_id = uuid4()
    result = gw.validate(
        {
            "val_id": "VAL123",
            "order_id": str(order_id),
            "tran_id": "SOL-2",
            "amount": "160.00",
            "status": "VALID",
        }
    )
    assert result.ok
    assert result.order_id == order_id
    assert result.amount_poisha == 16000
    assert result.provider_ref == "VAL123"


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeInventory:
    async def reserve_for_order(self, *_a: object, **_k: object) -> int:
        return 0

    async def release_for_order(self, *_a: object, **_k: object) -> int:
        return 0

    async def consume_for_order(self, *_a: object, **_k: object) -> int:
        return 0


class FakeRepo:
    def __init__(self, order: SimpleNamespace) -> None:
        self.order = order

    async def require_owned(self, order_id: object, user_id: object) -> SimpleNamespace:
        if self.order.id != order_id or self.order.user_id != user_id:
            raise ProblemError(404, "Not found", "Order not found.", "x")
        return self.order

    async def require(self, _order_id: object) -> SimpleNamespace:
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


def _pending_order(*, method: str = "bkash") -> SimpleNamespace:
    user_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        order_number="SOL-PAY-0001",
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


def _payment_service(order: SimpleNamespace) -> PaymentService:
    settings = _settings()
    service = PaymentService(FakeSession(), settings=settings)  # type: ignore[arg-type]
    service.orders.repo = FakeRepo(order)  # type: ignore[assignment]
    service.orders.audit = FakeAudit()  # type: ignore[assignment]
    service.orders.inventory = FakeInventory()  # type: ignore[assignment]
    return service


@pytest.mark.asyncio
async def test_start_pay_rejects_cod() -> None:
    order = _pending_order(method="cod")
    service = _payment_service(order)
    with pytest.raises(ProblemError) as exc:
        await service.start_pay(order.id, user_id=order.user_id)
    assert exc.value.status == 422


@pytest.mark.asyncio
async def test_start_and_validate_confirms_paid() -> None:
    order = _pending_order(method="bkash")
    service = _payment_service(order)
    started = await service.start_pay(order.id, user_id=order.user_id)
    assert started.method == "bkash"
    assert started.sandbox is True
    token = started.redirect_url.split("token=")[1].split("&")[0]
    out = await service.validate(
        "bkash",
        {"token": token, "status": "Completed"},
        user_id=order.user_id,
    )
    assert out.status == "confirmed"
    assert out.payment_status == "paid"
    assert order.status == "confirmed"
    assert order.payment_status == "paid"
    assert order.reservation_expires_at is None


@pytest.mark.asyncio
async def test_validate_rejects_amount_mismatch() -> None:
    order = _pending_order(method="sslcommerz")
    service = _payment_service(order)
    with pytest.raises(ProblemError) as exc:
        await service.validate(
            "sslcommerz",
            {
                "val_id": "V1",
                "order_id": str(order.id),
                "amount": "1.00",
                "status": "VALID",
            },
            user_id=order.user_id,
        )
    assert "amount" in (exc.value.detail or "").lower()


@pytest.mark.asyncio
async def test_validate_idempotent_when_already_paid() -> None:
    order = _pending_order(method="bkash")
    service = _payment_service(order)
    started = await service.start_pay(order.id, user_id=order.user_id)
    token = started.redirect_url.split("token=")[1].split("&")[0]
    await service.validate(
        "bkash", {"token": token, "status": "Completed"}, user_id=order.user_id
    )
    again = await service.validate(
        "bkash", {"token": token, "status": "Completed"}, user_id=order.user_id
    )
    assert again.meta.get("idempotent") is True
