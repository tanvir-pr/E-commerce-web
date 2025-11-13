"""Order persistence."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
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
