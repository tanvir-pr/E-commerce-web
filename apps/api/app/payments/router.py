"""Customer payment routes — start hosted redirect and validate return."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user_id
from app.orders.mailer import ArqOrderMailer
from app.payments.schemas import PayStartOut, PayValidateIn, PayValidateOut
from app.payments.service import PaymentService
from app.session import get_session

router = APIRouter(tags=["payments"])


def get_payment_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> PaymentService:
    return PaymentService(
        session, mailer=ArqOrderMailer(request.app.state.arq)
    )


@router.post("/orders/{order_id}/pay", response_model=PayStartOut)
async def start_order_payment(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> PayStartOut:
    return await service.start_pay(order_id, user_id=user_id)


@router.post("/payments/{method}/validate", response_model=PayValidateOut)
async def validate_payment(
    method: str,
    body: PayValidateIn,
    user_id: UUID = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> PayValidateOut:
    payload: dict[str, Any] = body.model_dump(exclude_none=True)
    return await service.validate_owned_or_forbidden(
        method, payload, user_id=user_id
    )
