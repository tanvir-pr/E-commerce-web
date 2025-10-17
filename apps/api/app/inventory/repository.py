"""Stock batch and movement persistence."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import asc, func, nulls_last, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import StockBatch, StockMovement
from app.models.product import ProductVariant
from app.problems import PROBLEM_CONFLICT, PROBLEM_NOT_FOUND, ProblemError


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def require_variant(self, variant_id: UUID) -> ProductVariant:
        result = await self.session.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.product))
            .where(ProductVariant.id == variant_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ProblemError(404, "Not found", "Variant not found.", PROBLEM_NOT_FOUND)
        return row

    async def require_batch(self, batch_id: UUID) -> StockBatch:
        result = await self.session.execute(
            select(StockBatch).where(StockBatch.id == batch_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ProblemError(404, "Not found", "Stock batch not found.", PROBLEM_NOT_FOUND)
        return row

    async def list_batches(
        self, variant_id: UUID, *, include_empty: bool = False
    ) -> list[StockBatch]:
        stmt = select(StockBatch).where(StockBatch.variant_id == variant_id)
        if not include_empty:
            stmt = stmt.where(StockBatch.qty_on_hand > 0)
        stmt = stmt.order_by(
            nulls_last(asc(StockBatch.expires_on)),
            asc(StockBatch.received_at),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_batch(self, batch: StockBatch) -> StockBatch:
        self.session.add(batch)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A batch with that lot code already exists for this SKU.",
                PROBLEM_CONFLICT,
            ) from exc
        return batch

    async def save_batch(self, batch: StockBatch) -> StockBatch:
        batch.updated_at = datetime.now(UTC)
        await self.session.flush()
        return batch

    async def add_movement(self, movement: StockMovement) -> StockMovement:
        self.session.add(movement)
        await self.session.flush()
        return movement

    async def list_movements(
        self, variant_id: UUID, *, limit: int = 50
    ) -> list[StockMovement]:
        result = await self.session.execute(
            select(StockMovement)
            .where(StockMovement.variant_id == variant_id)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def qty_on_hand(self, variant_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(StockBatch.qty_on_hand), 0)).where(
                StockBatch.variant_id == variant_id
            )
        )
        return int(result.scalar_one())

    async def nearest_expiry(self, variant_id: UUID) -> date | None:
        result = await self.session.execute(
            select(func.min(StockBatch.expires_on)).where(
                StockBatch.variant_id == variant_id,
                StockBatch.qty_on_hand > 0,
                StockBatch.expires_on.is_not(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_variants(self) -> list[ProductVariant]:
        result = await self.session.execute(
            select(ProductVariant)
            .options(selectinload(ProductVariant.product))
            .order_by(ProductVariant.sku.asc())
        )
        return list(result.scalars().unique().all())
