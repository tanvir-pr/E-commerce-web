"""Staff cart inspection and clear."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.cart.schemas import AdminCartDetailOut, AdminCartListOut, MessageOut
from app.cart.service import CartService
from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.session import get_session

router = APIRouter(prefix="/admin/carts", tags=["admin-carts"])


def get_cart_service(session: AsyncSession = Depends(get_session)) -> CartService:
    return CartService(session)


@router.get("", response_model=AdminCartListOut)
async def list_carts(
    status: str = Query(default="all"),
    _staff: User = Depends(get_current_staff_user),
    service: CartService = Depends(get_cart_service),
) -> AdminCartListOut:
    return await service.admin_list(status=status)


@router.get("/{cart_id}", response_model=AdminCartDetailOut)
async def get_cart(
    cart_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: CartService = Depends(get_cart_service),
) -> AdminCartDetailOut:
    return await service.admin_get(cart_id)


@router.delete("/{cart_id}", response_model=MessageOut)
async def clear_cart(
    cart_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CartService = Depends(get_cart_service),
) -> MessageOut:
    await service.admin_clear(cart_id, actor_user_id=actor_id)
    return MessageOut(message="Cart cleared.")
