"""Public shipping zones and quote."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.session import get_session
from app.shipping.schemas import DeliveryZoneSummaryOut, ShippingQuoteIn, ShippingQuoteOut
from app.shipping.service import ShippingService

router = APIRouter(prefix="/shipping", tags=["shipping"])


def get_shipping_service(session: AsyncSession = Depends(get_session)) -> ShippingService:
    return ShippingService(session)


@router.get("/zones", response_model=list[DeliveryZoneSummaryOut])
async def list_zones(
    service: ShippingService = Depends(get_shipping_service),
) -> list[DeliveryZoneSummaryOut]:
    return await service.list_public_zones()


@router.post("/quote", response_model=ShippingQuoteOut)
async def quote_shipping(
    body: ShippingQuoteIn,
    service: ShippingService = Depends(get_shipping_service),
) -> ShippingQuoteOut:
    return await service.quote(body)
