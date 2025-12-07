"""Return request and ledger persistence."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.returns import LedgerEntry, ReturnRequest, ReturnRequestItem, ReturnRequestPhoto
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class ReturnsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_return(self, row: ReturnRequest) -> ReturnRequest:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_item(self, row: ReturnRequestItem) -> ReturnRequestItem:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_photo(self, row: ReturnRequestPhoto) -> ReturnRequestPhoto:
        self.session.add(row)
        await self.session.flush()
        return row

    async def save_return(self, row: ReturnRequest) -> ReturnRequest:
        await self.session.flush()
        return row

    async def get_return(self, rma_id: UUID) -> ReturnRequest | None:
        result = await self.session.execute(
            select(ReturnRequest)
            .options(
                selectinload(ReturnRequest.items),
                selectinload(ReturnRequest.photos),
            )
            .where(ReturnRequest.id == rma_id)
        )
        return result.scalar_one_or_none()

    async def require_return(self, rma_id: UUID) -> ReturnRequest:
        row = await self.get_return(rma_id)
        if row is None:
            raise ProblemError(404, "Not found", "Return request not found.", PROBLEM_NOT_FOUND)
        return row

    async def list_for_order(self, order_id: UUID) -> list[ReturnRequest]:
        result = await self.session.execute(
            select(ReturnRequest)
            .options(
                selectinload(ReturnRequest.items),
                selectinload(ReturnRequest.photos),
            )
            .where(ReturnRequest.order_id == order_id)
            .order_by(ReturnRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_admin(self, *, status: str = "pending") -> list[ReturnRequest]:
        stmt = (
            select(ReturnRequest)
            .options(
                selectinload(ReturnRequest.items),
                selectinload(ReturnRequest.photos),
            )
            .order_by(ReturnRequest.created_at.asc())
        )
        if status != "all":
            stmt = stmt.where(ReturnRequest.status == status)
        result = await self.session.execute(stmt.limit(100))
        return list(result.scalars().all())

    async def has_open_return(self, order_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(ReturnRequest)
            .where(
                ReturnRequest.order_id == order_id,
                ReturnRequest.status == "pending",
            )
        )
        return int(result.scalar_one() or 0) > 0

    async def approved_qty_for_item(self, order_item_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(ReturnRequestItem.qty), 0)).where(
                ReturnRequestItem.order_item_id == order_item_id,
                ReturnRequestItem.return_request_id.in_(
                    select(ReturnRequest.id).where(
                        ReturnRequest.status.in_(("pending", "approved"))
                    )
                ),
            )
        )
        return int(result.scalar_one() or 0)

    async def add_ledger(self, row: LedgerEntry) -> LedgerEntry:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_ledger(self, order_id: UUID) -> list[LedgerEntry]:
        result = await self.session.execute(
            select(LedgerEntry)
            .where(LedgerEntry.order_id == order_id)
            .order_by(LedgerEntry.created_at.asc())
        )
        return list(result.scalars().all())

    async def has_sale_entry(self, order_id: UUID) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(LedgerEntry)
            .where(LedgerEntry.order_id == order_id, LedgerEntry.entry_type == "sale")
        )
        return int(result.scalar_one() or 0) > 0

    async def refunded_poisha(self, order_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount_poisha), 0)).where(
                LedgerEntry.order_id == order_id,
                LedgerEntry.entry_type.in_(("refund", "shipping_refund")),
            )
        )
        return int(result.scalar_one() or 0)
