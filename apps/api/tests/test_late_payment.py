"""Late payment after cancel: re-reserve or auto-refund (Part 25)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.config import Settings
from app.payments.service import PaymentService
from app.problems import ProblemError


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://u:p@localhost/db",
        redis_url="redis://localhost:6379/0",
        public_web_url="http://localhost:3001",
        payment_gateway_mode="sandbox",
        bkash_app_secret="bk-secret",
        sslcommerz_store_password="ssl-secret",
        jwt_secret="jwt",
    )


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeInventory:
    def __init__(self, *, allow_reserve: bool = True) -> None:
        self.allow_reserve = allow_reserve
        self.reserved = 0

    async def reserve_for_order(self, *_a: object, **_k: object) -> int:
        if not self.allow_reserve:
            raise ProblemError(
                422,
                "Validation error",
                "Insufficient stock to reserve SKU-1: need 1, available 0.",
                "validation",
            )
        self.reserved += 1
        return 1

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
        self.order = order
        return order


class FakeEventRepo:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], SimpleNamespace] = {}

    async def get_by_gateway_event(
        self, *, gateway: str, gateway_event_id: str
    ) -> SimpleNamespace | None:
        return self.rows.get((gateway, gateway_event_id))

    async def list_by_status(self, status: str, *, limit: int = 100) -> list[SimpleNamespace]:
        rows = [r for r in self.rows.values() if r.status == status]
        return rows[:limit]

    async def try_insert(self, **kwargs: object) -> SimpleNamespace | None:
        key = (str(kwargs["gateway"]), str(kwargs["gateway_event_id"]))
        if key in self.rows:
            return None
        row = SimpleNamespace(**kwargs)
        self.rows[key] = row
        return row

    async def save(self, event: SimpleNamespace) -> SimpleNamespace:
        key = (str(event.gateway), str(event.gateway_event_id))
        self.rows[key] = event
        return event


def _cancelled_order(*, method: str = "bkash") -> SimpleNamespace:
    user_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        order_number="SOL-LATE-0001",
        user_id=user_id,
        status="cancelled",
        currency="BDT",
        merchandise_subtotal_poisha=10000,
        shipping_poisha=6000,
        total_poisha=16000,
        shipping_zone_slug="dhaka-metro",
        shipping_zone_name="Dhaka metro",
        total_weight_grams=100,
        shipping_address={"line1": "12 Road", "city": "Dhaka", "country": "BD"},
        payment_method=method,
        payment_status="cancelled",
        reservation_expires_at=None,
        courier_name=None,
        tracking_number=None,
        packed_at=None,
        placed_at=datetime.now(UTC) - timedelta(hours=1),
        confirmed_at=None,
        shipped_at=None,
        delivered_at=None,
        delivery_failed_at=None,
        returned_at=None,
        cancelled_at=datetime.now(UTC),
        items=[
            SimpleNamespace(
                id=uuid4(),
                variant_id=uuid4(),
                product_id=uuid4(),
                product_slug="serum",
                product_name="Serum",
                sku="SER-1",
                size_label="30ml",
                shade_name=None,
                spf=None,
                qty=1,
                unit_price_poisha=10000,
                line_total_poisha=10000,
            )
        ],
        events=[],
        user=SimpleNamespace(id=user_id, email="buyer@example.com"),
    )


def _service(
    order: SimpleNamespace, *, allow_reserve: bool = True
) -> tuple[PaymentService, FakeEventRepo, FakeInventory]:
    service = PaymentService(FakeSession(), settings=_settings())  # type: ignore[arg-type]
    service.orders.repo = FakeOrderRepo(order)  # type: ignore[assignment]
    service.orders.audit = FakeAudit()  # type: ignore[assignment]
    inventory = FakeInventory(allow_reserve=allow_reserve)
    service.orders.inventory = inventory  # type: ignore[assignment]
    events = FakeEventRepo()
    service.events = events  # type: ignore[assignment]
    return service, events, inventory


@pytest.mark.asyncio
async def test_late_payment_re_reserves_cancelled_order() -> None:
    order = _cancelled_order()
    service, events, inventory = _service(order, allow_reserve=True)
    out = await service.process_return(
        "bkash",
        {
            "paymentID": "BK-LATE-1",
            "order_id": str(order.id),
            "amount": "160.00",
            "transactionStatus": "Completed",
        },
    )
    assert out.status == "confirmed"
    assert out.payment_status == "paid"
    assert out.meta.get("late_payment") == "re_reserved"
    assert inventory.reserved == 1
    assert order.status == "confirmed"
    assert list(events.rows.values())[0].status == "processed"


@pytest.mark.asyncio
async def test_late_payment_refunds_when_stock_gone() -> None:
    order = _cancelled_order()
    service, events, inventory = _service(order, allow_reserve=False)
    out = await service.process_return(
        "bkash",
        {
            "paymentID": "BK-LATE-2",
            "order_id": str(order.id),
            "amount": "160.00",
            "transactionStatus": "Completed",
        },
    )
    assert out.status == "cancelled"
    assert out.payment_status == "refunded"
    assert out.meta.get("late_payment") == "refunded"
    assert inventory.reserved == 0
    assert list(events.rows.values())[0].status == "refunded"


@pytest.mark.asyncio
async def test_late_payment_event_idempotent() -> None:
    order = _cancelled_order()
    service, events, _inv = _service(order, allow_reserve=True)
    payload = {
        "paymentID": "BK-LATE-3",
        "order_id": str(order.id),
        "amount": "160.00",
        "transactionStatus": "Completed",
    }
    await service.process_return("bkash", payload)
    again = await service.process_return("bkash", payload)
    assert again.meta.get("idempotent") is True
    assert len(events.rows) == 1


@pytest.mark.asyncio
async def test_reconcile_refund_needed() -> None:
    order = _cancelled_order()
    service, events, _inv = _service(order, allow_reserve=False)
    event = SimpleNamespace(
        id=uuid4(),
        gateway="bkash",
        gateway_event_id="BK-ORPHAN-1",
        order_id=order.id,
        provider_ref="BK-ORPHAN-1",
        amount_poisha=16000,
        status="refund_needed",
        source="webhook",
        raw_payload={},
    )
    events.rows[("bkash", "BK-ORPHAN-1")] = event
    order.payment_status = "refund_needed"
    result = await service.reconcile_late_payments()
    assert result["refunded"] == 1
    assert order.payment_status == "refunded"
    assert event.status == "refunded"
