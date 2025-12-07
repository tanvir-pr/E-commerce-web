"""Customer return and invoice routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user_id
from app.orders.mailer import ArqOrderMailer
from app.returns.schemas import CreateReturnIn, LedgerListOut, ReturnListOut, ReturnRequestOut
from app.returns.service import ReturnsService
from app.session import get_session

router = APIRouter(tags=["returns"])


def get_returns_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> ReturnsService:
    return ReturnsService(session, mailer=ArqOrderMailer(request.app.state.arq))


@router.post("/orders/{order_id}/returns", response_model=ReturnRequestOut, status_code=201)
async def create_return(
    order_id: UUID,
    body: CreateReturnIn,
    user_id: UUID = Depends(get_current_user_id),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnRequestOut:
    return await service.create(order_id, body, user_id=user_id)


@router.get("/orders/{order_id}/returns", response_model=ReturnListOut)
async def list_returns(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnListOut:
    return await service.list_mine(order_id, user_id=user_id)


@router.post(
    "/orders/{order_id}/returns/{rma_id}/photos",
    response_model=ReturnRequestOut,
)
async def upload_return_photo(
    order_id: UUID,
    rma_id: UUID,
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    service: ReturnsService = Depends(get_returns_service),
) -> ReturnRequestOut:
    _ = order_id
    data = await file.read()
    return await service.add_photo(
        rma_id,
        user_id=user_id,
        data=data,
        content_type=file.content_type or "application/octet-stream",
    )


@router.get("/orders/{order_id}/ledger", response_model=LedgerListOut)
async def order_ledger(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReturnsService = Depends(get_returns_service),
) -> LedgerListOut:
    return await service.ledger_for_order(order_id, user_id=user_id)


@router.get("/orders/{order_id}/invoice.pdf")
async def order_invoice_pdf(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReturnsService = Depends(get_returns_service),
) -> Response:
    pdf, filename = await service.invoice_pdf(order_id, user_id=user_id)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
