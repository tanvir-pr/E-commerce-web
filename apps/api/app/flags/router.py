"""Public checkout method availability."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.flags.schemas import CheckoutMethodsOut
from app.flags.service import FeatureFlagService
from app.session import get_session

router = APIRouter(tags=["checkout-flags"])


def get_flag_service(session: AsyncSession = Depends(get_session)) -> FeatureFlagService:
    return FeatureFlagService(session)


@router.get("/checkout/methods", response_model=CheckoutMethodsOut)
async def checkout_methods(
    service: FeatureFlagService = Depends(get_flag_service),
) -> CheckoutMethodsOut:
    return await service.checkout_methods()
