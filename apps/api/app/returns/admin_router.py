"""Staff return review routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.orders.mailer import ArqOrderMailer
from app.returns.schemas import LedgerListOut, ReturnListOut, ReturnRequestOut, ReviewReturnIn
from app.returns.service import ReturnsService
from app.session import get_session

router = APIRouter(tags=["admin-returns"])


def get_returns_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> ReturnsService:
    return ReturnsService(session, mailer=ArqOrderMailer(request.app.state.arq))


@router.get("/admin/returns", response_model=ReturnListOut)
async def admin_list_returns(
    status: str = Query(default="pending"),
    _staff: User = Depends(get_current_staff_user),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnListOut:
    return await service.admin_list(status=status)


@router.get("/admin/returns/{rma_id}", response_model=ReturnRequestOut)
async def admin_get_return(
    rma_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnRequestOut:
    return await service.admin_get(rma_id)


@router.post("/admin/returns/{rma_id}/approve", response_model=ReturnRequestOut)
async def admin_approve_return(
    rma_id: UUID,
    body: ReviewReturnIn | None = None,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnRequestOut:
    return await service.approve(
        rma_id,
        actor_user_id=actor_id,
        staff_note=body.staff_note if body else None,
    )


@router.post("/admin/returns/{rma_id}/reject", response_model=ReturnRequestOut)
async def admin_reject_return(
    rma_id: UUID,
    body: ReviewReturnIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnRequestOut:
    return await service.reject(
        rma_id, actor_user_id=actor_id, staff_note=body.staff_note
    )


@router.get("/admin/orders/{order_id}/ledger", response_model=LedgerListOut)
async def admin_order_ledger(
    order_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: ReturnsService = Depends(get_returns_service),
) -> LedgerListOut:
    return await service.ledger_for_order(order_id, staff=True)


@router.get("/admin/orders/{order_id}/invoice.pdf")
async def admin_order_invoice(
    order_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: ReturnsService = Depends(get_returns_service),
) -> Response:
    pdf, filename = await service.invoice_pdf(order_id, staff=True)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
