"""Dashboard date range and CSV export."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.orders.service import OrderService
from app.problems import PROBLEM_VALIDATION, ProblemError


class FakeRepo:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def period_stats(self, *, since: datetime, until: datetime | None = None):
        self.calls.append(("period", since, until))
        return {
            "revenue_poisha": 10000,
            "order_count": 2,
            "cancelled_count": 0,
            "cod_sold_count": 1,
            "placed_count": 2,
        }

    async def count_by_status(self) -> dict[str, int]:
        return {"confirmed": 1}

    async def count_overdue_confirmed(self, *, cutoff: datetime) -> int:
        return 0

    async def top_products(
        self, *, since: datetime, until: datetime | None = None, limit: int = 5
    ):
        self.calls.append(("top", since, until, limit))
        return [(uuid4(), "serum", "Serum", 3, 9000)]

    async def list_admin(
        self,
        *,
        status: str,
        limit: int = 100,
        since: datetime | None = None,
        until: datetime | None = None,
    ):
        self.calls.append(("list", status, since, until))
        now = datetime.now(UTC)
        return [
            SimpleNamespace(
                id=uuid4(),
                order_number="ORD-1",
                status="confirmed",
                total_poisha=5000,
                currency="BDT",
                payment_method="cod",
                items=[SimpleNamespace()],
                placed_at=now,
                user=SimpleNamespace(email="buyer@example.com"),
                shipping_zone_slug="dhaka",
                courier_name=None,
                tracking_number=None,
                packed_at=None,
                confirmed_at=now,
                shipped_at=None,
            )
        ]


class FakeInventory:
    async def low_stock(self, *, threshold: int):
        return SimpleNamespace(items=[])


class FakeCarts:
    async def admin_list(self, *, status: str):
        return SimpleNamespace(items=[])


@pytest.mark.asyncio
async def test_dashboard_custom_range() -> None:
    service = OrderService(SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeRepo()
    service.repo = repo  # type: ignore[assignment]
    service.inventory = FakeInventory()  # type: ignore[assignment]
    service.carts = FakeCarts()  # type: ignore[assignment]
    service.settings = SimpleNamespace(
        inventory_low_stock_threshold=10,
        inventory_near_expiry_days=60,
        fulfilment_sla_hours=48,
    )

    start = datetime(2026, 11, 1, tzinfo=UTC)
    end = datetime(2026, 11, 15, tzinfo=UTC)
    out = await service.dashboard_metrics(range_from=start, range_to=end)
    assert out.custom is not None
    assert out.custom.order_count == 2
    assert out.range_from == start
    assert any(c[0] == "period" and c[1] == start and c[2] == end for c in repo.calls)


@pytest.mark.asyncio
async def test_dashboard_rejects_inverted_range() -> None:
    service = OrderService(SimpleNamespace())  # type: ignore[arg-type]
    service.repo = FakeRepo()  # type: ignore[assignment]
    service.inventory = FakeInventory()  # type: ignore[assignment]
    service.carts = FakeCarts()  # type: ignore[assignment]
    service.settings = SimpleNamespace(
        inventory_low_stock_threshold=10,
        inventory_near_expiry_days=60,
        fulfilment_sla_hours=48,
    )
    now = datetime.now(UTC)
    with pytest.raises(ProblemError) as exc:
        await service.dashboard_metrics(
            range_from=now, range_to=now - timedelta(days=1)
        )
    assert exc.value.type_ == PROBLEM_VALIDATION


@pytest.mark.asyncio
async def test_metrics_and_orders_csv() -> None:
    service = OrderService(SimpleNamespace())  # type: ignore[arg-type]
    service.repo = FakeRepo()  # type: ignore[assignment]
    service.inventory = FakeInventory()  # type: ignore[assignment]
    service.carts = FakeCarts()  # type: ignore[assignment]
    service.settings = SimpleNamespace(
        inventory_low_stock_threshold=10,
        inventory_near_expiry_days=60,
        fulfilment_sla_hours=48,
    )

    metrics_csv = await service.metrics_csv()
    assert "revenue_poisha" in metrics_csv
    assert "serum" in metrics_csv

    from app.orders.schemas import OrderSummaryOut

    def _summary(row: object, *, include_email: bool = False) -> OrderSummaryOut:  # noqa: ANN001
        return OrderSummaryOut(
            id=uuid4(),
            order_number="ORD-1",
            status="confirmed",
            total_poisha=5000,
            currency="BDT",
            item_count=1,
            placed_at=datetime.now(UTC),
            user_email="buyer@example.com" if include_email else None,
            payment_method="cod",
        )

    service._summary = _summary  # type: ignore[method-assign]
    orders_csv = await service.orders_csv(status="all")
    assert "ORD-1" in orders_csv
    assert "buyer@example.com" in orders_csv
