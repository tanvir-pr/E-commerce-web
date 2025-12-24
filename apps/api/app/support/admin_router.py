"""Staff support inbox."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.session import get_session
from app.support.mailer import ArqSupportMailer, NullSupportMailer
from app.support.schemas import (
    TicketListOut,
    TicketMessageIn,
    TicketOut,
    TicketStatusIn,
)
from app.support.service import SupportService

router = APIRouter(tags=["admin-support"])


def get_support_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SupportService:
    arq = getattr(request.app.state, "arq", None)
    mailer = ArqSupportMailer(arq) if arq is not None else NullSupportMailer()
    return SupportService(session, mailer=mailer)


@router.get("/admin/support/tickets", response_model=TicketListOut)
async def admin_list_tickets(
    status: str = Query(default="open"),
    _staff: User = Depends(get_current_staff_user),
    service: SupportService = Depends(get_support_service),
) -> TicketListOut:
    return await service.admin_list(status=status)


@router.get("/admin/support/tickets/{ticket_id}", response_model=TicketOut)
async def admin_get_ticket(
    ticket_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: SupportService = Depends(get_support_service),
) -> TicketOut:
    return await service.admin_get(ticket_id)


@router.post("/admin/support/tickets/{ticket_id}/messages", response_model=TicketOut)
async def admin_reply_ticket(
    ticket_id: UUID,
    body: TicketMessageIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: SupportService = Depends(get_support_service),
) -> TicketOut:
    return await service.admin_reply(ticket_id, body, actor_user_id=actor_id)


@router.patch("/admin/support/tickets/{ticket_id}", response_model=TicketOut)
async def admin_set_ticket_status(
    ticket_id: UUID,
    body: TicketStatusIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: SupportService = Depends(get_support_service),
) -> TicketOut:
    return await service.admin_set_status(ticket_id, body, actor_user_id=actor_id)
