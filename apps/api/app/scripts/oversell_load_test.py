"""Concurrent FEFO stock deduct stress test — assert no oversell.

N concurrent buyers each try to take ``--qty`` units from one variant.
Successes must be ≤ starting on-hand and final on-hand must stay ≥ 0.

Usage:

  python -m app.scripts.oversell_load_test --variant-id <uuid> --buyers 20
  python -m app.scripts.oversell_load_test --variant-id <uuid> --set-stock 5 --buyers 20
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select, update

from app.inventory.repository import InventoryRepository
from app.inventory.service import InventoryService
from app.models.inventory import StockBatch
from app.session import SessionFactory


async def _attempt(variant_id: UUID, qty: int) -> bool:
    async with SessionFactory() as session:
        try:
            service = InventoryService(session)
            plan, allocated = await service._plan_fefo(  # noqa: SLF001
                variant_id, qty, for_update=True
            )
            if allocated < qty:
                await session.rollback()
                return False
            repo = InventoryRepository(session)
            for slice_line in plan:
                batch = await repo.require_batch(slice_line.batch_id)
                if batch.qty_on_hand < slice_line.qty:
                    await session.rollback()
                    return False
                batch.qty_on_hand -= slice_line.qty
                await repo.save_batch(batch)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            return False


async def _on_hand(variant_id: UUID) -> int:
    async with SessionFactory() as session:
        result = await session.execute(
            select(StockBatch.qty_on_hand).where(StockBatch.variant_id == variant_id)
        )
        return int(sum(int(r or 0) for r in result.scalars().all()))


async def run(*, variant_id: UUID, buyers: int, qty: int) -> int:
    before = await _on_hand(variant_id)
    results = await asyncio.gather(*[_attempt(variant_id, qty) for _ in range(buyers)])
    successes = sum(1 for ok in results if ok)
    after = await _on_hand(variant_id)
    print(f"stock_before={before} buyers={buyers} successes={successes} stock_after={after}")
    if after < 0:
        raise SystemExit("FAIL: negative on-hand (oversell)")
    if successes * qty > before:
        raise SystemExit(f"FAIL: reserved {successes * qty} > stock {before}")
    print("PASS: no oversell detected")
    return successes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant-id", required=True, type=UUID)
    parser.add_argument("--buyers", type=int, default=20)
    parser.add_argument("--qty", type=int, default=1, help="Units each buyer tries to take")
    parser.add_argument(
        "--set-stock",
        type=int,
        default=None,
        help="Optionally force first batch on-hand before the run",
    )
    args = parser.parse_args()

    async def _prepare() -> None:
        if args.set_stock is None:
            return
        async with SessionFactory() as session:
            result = await session.execute(
                select(StockBatch)
                .where(StockBatch.variant_id == args.variant_id)
                .order_by(StockBatch.received_at.asc())
                .limit(1)
            )
            batch = result.scalar_one_or_none()
            if batch is None:
                raise SystemExit("No stock batch for variant; receive inventory first")
            await session.execute(
                update(StockBatch)
                .where(StockBatch.id == batch.id)
                .values(qty_on_hand=args.set_stock)
            )
            await session.commit()
            print(f"set_stock={args.set_stock} on batch {batch.id}")

    asyncio.run(_prepare())
    asyncio.run(run(variant_id=args.variant_id, buyers=args.buyers, qty=args.qty))


if __name__ == "__main__":
    main()
