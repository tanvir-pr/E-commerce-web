"""Customer order routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user_id
from app.orders.mailer import ArqOrderMailer
from app.orders.schemas import OrderListOut, OrderOut, PlaceOrderIn, TransitionIn
from app.orders.service import OrderService
from app.security.cookies import CART_COOKIE, clear_cart_cookie
from app.session import get_session

router = APIRouter(tags=["orders"])


def get_order_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> OrderService:
    return OrderService(session, mailer=ArqOrderMailer(request.app.state.arq))


def _guest_token(request: Request) -> str | None:
    return request.cookies.get(CART_COOKIE)


@router.post("/checkout/place", response_model=OrderOut, status_code=201)
async def place_order(
    body: PlaceOrderIn,
    request: Request,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    order = await service.place(body, user_id=user_id, guest_token=_guest_token(request))
    clear_cart_cookie(response)
    return order


@router.get("/orders", response_model=OrderListOut)
async def list_my_orders(
    user_id: UUID = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrderListOut:
    return await service.list_mine(user_id)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_my_order(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.get_mine(order_id, user_id=user_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_my_order(
    order_id: UUID,
    body: TransitionIn | None = None,
    user_id: UUID = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    note = body.note if body else None
    return await service.cancel_mine(order_id, user_id=user_id, note=note)
