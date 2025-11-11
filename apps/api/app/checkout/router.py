"""Authenticated checkout quote routes (no order placement yet)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.checkout.schemas import CheckoutQuoteIn, CheckoutQuoteOut
from app.checkout.service import CheckoutService
from app.deps import get_current_user_id
from app.security.cookies import CART_COOKIE, clear_cart_cookie
from app.session import get_session

router = APIRouter(prefix="/checkout", tags=["checkout"])


def get_checkout_service(session: AsyncSession = Depends(get_session)) -> CheckoutService:
    return CheckoutService(session)


def _guest_token(request: Request) -> str | None:
    return request.cookies.get(CART_COOKIE)


@router.post("/quote", response_model=CheckoutQuoteOut)
async def checkout_quote(
    body: CheckoutQuoteIn,
    request: Request,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    service: CheckoutService = Depends(get_checkout_service),
) -> CheckoutQuoteOut:
    quote = await service.quote(
        body, user_id=user_id, guest_token=_guest_token(request)
    )
    # Guest cart merges into the user cart during quote; drop guest cookie.
    clear_cart_cookie(response)
    return quote


@router.post("/reprice", response_model=CheckoutQuoteOut)
async def checkout_reprice(
    body: CheckoutQuoteIn,
    request: Request,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    service: CheckoutService = Depends(get_checkout_service),
) -> CheckoutQuoteOut:
    """Same as /quote — refresh after bag edits."""
    quote = await service.quote(
        body, user_id=user_id, guest_token=_guest_token(request)
    )
    clear_cart_cookie(response)
    return quote
