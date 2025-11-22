"""Staff order list, fulfilment, and dashboard metrics."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.orders.mailer import ArqOrderMailer
from app.orders.schemas import DashboardMetricsOut, OrderListOut, OrderOut, TransitionIn
from app.orders.service import OrderService
from app.session import get_session

router = APIRouter(tags=["admin-orders"])


class PackIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


def get_order_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> OrderService:
    return OrderService(session, mailer=ArqOrderMailer(request.app.state.arq))


@router.get("/admin/metrics", response_model=DashboardMetricsOut)
async def admin_dashboard_metrics(
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> DashboardMetricsOut:
    return await service.dashboard_metrics()


@router.get("/admin/orders", response_model=OrderListOut)
async def admin_list_orders(
    status: str = Query(default="all"),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderListOut:
    return await service.admin_list(status=status)


@router.get("/admin/orders/{order_id}", response_model=OrderOut)
async def admin_get_order(
    order_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.admin_get(order_id)


@router.post("/admin/orders/{order_id}/pack", response_model=OrderOut)
async def admin_pack_order(
    order_id: UUID,
    body: PackIn | None = None,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.admin_pack(
        order_id,
        actor_user_id=actor_id,
        note=body.note if body else None,
    )


@router.post("/admin/orders/{order_id}/transition", response_model=OrderOut)
async def admin_transition_order(
    order_id: UUID,
    body: TransitionIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.admin_transition(order_id, body, actor_user_id=actor_id)
