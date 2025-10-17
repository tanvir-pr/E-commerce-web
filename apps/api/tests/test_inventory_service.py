"""InventoryService FEFO and adjustments with fakes."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.inventory.schemas import AdjustmentIn, FefoIssueIn, ReceiptIn
from app.inventory.service import InventoryService
from app.problems import ProblemError


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


class FakeRepo:
    def __init__(self, variant: SimpleNamespace) -> None:
        self.variant = variant
        self.batches: dict[UUID, SimpleNamespace] = {}
        self.movements: list[SimpleNamespace] = []

    async def require_variant(self, variant_id: UUID) -> SimpleNamespace:
        if variant_id != self.variant.id:
            raise ProblemError(404, "Not found", "Variant not found.", "x")
        return self.variant

    async def require_batch(self, batch_id: UUID) -> SimpleNamespace:
        row = self.batches.get(batch_id)
        if row is None:
            raise ProblemError(404, "Not found", "Stock batch not found.", "x")
        return row

    async def list_batches(
        self, variant_id: UUID, *, include_empty: bool = False
    ) -> list[SimpleNamespace]:
        rows = [b for b in self.batches.values() if b.variant_id == variant_id]
        if not include_empty:
            rows = [b for b in rows if b.qty_on_hand > 0]

        def sort_key(batch: SimpleNamespace) -> tuple[int, date, datetime]:
            exp = batch.expires_on or date.max
            null_flag = 1 if batch.expires_on is None else 0
            return (null_flag, exp, batch.received_at)

        return sorted(rows, key=sort_key)

    async def add_batch(self, batch: object) -> SimpleNamespace:
        batch_id = getattr(batch, "id", None) or uuid4()
        row = SimpleNamespace(
            id=batch_id,
            variant_id=batch.variant_id,
            lot_code=getattr(batch, "lot_code", None),
            qty_on_hand=int(batch.qty_on_hand),
            expires_on=getattr(batch, "expires_on", None),
            received_at=getattr(batch, "received_at", datetime.now(UTC)),
            note=getattr(batch, "note", None),
            updated_at=datetime.now(UTC),
        )
        self.batches[row.id] = row
        return row

    async def save_batch(self, batch: SimpleNamespace) -> SimpleNamespace:
        batch.updated_at = datetime.now(UTC)
        return batch

    async def add_movement(self, movement: object) -> SimpleNamespace:
        row = SimpleNamespace(
            id=uuid4(),
            variant_id=movement.variant_id,
            batch_id=getattr(movement, "batch_id", None),
            qty_delta=int(movement.qty_delta),
            reason=str(movement.reason),
            note=getattr(movement, "note", None),
            actor_user_id=getattr(movement, "actor_user_id", None),
            created_at=datetime.now(UTC),
        )
        self.movements.append(row)
        return row

    async def list_movements(
        self, variant_id: UUID, *, limit: int = 50
    ) -> list[SimpleNamespace]:
        rows = [m for m in self.movements if m.variant_id == variant_id]
        return rows[:limit]

    async def qty_on_hand(self, variant_id: UUID) -> int:
        return sum(b.qty_on_hand for b in self.batches.values() if b.variant_id == variant_id)

    async def nearest_expiry(self, variant_id: UUID) -> date | None:
        dates = [
            b.expires_on
            for b in self.batches.values()
            if b.variant_id == variant_id and b.qty_on_hand > 0 and b.expires_on
        ]
        return min(dates) if dates else None

    async def list_variants(self) -> list[SimpleNamespace]:
        return [self.variant]


def _service() -> tuple[InventoryService, FakeRepo, FakeAudit, SimpleNamespace]:
    variant = SimpleNamespace(
        id=uuid4(),
        sku="SER-BAR-30",
        product_id=uuid4(),
        product=SimpleNamespace(slug="daily-barrier-serum"),
    )
    service = InventoryService(FakeSession())  # type: ignore[arg-type]
    repo = FakeRepo(variant)
    audit = FakeAudit()
    service.repo = repo  # type: ignore[assignment]
    service.audit = audit  # type: ignore[assignment]
    return service, repo, audit, variant


@pytest.mark.asyncio
async def test_receipt_creates_batch_and_movement() -> None:
    service, repo, audit, variant = _service()
    out = await service.receive(
        ReceiptIn(
            variant_id=variant.id,
            qty=40,
            lot_code="LOT-A",
            expires_on=date.today() + timedelta(days=180),
        ),
        actor_user_id=uuid4(),
    )
    assert out.qty_on_hand == 40
    assert out.batches[0].lot_code == "LOT-A"
    assert len(repo.movements) == 1
    assert repo.movements[0].reason == "receipt"
    assert "inventory.receipt" in audit.actions


@pytest.mark.asyncio
async def test_fefo_issues_earliest_expiry_first() -> None:
    service, repo, _a, variant = _service()
    await service.receive(
        ReceiptIn(
            variant_id=variant.id,
            qty=10,
            lot_code="LATE",
            expires_on=date.today() + timedelta(days=90),
        ),
        actor_user_id=uuid4(),
    )
    await service.receive(
        ReceiptIn(
            variant_id=variant.id,
            qty=10,
            lot_code="EARLY",
            expires_on=date.today() + timedelta(days=30),
        ),
        actor_user_id=uuid4(),
    )
    preview = await service.preview_fefo(variant.id, 12)
    assert preview.lines[0].lot_code == "EARLY"
    assert preview.lines[0].qty == 10
    assert preview.lines[1].lot_code == "LATE"
    assert preview.lines[1].qty == 2

    issued = await service.issue_fefo(
        FefoIssueIn(variant_id=variant.id, qty=12, reason="waste"),
        actor_user_id=uuid4(),
    )
    assert issued.shortfall == 0
    assert await repo.qty_on_hand(variant.id) == 8
    early = next(b for b in repo.batches.values() if b.lot_code == "EARLY")
    late = next(b for b in repo.batches.values() if b.lot_code == "LATE")
    assert early.qty_on_hand == 0
    assert late.qty_on_hand == 8


@pytest.mark.asyncio
async def test_adjust_rejects_negative_batch() -> None:
    service, repo, _a, variant = _service()
    stock = await service.receive(
        ReceiptIn(variant_id=variant.id, qty=5, lot_code="X"),
        actor_user_id=uuid4(),
    )
    batch_id = stock.batches[0].id
    with pytest.raises(ProblemError) as exc:
        await service.adjust(
            AdjustmentIn(batch_id=batch_id, qty_delta=-6),
            actor_user_id=uuid4(),
        )
    assert exc.value.status == 422


@pytest.mark.asyncio
async def test_fefo_issue_shortfall() -> None:
    service, _r, _a, variant = _service()
    await service.receive(
        ReceiptIn(variant_id=variant.id, qty=3, lot_code="S"),
        actor_user_id=uuid4(),
    )
    with pytest.raises(ProblemError) as exc:
        await service.issue_fefo(
            FefoIssueIn(variant_id=variant.id, qty=5),
            actor_user_id=uuid4(),
        )
    assert "Insufficient stock" in exc.value.detail
