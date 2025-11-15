"""Inventory use cases: receipt, adjust, FEFO issue/preview, reservations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.inventory.constants import MOVEMENT_REASONS
from app.inventory.repository import InventoryRepository
from app.inventory.schemas import (
    AdjustmentIn,
    FefoAllocationLine,
    FefoIssueIn,
    FefoPreviewOut,
    LowStockItemOut,
    LowStockListOut,
    ReceiptIn,
    StockBatchOut,
    StockMovementListOut,
    StockMovementOut,
    VariantStockOut,
)
from app.models.inventory import StockBatch, StockMovement
from app.models.order import Order, OrderItem
from app.models.reservation import StockReservationAllocation
from app.problems import PROBLEM_VALIDATION, ProblemError


class InventoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InventoryRepository(session)
        self.audit = AuditService(session)

    async def get_variant_stock(
        self, variant_id: UUID, *, include_empty: bool = False
    ) -> VariantStockOut:
        variant = await self.repo.require_variant(variant_id)
        batches = await self.repo.list_batches(variant_id, include_empty=include_empty)
        qty = await self.repo.qty_on_hand(variant_id)
        return VariantStockOut(
            variant_id=variant.id,
            sku=variant.sku,
            product_id=variant.product_id,
            qty_on_hand=qty,
            batch_count=len([b for b in batches if b.qty_on_hand > 0]),
            nearest_expiry=await self.repo.nearest_expiry(variant_id),
            batches=[_batch_out(b) for b in batches],
        )

    async def receive(self, body: ReceiptIn, *, actor_user_id: UUID) -> VariantStockOut:
        variant = await self.repo.require_variant(body.variant_id)
        lot = body.lot_code.strip() if body.lot_code else None
        batch = StockBatch(
            variant_id=variant.id,
            lot_code=lot or None,
            qty_on_hand=body.qty,
            expires_on=body.expires_on,
            received_at=datetime.now(UTC),
            note=body.note,
        )
        saved = await self.repo.add_batch(batch)
        await self.repo.add_movement(
            StockMovement(
                variant_id=variant.id,
                batch_id=saved.id,
                qty_delta=body.qty,
                reason="receipt",
                note=body.note,
                actor_user_id=actor_user_id,
            )
        )
        await self.audit.record(
            action="inventory.receipt",
            actor_user_id=actor_user_id,
            subject_type="stock_batch",
            subject_id=str(saved.id),
            meta={"variant_id": str(variant.id), "qty": body.qty},
        )
        return await self.get_variant_stock(variant.id, include_empty=True)

    async def adjust(self, body: AdjustmentIn, *, actor_user_id: UUID) -> VariantStockOut:
        if body.qty_delta == 0:
            raise ProblemError(
                422,
                "Validation error",
                "qty_delta must not be zero.",
                PROBLEM_VALIDATION,
            )
        batch = await self.repo.require_batch(body.batch_id)
        new_qty = batch.qty_on_hand + body.qty_delta
        if new_qty < 0:
            raise ProblemError(
                422,
                "Validation error",
                "Adjustment would make batch quantity negative.",
                PROBLEM_VALIDATION,
            )
        batch.qty_on_hand = new_qty
        await self.repo.save_batch(batch)
        reason = "adjustment_in" if body.qty_delta > 0 else "adjustment_out"
        await self.repo.add_movement(
            StockMovement(
                variant_id=batch.variant_id,
                batch_id=batch.id,
                qty_delta=body.qty_delta,
                reason=reason,
                note=body.note,
                actor_user_id=actor_user_id,
            )
        )
        await self.audit.record(
            action="inventory.adjustment",
            actor_user_id=actor_user_id,
            subject_type="stock_batch",
            subject_id=str(batch.id),
            meta={"qty_delta": body.qty_delta},
        )
        return await self.get_variant_stock(batch.variant_id, include_empty=True)

    async def preview_fefo(self, variant_id: UUID, qty: int) -> FefoPreviewOut:
        if qty <= 0:
            raise ProblemError(
                422,
                "Validation error",
                "qty must be greater than zero.",
                PROBLEM_VALIDATION,
            )
        await self.repo.require_variant(variant_id)
        lines, allocated = await self._plan_fefo(variant_id, qty)
        return FefoPreviewOut(
            variant_id=variant_id,
            requested_qty=qty,
            allocated_qty=allocated,
            shortfall=max(0, qty - allocated),
            lines=lines,
        )

    async def issue_fefo(self, body: FefoIssueIn, *, actor_user_id: UUID) -> FefoPreviewOut:
        reason = body.reason or "fefo_issue"
        if reason not in MOVEMENT_REASONS:
            raise ProblemError(
                422,
                "Validation error",
                f"reason must be one of: {', '.join(sorted(MOVEMENT_REASONS))}",
                PROBLEM_VALIDATION,
            )
        await self.repo.require_variant(body.variant_id)
        lines, allocated = await self._plan_fefo(body.variant_id, body.qty)
        if allocated < body.qty:
            raise ProblemError(
                422,
                "Validation error",
                f"Insufficient stock: need {body.qty}, available {allocated}.",
                PROBLEM_VALIDATION,
            )
        for line in lines:
            batch = await self.repo.require_batch(line.batch_id)
            batch.qty_on_hand -= line.qty
            await self.repo.save_batch(batch)
            await self.repo.add_movement(
                StockMovement(
                    variant_id=body.variant_id,
                    batch_id=batch.id,
                    qty_delta=-line.qty,
                    reason=reason,
                    note=body.note,
                    actor_user_id=actor_user_id,
                )
            )
        await self.audit.record(
            action="inventory.fefo_issue",
            actor_user_id=actor_user_id,
            subject_type="product_variant",
            subject_id=str(body.variant_id),
            meta={"qty": body.qty, "reason": reason},
        )
        return FefoPreviewOut(
            variant_id=body.variant_id,
            requested_qty=body.qty,
            allocated_qty=allocated,
            shortfall=0,
            lines=lines,
        )

    async def list_movements(
        self, variant_id: UUID, *, limit: int = 50
    ) -> StockMovementListOut:
        await self.repo.require_variant(variant_id)
        rows = await self.repo.list_movements(variant_id, limit=limit)
        return StockMovementListOut(items=[_movement_out(row) for row in rows])

    async def low_stock(self, *, threshold: int) -> LowStockListOut:
        if threshold < 0:
            raise ProblemError(
                422,
                "Validation error",
                "threshold must be >= 0.",
                PROBLEM_VALIDATION,
            )
        items: list[LowStockItemOut] = []
        for variant in await self.repo.list_variants():
            qty = await self.repo.qty_on_hand(variant.id)
            if qty > threshold:
                continue
            product = variant.product
            items.append(
                LowStockItemOut(
                    variant_id=variant.id,
                    sku=variant.sku,
                    product_id=variant.product_id,
                    product_slug=product.slug if product else None,
                    qty_on_hand=qty,
                    nearest_expiry=await self.repo.nearest_expiry(variant.id),
                )
            )
        return LowStockListOut(items=items, threshold=threshold)

    async def reserve_for_order(
        self,
        order: Order,
        items: list[OrderItem],
        *,
        actor_user_id: UUID | None,
    ) -> int:
        """FEFO-deduct on-hand for tracked SKUs. Returns reserved unit count.

        Soft/untracked SKUs (no positive on-hand) are skipped. Partial shortfall
        on a tracked SKU raises and rolls back with the request transaction.
        """
        # Lock variants in stable order to reduce deadlocks.
        lines = sorted(items, key=lambda item: str(item.variant_id))
        reserved_units = 0
        for item in lines:
            on_hand = await self.repo.qty_on_hand(item.variant_id)
            if on_hand <= 0:
                continue
            plan, allocated = await self._plan_fefo(
                item.variant_id, item.qty, for_update=True
            )
            if allocated < item.qty:
                raise ProblemError(
                    422,
                    "Validation error",
                    (
                        f"Insufficient stock to reserve {item.sku}: "
                        f"need {item.qty}, available {allocated}."
                    ),
                    PROBLEM_VALIDATION,
                )
            for slice_line in plan:
                batch = await self.repo.require_batch(slice_line.batch_id)
                batch.qty_on_hand -= slice_line.qty
                await self.repo.save_batch(batch)
                await self.repo.add_movement(
                    StockMovement(
                        variant_id=item.variant_id,
                        batch_id=batch.id,
                        qty_delta=-slice_line.qty,
                        reason="reservation",
                        note=f"Order {order.order_number}",
                        actor_user_id=actor_user_id,
                    )
                )
                await self.repo.add_allocation(
                    StockReservationAllocation(
                        order_id=order.id,
                        order_item_id=item.id,
                        variant_id=item.variant_id,
                        batch_id=batch.id,
                        qty=slice_line.qty,
                    )
                )
                reserved_units += slice_line.qty
        if reserved_units:
            await self.audit.record(
                action="inventory.reserved",
                actor_user_id=actor_user_id,
                subject_type="order",
                subject_id=str(order.id),
                meta={"units": reserved_units, "order_number": order.order_number},
            )
        return reserved_units

    async def release_for_order(
        self,
        order: Order,
        *,
        actor_user_id: UUID | None,
        note: str | None = None,
    ) -> int:
        """Restore on-hand for active (non-consumed) allocations. Idempotent."""
        rows = await self.repo.list_active_allocations(order.id, for_update=True)
        if not rows:
            return 0
        now = datetime.now(UTC)
        restored = 0
        for row in rows:
            if not row.consumed:
                batch = await self.repo.require_batch(row.batch_id)
                batch.qty_on_hand += row.qty
                await self.repo.save_batch(batch)
                await self.repo.add_movement(
                    StockMovement(
                        variant_id=row.variant_id,
                        batch_id=row.batch_id,
                        qty_delta=row.qty,
                        reason="reservation_release",
                        note=note or f"Release {order.order_number}",
                        actor_user_id=actor_user_id,
                    )
                )
                restored += row.qty
            row.released_at = now
            await self.repo.save_allocation(row)
        if restored:
            await self.audit.record(
                action="inventory.reservation_released",
                actor_user_id=actor_user_id,
                subject_type="order",
                subject_id=str(order.id),
                meta={"units": restored, "order_number": order.order_number},
            )
        return restored

    async def consume_for_order(
        self,
        order: Order,
        *,
        actor_user_id: UUID | None,
    ) -> int:
        """Mark active allocations consumed (shipped) without restocking."""
        rows = await self.repo.list_active_allocations(order.id, for_update=True)
        if not rows:
            return 0
        now = datetime.now(UTC)
        for row in rows:
            row.consumed = True
            row.released_at = now
            await self.repo.save_allocation(row)
        await self.audit.record(
            action="inventory.reservation_consumed",
            actor_user_id=actor_user_id,
            subject_type="order",
            subject_id=str(order.id),
            meta={"units": sum(r.qty for r in rows), "order_number": order.order_number},
        )
        return len(rows)

    async def _plan_fefo(
        self, variant_id: UUID, qty: int, *, for_update: bool = False
    ) -> tuple[list[FefoAllocationLine], int]:
        remaining = qty
        lines: list[FefoAllocationLine] = []
        batches = await self.repo.list_batches(
            variant_id, include_empty=False, for_update=for_update
        )
        for batch in batches:
            if remaining <= 0:
                break
            take = min(batch.qty_on_hand, remaining)
            if take <= 0:
                continue
            lines.append(
                FefoAllocationLine(
                    batch_id=batch.id,
                    lot_code=batch.lot_code,
                    expires_on=batch.expires_on,
                    qty=take,
                )
            )
            remaining -= take
        allocated = qty - remaining
        return lines, allocated


def _batch_out(row: StockBatch) -> StockBatchOut:
    return StockBatchOut(
        id=row.id,
        variant_id=row.variant_id,
        lot_code=row.lot_code,
        qty_on_hand=row.qty_on_hand,
        expires_on=row.expires_on,
        received_at=row.received_at,
        note=row.note,
    )


def _movement_out(row: StockMovement) -> StockMovementOut:
    return StockMovementOut(
        id=row.id,
        variant_id=row.variant_id,
        batch_id=row.batch_id,
        qty_delta=row.qty_delta,
        reason=row.reason,
        note=row.note,
        actor_user_id=row.actor_user_id,
        created_at=row.created_at,
    )
