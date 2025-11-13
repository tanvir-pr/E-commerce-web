"""Staff order list and status transitions."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.orders.schemas import OrderListOut, OrderOut, TransitionIn
from app.orders.service import OrderService
from app.session import get_session

router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(session)


@router.get("", response_model=OrderListOut)
async def admin_list_orders(
    status: str = Query(default="all"),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderListOut:
    return await service.admin_list(status=status)


@router.get("/{order_id}", response_model=OrderOut)
async def admin_get_order(
    order_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.admin_get(order_id)


@router.post("/{order_id}/transition", response_model=OrderOut)
async def admin_transition_order(
    order_id: UUID,
    body: TransitionIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.admin_transition(order_id, body, actor_user_id=actor_id)
