"""Order state machine allow-list."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.orders.constants import ALLOWED_TRANSITIONS
from app.orders.schemas import TransitionIn
from app.orders.service import OrderService
from app.problems import ProblemError


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeInventory:
    def __init__(self) -> None:
        self.released = 0
        self.consumed = 0

    async def reserve_for_order(self, *_args: object, **_kwargs: object) -> int:
        return 0

    async def release_for_order(self, *_args: object, **_kwargs: object) -> int:
        self.released += 1
        return 1

    async def consume_for_order(self, *_args: object, **_kwargs: object) -> int:
        self.consumed += 1
        return 1


class FakeRepo:
    def __init__(self, order: SimpleNamespace) -> None:
        self.order = order
        self.events: list[SimpleNamespace] = []

    async def require(self, _order_id: object) -> SimpleNamespace:
        return self.order

    async def add_event(self, event: object) -> object:
        self.events.append(event)  # type: ignore[arg-type]
        return event

    async def save(self, order: SimpleNamespace) -> SimpleNamespace:
        return order

    async def list_expired_pending(
        self, *, now: datetime, limit: int = 100
    ) -> list[SimpleNamespace]:
        _ = limit
        if (
            self.order.status == "pending_payment"
            and self.order.reservation_expires_at is not None
            and self.order.reservation_expires_at <= now
        ):
            return [self.order]
        return []


def _order(status: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        order_number="SOL-TEST-000001",
        user_id=uuid4(),
        status=status,
        currency="BDT",
        merchandise_subtotal_poisha=10000,
        shipping_poisha=6000,
        total_poisha=16000,
        shipping_zone_slug="dhaka-metro",
        shipping_zone_name="Dhaka metro",
        total_weight_grams=100,
        shipping_address={
            "line1": "12 Road",
            "city": "Dhaka",
            "district": "Dhaka",
            "country": "BD",
        },
        payment_method="cod",
        payment_status="pending",
        reservation_expires_at=None,
        placed_at=datetime.now(UTC),
        confirmed_at=None,
        shipped_at=None,
        delivered_at=None,
        cancelled_at=None,
        items=[],
        events=[],
        user=None,
    )


def _service(order: SimpleNamespace) -> tuple[OrderService, FakeInventory]:
    service = OrderService(FakeSession())  # type: ignore[arg-type]
    service.repo = FakeRepo(order)  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    inventory = FakeInventory()
    service.inventory = inventory  # type: ignore[assignment]
    return service, inventory


@pytest.mark.asyncio
async def test_pending_payment_can_confirm_or_cancel() -> None:
    assert ALLOWED_TRANSITIONS["pending_payment"] == frozenset({"confirmed", "cancelled"})
    order = _order("pending_payment")
    order.reservation_expires_at = datetime.now(UTC)
    service, inventory = _service(order)
    out = await service.admin_transition(
        order.id,
        TransitionIn(to_status="confirmed", note="COD accepted"),
        actor_user_id=uuid4(),
    )
    assert out.status == "confirmed"
    assert order.confirmed_at is not None
    assert order.reservation_expires_at is None
    assert inventory.released == 0


@pytest.mark.asyncio
async def test_rejects_illegal_transition() -> None:
    order = _order("pending_payment")
    service, _inventory = _service(order)
    with pytest.raises(ProblemError):
        await service.admin_transition(
            order.id,
            TransitionIn(to_status="shipped"),
            actor_user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_shipped_to_delivered() -> None:
    order = _order("shipped")
    service, _inventory = _service(order)
    out = await service.admin_transition(
        order.id,
        TransitionIn(to_status="delivered"),
        actor_user_id=uuid4(),
    )
    assert out.status == "delivered"
    assert order.delivered_at is not None


@pytest.mark.asyncio
async def test_cancel_releases_reservation() -> None:
    order = _order("pending_payment")
    service, inventory = _service(order)
    out = await service.admin_transition(
        order.id,
        TransitionIn(to_status="cancelled"),
        actor_user_id=uuid4(),
    )
    assert out.status == "cancelled"
    assert inventory.released == 1
    assert order.reservation_expires_at is None


@pytest.mark.asyncio
async def test_ship_consumes_reservation() -> None:
    order = _order("confirmed")
    service, inventory = _service(order)
    out = await service.admin_transition(
        order.id,
        TransitionIn(to_status="shipped"),
        actor_user_id=uuid4(),
    )
    assert out.status == "shipped"
    assert inventory.consumed == 1


@pytest.mark.asyncio
async def test_expire_reservations_cancels_pending() -> None:
    order = _order("pending_payment")
    order.reservation_expires_at = datetime.now(UTC)
    service, inventory = _service(order)
    count = await service.expire_reservations()
    assert count == 1
    assert order.status == "cancelled"
    assert inventory.released == 1
