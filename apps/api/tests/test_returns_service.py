"""RMA approve/reject, ledger, and invoice PDF (Part 26)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.config import Settings
from app.problems import ProblemError
from app.returns.schemas import CreateReturnIn, ReturnItemIn
from app.returns.service import ReturnsService


def _settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://u:p@localhost/db",
        redis_url="redis://localhost:6379/0",
        public_web_url="http://localhost:3001",
        media_root="/tmp/store-media-test",
        media_max_upload_bytes=1_000_000,
        bkash_app_secret="bk",
        sslcommerz_store_password="ssl",
        jwt_secret="jwt",
    )


class FakeSession:
    async def flush(self) -> None:
        return None

    def add(self, _obj: object) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeInventory:
    def __init__(self) -> None:
        self.restocked_lines: list[tuple[object, int]] = []

    async def restock_order_items(
        self, _order: object, lines: list[tuple[object, int]], **_k: object
    ) -> int:
        self.restocked_lines.extend(lines)
        return sum(q for _, q in lines)


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


class FakeReturnsRepo:
    def __init__(self) -> None:
        self.returns: dict[object, SimpleNamespace] = {}
        self.ledger: list[SimpleNamespace] = []

    async def add_return(self, row: object) -> object:
        if getattr(row, "id", None) is None:
            row.id = uuid4()  # type: ignore[attr-defined]
        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
        if getattr(row, "updated_at", None) is None:
            row.updated_at = datetime.now(UTC)  # type: ignore[attr-defined]
        if getattr(row, "items", None) is None:
            row.items = []  # type: ignore[attr-defined]
        if getattr(row, "photos", None) is None:
            row.photos = []  # type: ignore[attr-defined]
        self.returns[row.id] = row  # type: ignore[index]
        return row

    async def add_item(self, row: object) -> object:
        if getattr(row, "id", None) is None:
            row.id = uuid4()  # type: ignore[attr-defined]
        parent = self.returns[row.return_request_id]  # type: ignore[index]
        parent.items.append(row)
        return row

    async def add_photo(self, row: object) -> object:
        return row

    async def save_return(self, row: object) -> object:
        self.returns[row.id] = row  # type: ignore[index]
        return row

    async def get_return(self, rma_id: object) -> SimpleNamespace | None:
        return self.returns.get(rma_id)

    async def require_return(self, rma_id: object) -> SimpleNamespace:
        row = self.returns.get(rma_id)
        if row is None:
            raise ProblemError(404, "Not found", "Return request not found.", "x")
        return row

    async def list_for_order(self, order_id: object) -> list[SimpleNamespace]:
        return [r for r in self.returns.values() if r.order_id == order_id]

    async def list_admin(self, *, status: str = "pending") -> list[SimpleNamespace]:
        rows = list(self.returns.values())
        if status != "all":
            rows = [r for r in rows if r.status == status]
        return rows

    async def has_open_return(self, order_id: object) -> bool:
        return any(
            r.order_id == order_id and r.status == "pending" for r in self.returns.values()
        )

    async def approved_qty_for_item(self, order_item_id: object) -> int:
        total = 0
        for r in self.returns.values():
            if r.status not in {"pending", "approved"}:
                continue
            for item in r.items:
                if item.order_item_id == order_item_id:
                    total += int(item.qty)
        return total

    async def add_ledger(self, row: object) -> object:
        if getattr(row, "id", None) is None:
            row.id = uuid4()  # type: ignore[attr-defined]
        if getattr(row, "created_at", None) is None:
            row.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
        self.ledger.append(row)  # type: ignore[arg-type]
        return row

    async def list_ledger(self, order_id: object) -> list[SimpleNamespace]:
        return [r for r in self.ledger if r.order_id == order_id]

    async def has_sale_entry(self, order_id: object) -> bool:
        return any(r.order_id == order_id and r.entry_type == "sale" for r in self.ledger)

    async def refunded_poisha(self, order_id: object) -> int:
        return sum(
            int(r.amount_poisha)
            for r in self.ledger
            if r.order_id == order_id and r.entry_type in {"refund", "shipping_refund"}
        )


def _delivered_order(*, method: str = "bkash") -> SimpleNamespace:
    user_id = uuid4()
    item_id = uuid4()
    variant_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        order_number="SOL-RMA-0001",
        user_id=user_id,
        status="delivered",
        currency="BDT",
        merchandise_subtotal_poisha=10000,
        shipping_poisha=6000,
        total_poisha=16000,
        shipping_address={"line1": "12 Road", "city": "Dhaka", "district": "Dhaka"},
        payment_method=method,
        payment_status="paid",
        placed_at=datetime.now(UTC),
        returned_at=None,
        items=[
            SimpleNamespace(
                id=item_id,
                variant_id=variant_id,
                product_name="Serum",
                sku="SER-1",
                qty=1,
                unit_price_poisha=10000,
                line_total_poisha=10000,
            )
        ],
        events=[],
    )


def _service(order: SimpleNamespace) -> tuple[ReturnsService, FakeReturnsRepo, FakeInventory]:
    service = ReturnsService(FakeSession(), settings=_settings())  # type: ignore[arg-type]
    repo = FakeReturnsRepo()
    inventory = FakeInventory()
    service.repo = repo  # type: ignore[assignment]
    service.orders.repo = FakeOrderRepo(order)  # type: ignore[assignment]
    service.orders.audit = FakeAudit()  # type: ignore[assignment]
    service.inventory = inventory  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    return service, repo, inventory


@pytest.mark.asyncio
async def test_create_and_approve_full_rma() -> None:
    order = _delivered_order()
    item_id = order.items[0].id
    service, repo, inventory = _service(order)
    created = await service.create(
        order.id,
        CreateReturnIn(
            reason_code="defective",
            customer_note="Broken pump",
            items=[ReturnItemIn(order_item_id=item_id, qty=1)],
        ),
        user_id=order.user_id,
    )
    assert created.status == "pending"
    assert created.refund_poisha == 10000

    approved = await service.approve(created.id, actor_user_id=uuid4(), staff_note="OK")
    assert approved.status == "approved"
    assert order.status == "returned"
    assert order.payment_status == "refunded"
    assert inventory.restocked_lines
    assert any(e.entry_type == "sale" for e in repo.ledger)
    assert any(e.entry_type == "refund" for e in repo.ledger)


@pytest.mark.asyncio
async def test_reject_requires_note() -> None:
    order = _delivered_order()
    service, _repo, _inv = _service(order)
    created = await service.create(
        order.id,
        CreateReturnIn(
            reason_code="other",
            items=[ReturnItemIn(order_item_id=order.items[0].id, qty=1)],
        ),
        user_id=order.user_id,
    )
    with pytest.raises(ProblemError) as exc:
        await service.reject(created.id, actor_user_id=uuid4(), staff_note=None)
    assert exc.value.status == 422


@pytest.mark.asyncio
async def test_invoice_pdf_bytes() -> None:
    order = _delivered_order()
    service, _repo, _inv = _service(order)
    pdf, filename = await service.invoice_pdf(order.id, user_id=order.user_id)
    assert pdf.startswith(b"%PDF")
    assert filename.startswith("SOL-RMA")
