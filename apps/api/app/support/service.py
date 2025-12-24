"""Support tickets, prefs, and stock-back notify."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.models.support import NotificationPreference, SupportTicket, SupportTicketMessage
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_VALIDATION, ProblemError
from app.support.mailer import NullSupportMailer, SupportMailer
from app.support.repository import SupportRepository
from app.support.schemas import (
    NotificationPrefsIn,
    NotificationPrefsOut,
    TicketCreateIn,
    TicketListOut,
    TicketMessageIn,
    TicketMessageOut,
    TicketOut,
    TicketStatusIn,
    TicketSummaryOut,
)


class SupportService:
    def __init__(
        self,
        session: AsyncSession,
        mailer: SupportMailer | None = None,
    ) -> None:
        self.session = session
        self.repo = SupportRepository(session)
        self.audit = AuditService(session)
        self.mailer: SupportMailer = mailer or NullSupportMailer()

    async def get_prefs(self, user_id: UUID) -> NotificationPrefsOut:
        row = await self._ensure_prefs(user_id)
        return self._prefs_out(row)

    async def update_prefs(
        self, user_id: UUID, body: NotificationPrefsIn
    ) -> NotificationPrefsOut:
        row = await self._ensure_prefs(user_id)
        if body.order_updates is not None:
            row.order_updates = body.order_updates
        if body.marketing is not None:
            row.marketing = body.marketing
        if body.stock_back is not None:
            row.stock_back = body.stock_back
        if body.support_replies is not None:
            row.support_replies = body.support_replies
        await self.repo.save_prefs(row)
        await self.audit.record(
            action="notification_prefs.updated",
            actor_user_id=user_id,
            subject_type="user",
            subject_id=str(user_id),
            meta=body.model_dump(exclude_none=True),
        )
        return self._prefs_out(row)

    async def wants_order_updates(self, user_id: UUID) -> bool:
        row = await self.repo.get_prefs(user_id)
        return True if row is None else row.order_updates

    async def create_ticket(
        self, body: TicketCreateIn, *, user_id: UUID
    ) -> TicketOut:
        if body.topic == "order" and body.order_id is None:
            raise ProblemError(
                422,
                "Validation error",
                "order_id is required for order tickets.",
                PROBLEM_VALIDATION,
            )
        if body.topic == "product" and body.product_id is None:
            raise ProblemError(
                422,
                "Validation error",
                "product_id is required for product tickets.",
                PROBLEM_VALIDATION,
            )
        ticket = SupportTicket(
            user_id=user_id,
            topic=body.topic,
            subject=body.subject.strip(),
            status="open",
            order_id=body.order_id,
            product_id=body.product_id,
        )
        await self.repo.add_ticket(ticket)
        await self.repo.add_message(
            SupportTicketMessage(
                ticket_id=ticket.id,
                author_user_id=user_id,
                body=body.body.strip(),
                is_staff=False,
            )
        )
        await self.audit.record(
            action="support.ticket_created",
            actor_user_id=user_id,
            subject_type="support_ticket",
            subject_id=str(ticket.id),
            meta={"topic": body.topic},
        )
        ticket = await self.repo.require_ticket(ticket.id)
        return self._ticket_out(ticket)

    async def list_mine(self, user_id: UUID) -> TicketListOut:
        rows = await self.repo.list_for_user(user_id)
        return TicketListOut(items=[self._summary(row) for row in rows])

    async def get_mine(self, ticket_id: UUID, *, user_id: UUID) -> TicketOut:
        ticket = await self.repo.require_ticket(ticket_id)
        if ticket.user_id != user_id:
            raise ProblemError(403, "Forbidden", "Not your ticket.", PROBLEM_FORBIDDEN)
        return self._ticket_out(ticket)

    async def reply_mine(
        self, ticket_id: UUID, body: TicketMessageIn, *, user_id: UUID
    ) -> TicketOut:
        ticket = await self.repo.require_ticket(ticket_id)
        if ticket.user_id != user_id:
            raise ProblemError(403, "Forbidden", "Not your ticket.", PROBLEM_FORBIDDEN)
        if ticket.status == "closed":
            raise ProblemError(
                422,
                "Validation error",
                "This ticket is closed.",
                PROBLEM_VALIDATION,
            )
        await self.repo.add_message(
            SupportTicketMessage(
                ticket_id=ticket.id,
                author_user_id=user_id,
                body=body.body.strip(),
                is_staff=False,
            )
        )
        ticket.status = "open"
        ticket.updated_at = datetime.now(UTC)
        await self.repo.save_ticket(ticket)
        ticket = await self.repo.require_ticket(ticket.id)
        return self._ticket_out(ticket)

    async def admin_list(self, *, status: str = "open") -> TicketListOut:
        if status not in ("all", "open", "pending", "closed"):
            raise ProblemError(
                422,
                "Validation error",
                "status must be open, pending, closed, or all.",
                PROBLEM_VALIDATION,
            )
        rows = await self.repo.list_admin(status=None if status == "all" else status)
        emails = await self.repo.user_emails([r.user_id for r in rows])
        return TicketListOut(
            items=[self._summary(row, user_email=emails.get(row.user_id)) for row in rows]
        )

    async def admin_get(self, ticket_id: UUID) -> TicketOut:
        ticket = await self.repo.require_ticket(ticket_id)
        emails = await self.repo.user_emails([ticket.user_id])
        return self._ticket_out(ticket, user_email=emails.get(ticket.user_id))

    async def admin_reply(
        self,
        ticket_id: UUID,
        body: TicketMessageIn,
        *,
        actor_user_id: UUID,
    ) -> TicketOut:
        ticket = await self.repo.require_ticket(ticket_id)
        await self.repo.add_message(
            SupportTicketMessage(
                ticket_id=ticket.id,
                author_user_id=actor_user_id,
                body=body.body.strip(),
                is_staff=True,
            )
        )
        if ticket.status == "closed":
            ticket.status = "pending"
            ticket.closed_at = None
        elif ticket.status == "open":
            ticket.status = "pending"
        ticket.updated_at = datetime.now(UTC)
        await self.repo.save_ticket(ticket)
        await self.audit.record(
            action="support.staff_reply",
            actor_user_id=actor_user_id,
            subject_type="support_ticket",
            subject_id=str(ticket.id),
            meta={},
        )
        prefs = await self.repo.get_prefs(ticket.user_id)
        if prefs is None or prefs.support_replies:
            user = await self.repo.get_user(ticket.user_id)
            if user is not None and user.email:
                await self.mailer.send_support_reply(
                    email=user.email,
                    ticket_id=str(ticket.id),
                    subject=ticket.subject,
                    preview=body.body.strip(),
                )
        ticket = await self.repo.require_ticket(ticket.id)
        emails = await self.repo.user_emails([ticket.user_id])
        return self._ticket_out(ticket, user_email=emails.get(ticket.user_id))

    async def admin_set_status(
        self,
        ticket_id: UUID,
        body: TicketStatusIn,
        *,
        actor_user_id: UUID,
    ) -> TicketOut:
        ticket = await self.repo.require_ticket(ticket_id)
        ticket.status = body.status
        ticket.closed_at = datetime.now(UTC) if body.status == "closed" else None
        ticket.updated_at = datetime.now(UTC)
        await self.repo.save_ticket(ticket)
        await self.audit.record(
            action="support.ticket_status",
            actor_user_id=actor_user_id,
            subject_type="support_ticket",
            subject_id=str(ticket.id),
            meta={"status": body.status, "note": body.note},
        )
        ticket = await self.repo.require_ticket(ticket.id)
        emails = await self.repo.user_emails([ticket.user_id])
        return self._ticket_out(ticket, user_email=emails.get(ticket.user_id))

    async def notify_stock_back(self, product_id: UUID) -> int:
        product = await self.repo.get_product(product_id)
        if product is None:
            return 0
        recipients = await self.repo.wishlisters_for_stock_back(product_id)
        for _uid, email, slug in recipients:
            await self.mailer.send_stock_back(
                email=email,
                product_slug=slug,
                product_name=product.name,
            )
        return len(recipients)

    async def _ensure_prefs(self, user_id: UUID) -> NotificationPreference:
        row = await self.repo.get_prefs(user_id)
        if row is not None:
            return row
        row = NotificationPreference(
            user_id=user_id,
            order_updates=True,
            marketing=False,
            stock_back=True,
            support_replies=True,
        )
        return await self.repo.add_prefs(row)

    def _prefs_out(self, row: NotificationPreference) -> NotificationPrefsOut:
        return NotificationPrefsOut(
            order_updates=row.order_updates,
            marketing=row.marketing,
            stock_back=row.stock_back,
            support_replies=row.support_replies,
        )

    def _summary(
        self, ticket: SupportTicket, *, user_email: str | None = None
    ) -> TicketSummaryOut:
        return TicketSummaryOut(
            id=ticket.id,
            topic=ticket.topic,
            subject=ticket.subject,
            status=ticket.status,
            order_id=ticket.order_id,
            product_id=ticket.product_id,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            user_email=user_email,
            message_count=len(ticket.messages or []),
        )

    def _ticket_out(
        self, ticket: SupportTicket, *, user_email: str | None = None
    ) -> TicketOut:
        summary = self._summary(ticket, user_email=user_email)
        return TicketOut(
            **summary.model_dump(),
            messages=[
                TicketMessageOut(
                    id=m.id,
                    body=m.body,
                    is_staff=m.is_staff,
                    author_user_id=m.author_user_id,
                    created_at=m.created_at,
                )
                for m in sorted(
                    ticket.messages or [],
                    key=lambda x: x.created_at or datetime.min.replace(tzinfo=UTC),
                )
            ],
        )
