"""Customer support tickets and notification preferences."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user_id
from app.session import get_session
from app.support.mailer import ArqSupportMailer, NullSupportMailer
from app.support.schemas import (
    NotificationPrefsIn,
    NotificationPrefsOut,
    TicketCreateIn,
    TicketListOut,
    TicketMessageIn,
    TicketOut,
)
from app.support.service import SupportService

router = APIRouter(tags=["support"])


def get_support_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SupportService:
    arq = getattr(request.app.state, "arq", None)
    mailer = ArqSupportMailer(arq) if arq is not None else NullSupportMailer()
    return SupportService(session, mailer=mailer)


@router.get("/users/me/notification-preferences", response_model=NotificationPrefsOut)
async def get_notification_prefs(
    user_id: UUID = Depends(get_current_user_id),
    service: SupportService = Depends(get_support_service),
) -> NotificationPrefsOut:
    return await service.get_prefs(user_id)


@router.patch("/users/me/notification-preferences", response_model=NotificationPrefsOut)
async def patch_notification_prefs(
    body: NotificationPrefsIn,
    user_id: UUID = Depends(get_current_user_id),
    service: SupportService = Depends(get_support_service),
) -> NotificationPrefsOut:
    return await service.update_prefs(user_id, body)


@router.get("/support/tickets", response_model=TicketListOut)
async def list_my_tickets(
    user_id: UUID = Depends(get_current_user_id),
    service: SupportService = Depends(get_support_service),
) -> TicketListOut:
    return await service.list_mine(user_id)


@router.post("/support/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(
    body: TicketCreateIn,
    user_id: UUID = Depends(get_current_user_id),
    service: SupportService = Depends(get_support_service),
) -> TicketOut:
    return await service.create_ticket(body, user_id=user_id)


@router.get("/support/tickets/{ticket_id}", response_model=TicketOut)
async def get_my_ticket(
    ticket_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: SupportService = Depends(get_support_service),
) -> TicketOut:
    return await service.get_mine(ticket_id, user_id=user_id)


@router.post("/support/tickets/{ticket_id}/messages", response_model=TicketOut)
async def reply_my_ticket(
    ticket_id: UUID,
    body: TicketMessageIn,
    user_id: UUID = Depends(get_current_user_id),
    service: SupportService = Depends(get_support_service),
) -> TicketOut:
    return await service.reply_mine(ticket_id, body, user_id=user_id)
