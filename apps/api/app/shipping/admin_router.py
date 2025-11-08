"""Staff delivery zone configuration."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.session import get_session
from app.shipping.schemas import (
    DeliveryZoneIn,
    DeliveryZoneListOut,
    DeliveryZoneOut,
    DeliveryZonePatchIn,
    MessageOut,
)
from app.shipping.service import ShippingService

router = APIRouter(prefix="/admin/shipping", tags=["admin-shipping"])


def get_shipping_service(session: AsyncSession = Depends(get_session)) -> ShippingService:
    return ShippingService(session)


@router.get("/zones", response_model=DeliveryZoneListOut)
async def admin_list_zones(
    _staff: User = Depends(get_current_staff_user),
    service: ShippingService = Depends(get_shipping_service),
) -> DeliveryZoneListOut:
    return await service.admin_list()


@router.get("/zones/{zone_id}", response_model=DeliveryZoneOut)
async def admin_get_zone(
    zone_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: ShippingService = Depends(get_shipping_service),
) -> DeliveryZoneOut:
    return await service.admin_get(zone_id)


@router.post("/zones", response_model=DeliveryZoneOut, status_code=201)
async def admin_create_zone(
    body: DeliveryZoneIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ShippingService = Depends(get_shipping_service),
) -> DeliveryZoneOut:
    return await service.create_zone(body, actor_user_id=actor_id)


@router.patch("/zones/{zone_id}", response_model=DeliveryZoneOut)
async def admin_patch_zone(
    zone_id: UUID,
    body: DeliveryZonePatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ShippingService = Depends(get_shipping_service),
) -> DeliveryZoneOut:
    return await service.patch_zone(zone_id, body, actor_user_id=actor_id)


@router.delete("/zones/{zone_id}", response_model=MessageOut)
async def admin_delete_zone(
    zone_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ShippingService = Depends(get_shipping_service),
) -> MessageOut:
    await service.delete_zone(zone_id, actor_user_id=actor_id)
    return MessageOut(message="Delivery zone deleted.")
