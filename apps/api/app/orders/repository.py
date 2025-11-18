"""Order persistence."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.models.order import Order, OrderEvent, OrderItem
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _options(self) -> Sequence[ExecutableOption]:
        return (
            selectinload(Order.items),
            selectinload(Order.events),
            selectinload(Order.user),
        )

    async def get_by_id(self, order_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .options(*self._options())
            .where(Order.id == order_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def require(self, order_id: UUID) -> Order:
        row = await self.get_by_id(order_id)
        if row is None:
            raise ProblemError(404, "Not found", "Order not found.", PROBLEM_NOT_FOUND)
        return row

    async def require_owned(self, order_id: UUID, user_id: UUID) -> Order:
        row = await self.require(order_id)
        if row.user_id != user_id:
            raise ProblemError(404, "Not found", "Order not found.", PROBLEM_NOT_FOUND)
        return row

    async def list_for_user(self, user_id: UUID, *, limit: int = 50) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .options(*self._options())
            .where(Order.user_id == user_id)
            .order_by(Order.placed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def list_admin(self, *, status: str, limit: int = 100) -> list[Order]:
        stmt = (
            select(Order)
            .options(*self._options())
            .order_by(Order.placed_at.desc())
            .limit(limit)
        )
        if status != "all":
            stmt = stmt.where(Order.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def add(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.flush()
        return await self.require(order.id)

    async def add_item(self, item: OrderItem) -> OrderItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def add_event(self, event: OrderEvent) -> OrderEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def save(self, order: Order) -> Order:
        await self.session.flush()
        return await self.require(order.id)

    async def list_expired_pending(self, *, now: datetime, limit: int = 100) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .options(*self._options())
            .where(
                Order.status == "pending_payment",
                Order.reservation_expires_at.is_not(None),
                Order.reservation_expires_at <= now,
            )
            .order_by(Order.reservation_expires_at.asc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def count_by_status(self) -> dict[str, int]:
        result = await self.session.execute(
            select(Order.status, func.count()).group_by(Order.status)
        )
        return {str(status): int(count) for status, count in result.all()}

    async def period_stats(self, *, since: datetime) -> dict[str, float | int]:
        sold = Order.status.in_(("confirmed", "shipped", "delivered"))
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.sum(case((sold, Order.total_poisha), else_=0)),
                    0,
                ),
                func.count().filter(sold),
                func.count().filter(Order.status == "cancelled"),
                func.count().filter(
                    sold,
                    Order.payment_method == "cod",
                ),
                func.count(),
            ).where(Order.placed_at >= since)
        )
        revenue, sold_count, cancelled, cod_sold, total = result.one()
        return {
            "revenue_poisha": int(revenue or 0),
            "order_count": int(sold_count or 0),
            "cancelled_count": int(cancelled or 0),
            "cod_sold_count": int(cod_sold or 0),
            "placed_count": int(total or 0),
        }

    async def count_overdue_confirmed(self, *, cutoff: datetime) -> int:
        result = await self.session.execute(
            select(func.count()).where(
                Order.status == "confirmed",
                Order.confirmed_at.is_not(None),
                Order.confirmed_at <= cutoff,
            )
        )
        return int(result.scalar_one())

    async def top_products(
        self, *, since: datetime, limit: int = 5
    ) -> list[tuple[UUID, str, str, int, int]]:
        result = await self.session.execute(
            select(
                OrderItem.product_id,
                OrderItem.product_slug,
                OrderItem.product_name,
                func.sum(OrderItem.qty),
                func.sum(OrderItem.line_total_poisha),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.placed_at >= since,
                Order.status.in_(("confirmed", "shipped", "delivered")),
            )
            .group_by(OrderItem.product_id, OrderItem.product_slug, OrderItem.product_name)
            .order_by(func.sum(OrderItem.line_total_poisha).desc())
            .limit(limit)
        )
        return [
            (row[0], row[1], row[2], int(row[3] or 0), int(row[4] or 0))
            for row in result.all()
        ]
