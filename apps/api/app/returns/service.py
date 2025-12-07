"""RMA create/review, ledger, refunds, and PDF invoices."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.audit.service import AuditService
from app.config import Settings, get_settings
from app.inventory.service import InventoryService
from app.media.constants import ALLOWED_UPLOAD_TYPES
from app.media.storage import MediaStorage
from app.models.order import Order, OrderEvent
from app.models.returns import (
    LedgerEntry,
    ReturnRequest,
    ReturnRequestItem,
    ReturnRequestPhoto,
)
from app.orders.mailer import NullOrderMailer, OrderMailer
from app.orders.service import OrderService
from app.payments.factory import GATEWAY_METHODS, get_gateway
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_VALIDATION, ProblemError
from app.returns.constants import (
    MAX_RETURN_PHOTOS,
    RETURN_REASON_CODES,
    RETURNABLE_PAYMENT_STATUSES,
)
from app.returns.invoice import build_invoice_pdf
from app.returns.repository import ReturnsRepository
from app.returns.schemas import (
    CreateReturnIn,
    LedgerEntryOut,
    LedgerListOut,
    ReturnItemOut,
    ReturnListOut,
    ReturnPhotoOut,
    ReturnRequestOut,
)


class ReturnsService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        mailer: OrderMailer | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = ReturnsRepository(session)
        self.orders = OrderService(
            session, settings=self.settings, mailer=mailer or NullOrderMailer()
        )
        self.inventory = InventoryService(session)
        self.audit = AuditService(session)
        self.media = MediaStorage(self.settings)

    async def create(
        self, order_id: UUID, body: CreateReturnIn, *, user_id: UUID
    ) -> ReturnRequestOut:
        order = await self.orders.repo.require_owned(order_id, user_id)
        if order.status != "delivered":
            raise ProblemError(
                422,
                "Validation error",
                "Returns are only accepted after delivery.",
                PROBLEM_VALIDATION,
            )
        if (order.payment_status or "") not in RETURNABLE_PAYMENT_STATUSES:
            raise ProblemError(
                422,
                "Validation error",
                "Order payment is not eligible for return refund.",
                PROBLEM_VALIDATION,
            )
        reason = body.reason_code.strip().lower()
        if reason not in RETURN_REASON_CODES:
            raise ProblemError(
                422,
                "Validation error",
                f"reason_code must be one of: {', '.join(sorted(RETURN_REASON_CODES))}",
                PROBLEM_VALIDATION,
            )
        if await self.repo.has_open_return(order.id):
            raise ProblemError(
                422,
                "Validation error",
                "An open return request already exists for this order.",
                PROBLEM_VALIDATION,
            )

        items_by_id = {item.id: item for item in order.items}
        rma = ReturnRequest(
            order_id=order.id,
            user_id=user_id,
            status="pending",
            reason_code=reason,
            customer_note=body.customer_note,
        )
        await self.repo.add_return(rma)
        for line in body.items:
            item = items_by_id.get(line.order_item_id)
            if item is None:
                raise ProblemError(
                    422,
                    "Validation error",
                    "Return item does not belong to this order.",
                    PROBLEM_VALIDATION,
                )
            used = await self.repo.approved_qty_for_item(item.id)
            remaining = item.qty - used
            if line.qty > remaining:
                raise ProblemError(
                    422,
                    "Validation error",
                    f"Cannot return {line.qty} of {item.sku}; only {remaining} left.",
                    PROBLEM_VALIDATION,
                )
            await self.repo.add_item(
                ReturnRequestItem(
                    return_request_id=rma.id,
                    order_item_id=item.id,
                    qty=line.qty,
                    unit_price_poisha=item.unit_price_poisha,
                )
            )
        await self.audit.record(
            action="return.created",
            actor_user_id=user_id,
            subject_type="return_request",
            subject_id=str(rma.id),
            meta={"order_id": str(order.id), "reason": reason},
        )
        rma = await self.repo.require_return(rma.id)
        return self._out(rma, order_number=order.order_number)

    async def list_mine(self, order_id: UUID, *, user_id: UUID) -> ReturnListOut:
        order = await self.orders.repo.require_owned(order_id, user_id)
        rows = await self.repo.list_for_order(order.id)
        return ReturnListOut(
            items=[self._out(r, order_number=order.order_number) for r in rows]
        )

    async def admin_list(self, *, status: str = "pending") -> ReturnListOut:
        rows = await self.repo.list_admin(status=status)
        items: list[ReturnRequestOut] = []
        for row in rows:
            order = await self.orders.repo.require(row.order_id)
            items.append(self._out(row, order_number=order.order_number))
        return ReturnListOut(items=items)

    async def admin_get(self, rma_id: UUID) -> ReturnRequestOut:
        row = await self.repo.require_return(rma_id)
        order = await self.orders.repo.require(row.order_id)
        return self._out(row, order_number=order.order_number)

    async def reject(
        self, rma_id: UUID, *, actor_user_id: UUID, staff_note: str | None
    ) -> ReturnRequestOut:
        row = await self.repo.require_return(rma_id)
        if row.status != "pending":
            raise ProblemError(
                422, "Validation error", "Only pending returns can be rejected.", PROBLEM_VALIDATION
            )
        if not (staff_note or "").strip():
            raise ProblemError(
                422, "Validation error", "staff_note is required to reject.", PROBLEM_VALIDATION
            )
        row.status = "rejected"
        row.staff_note = staff_note
        row.reviewed_by = actor_user_id
        row.reviewed_at = datetime.now(UTC)
        await self.repo.save_return(row)
        order = await self.orders.repo.require(row.order_id)
        await self.audit.record(
            action="return.rejected",
            actor_user_id=actor_user_id,
            subject_type="return_request",
            subject_id=str(row.id),
            meta={"order_id": str(order.id)},
        )
        return self._out(row, order_number=order.order_number)

    async def approve(
        self, rma_id: UUID, *, actor_user_id: UUID, staff_note: str | None = None
    ) -> ReturnRequestOut:
        row = await self.repo.require_return(rma_id)
        if row.status != "pending":
            raise ProblemError(
                422, "Validation error", "Only pending returns can be approved.", PROBLEM_VALIDATION
            )
        order = await self.orders.repo.require(row.order_id)
        await self.ensure_sale_ledger(order, actor_user_id=actor_user_id)

        items_by_id = {item.id: item for item in order.items}
        restock_lines: list[tuple[UUID, int]] = []
        refund_poisha = 0
        for line in row.items:
            item = items_by_id.get(line.order_item_id)
            if item is None:
                continue
            restock_lines.append((item.variant_id, line.qty))
            refund_poisha += line.qty * line.unit_price_poisha

        await self.inventory.restock_order_items(
            order,
            restock_lines,
            actor_user_id=actor_user_id,
            note=f"RMA {row.id}",
        )

        refund_ref = await self._issue_refund(order, refund_poisha)
        await self.repo.add_ledger(
            LedgerEntry(
                order_id=order.id,
                entry_type="refund",
                amount_poisha=refund_poisha,
                currency=order.currency or "BDT",
                return_request_id=row.id,
                gateway_refund_ref=refund_ref,
                note=f"RMA approved {row.reason_code}",
                actor_user_id=actor_user_id,
            )
        )

        # Include this refund (already inserted) when deciding full return.
        total_refunded = await self.repo.refunded_poisha(order.id)
        if total_refunded >= order.merchandise_subtotal_poisha:
            if order.status == "delivered":
                # Item restock already done — do not call order restock again.
                now = datetime.now(UTC)
                order.status = "returned"
                order.returned_at = now
                await self.orders.repo.add_event(
                    OrderEvent(
                        order_id=order.id,
                        from_status="delivered",
                        to_status="returned",
                        actor_user_id=actor_user_id,
                        source="staff",
                        note="RMA fully approved",
                        meta={"return_request_id": str(row.id)},
                    )
                )
            order.payment_status = "refunded"
            await self.orders.repo.save(order)

        row.status = "approved"
        row.staff_note = staff_note
        row.reviewed_by = actor_user_id
        row.reviewed_at = datetime.now(UTC)
        await self.repo.save_return(row)
        await self.audit.record(
            action="return.approved",
            actor_user_id=actor_user_id,
            subject_type="return_request",
            subject_id=str(row.id),
            meta={
                "order_id": str(order.id),
                "refund_poisha": refund_poisha,
                "refund_ref": refund_ref,
            },
        )
        return self._out(row, order_number=order.order_number)

    async def add_photo(
        self,
        rma_id: UUID,
        *,
        user_id: UUID,
        data: bytes,
        content_type: str,
    ) -> ReturnRequestOut:
        row = await self.repo.require_return(rma_id)
        if row.user_id != user_id:
            raise ProblemError(403, "Forbidden", "Not your return request.", PROBLEM_FORBIDDEN)
        if row.status != "pending":
            raise ProblemError(
                422,
                "Validation error",
                "Photos only allowed on pending returns.",
                PROBLEM_VALIDATION,
            )
        if len(row.photos) >= MAX_RETURN_PHOTOS:
            raise ProblemError(
                422,
                "Validation error",
                f"At most {MAX_RETURN_PHOTOS} photos per return.",
                PROBLEM_VALIDATION,
            )
        if content_type not in ALLOWED_UPLOAD_TYPES:
            raise ProblemError(
                422, "Validation error", "Photo must be jpeg, png, or webp.", PROBLEM_VALIDATION
            )
        if len(data) > self.settings.media_max_upload_bytes:
            raise ProblemError(422, "Validation error", "Photo too large.", PROBLEM_VALIDATION)
        photo_id = UUID(str(uuid7()))
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
        relative = self.media.return_photo_relative(row.id, photo_id, ext)
        self.media.write_bytes(relative, data)
        await self.repo.add_photo(
            ReturnRequestPhoto(
                id=photo_id,
                return_request_id=row.id,
                relative_path=relative,
                content_type=content_type,
            )
        )
        order = await self.orders.repo.require(row.order_id)
        row = await self.repo.require_return(row.id)
        return self._out(row, order_number=order.order_number)

    async def ensure_sale_ledger(
        self, order: Order, *, actor_user_id: UUID | None
    ) -> None:
        if await self.repo.has_sale_entry(order.id):
            return
        await self.repo.add_ledger(
            LedgerEntry(
                order_id=order.id,
                entry_type="sale",
                amount_poisha=order.total_poisha,
                currency=order.currency or "BDT",
                note="Order total",
                actor_user_id=actor_user_id,
            )
        )

    async def ledger_for_order(
        self, order_id: UUID, *, user_id: UUID | None = None, staff: bool = False
    ) -> LedgerListOut:
        if staff:
            order = await self.orders.repo.require(order_id)
        else:
            assert user_id is not None
            order = await self.orders.repo.require_owned(order_id, user_id)
        await self.ensure_sale_ledger(order, actor_user_id=user_id)
        rows = await self.repo.list_ledger(order.id)
        return LedgerListOut(
            items=[
                LedgerEntryOut(
                    id=r.id,
                    entry_type=r.entry_type,
                    amount_poisha=r.amount_poisha,
                    currency=r.currency,
                    note=r.note,
                    gateway_refund_ref=r.gateway_refund_ref,
                    created_at=r.created_at,
                )
                for r in rows
            ]
        )

    async def invoice_pdf(
        self, order_id: UUID, *, user_id: UUID | None = None, staff: bool = False
    ) -> tuple[bytes, str]:
        if staff:
            order = await self.orders.repo.require(order_id)
        else:
            assert user_id is not None
            order = await self.orders.repo.require_owned(order_id, user_id)
        await self.ensure_sale_ledger(order, actor_user_id=user_id)
        addr = order.shipping_address or {}
        ship_to = ", ".join(
            p
            for p in [
                str(addr.get("line1") or ""),
                str(addr.get("city") or ""),
                str(addr.get("district") or ""),
            ]
            if p
        )
        refunds = await self.repo.refunded_poisha(order.id)
        pdf = build_invoice_pdf(
            order_number=order.order_number,
            placed_at=order.placed_at.isoformat(),
            ship_to=ship_to or "—",
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            items=[
                {
                    "name": item.product_name,
                    "qty": item.qty,
                    "line_total_poisha": item.line_total_poisha,
                }
                for item in order.items
            ],
            merchandise_poisha=order.merchandise_subtotal_poisha,
            shipping_poisha=order.shipping_poisha,
            total_poisha=order.total_poisha,
            refunds_poisha=refunds,
        )
        return pdf, f"{order.order_number}.pdf"

    async def _issue_refund(self, order: Order, amount_poisha: int) -> str | None:
        method = (order.payment_method or "").strip().lower()
        if amount_poisha <= 0:
            return None
        if method == "cod" or method not in GATEWAY_METHODS:
            return f"COD-RF-{order.order_number}"
        # Prefer provider_ref from order events meta, else synthetic.
        provider_ref = order.order_number
        for event in reversed(list(order.events or [])):
            meta = getattr(event, "meta", None) or {}
            if isinstance(meta, dict) and meta.get("provider_ref"):
                provider_ref = str(meta["provider_ref"])
                break
        gateway = get_gateway(method, self.settings)
        result = gateway.refund(
            provider_ref=provider_ref,
            amount_poisha=amount_poisha,
            order_number=order.order_number,
        )
        if not result.ok:
            order.payment_status = "refund_needed"
            await self.orders.repo.save(order)
            raise ProblemError(
                422,
                "Validation error",
                result.reason or "Gateway refund failed.",
                PROBLEM_VALIDATION,
            )
        return result.refund_ref

    def _out(self, row: ReturnRequest, *, order_number: str | None) -> ReturnRequestOut:
        refund = sum(i.qty * i.unit_price_poisha for i in row.items)
        return ReturnRequestOut(
            id=row.id,
            order_id=row.order_id,
            order_number=order_number,
            status=row.status,
            reason_code=row.reason_code,
            customer_note=row.customer_note,
            staff_note=row.staff_note,
            refund_poisha=refund,
            items=[
                ReturnItemOut(
                    id=i.id,
                    order_item_id=i.order_item_id,
                    qty=i.qty,
                    unit_price_poisha=i.unit_price_poisha,
                )
                for i in row.items
            ],
            photos=[
                ReturnPhotoOut(
                    id=p.id,
                    relative_path=p.relative_path,
                    url=self.media.relative_url(p.relative_path),
                    content_type=p.content_type,
                    created_at=p.created_at,
                )
                for p in row.photos
            ],
            created_at=row.created_at,
            reviewed_at=row.reviewed_at,
        )
