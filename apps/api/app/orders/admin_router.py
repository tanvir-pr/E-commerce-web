"""Staff order list, fulfilment, and dashboard metrics."""

from datetime import date, datetime, time, timedelta
from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
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


def _day_start(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=UTC)


def _day_end_exclusive(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=UTC)


@router.get("/admin/metrics", response_model=DashboardMetricsOut)
async def admin_dashboard_metrics(
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> DashboardMetricsOut:
    return await service.dashboard_metrics(
        range_from=_day_start(range_from),
        range_to=_day_end_exclusive(range_to) if range_to else None,
    )


@router.get("/admin/metrics.csv")
async def admin_dashboard_metrics_csv(
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> Response:
    body = await service.metrics_csv(
        range_from=_day_start(range_from),
        range_to=_day_end_exclusive(range_to) if range_to else None,
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="metrics.csv"'},
    )


@router.get("/admin/orders", response_model=OrderListOut)
async def admin_list_orders(
    status: str = Query(default="all"),
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> OrderListOut:
    return await service.admin_list(
        status=status,
        since=_day_start(range_from),
        until=_day_end_exclusive(range_to) if range_to else None,
    )


@router.get("/admin/orders.csv")
async def admin_orders_csv(
    status: str = Query(default="all"),
    range_from: date | None = Query(default=None, alias="from"),
    range_to: date | None = Query(default=None, alias="to"),
    _staff: User = Depends(get_current_staff_user),
    service: OrderService = Depends(get_order_service),
) -> Response:
    body = await service.orders_csv(
        status=status,
        since=_day_start(range_from),
        until=_day_end_exclusive(range_to) if range_to else None,
    )
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="orders.csv"'},
    )


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
