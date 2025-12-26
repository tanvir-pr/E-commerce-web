"""Staff feature flag management."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.flags.schemas import FeatureFlagListOut, FeatureFlagOut, FeatureFlagPatchIn
from app.flags.service import FeatureFlagService
from app.models.user import User
from app.session import get_session

router = APIRouter(tags=["admin-flags"])


def get_flag_service(session: AsyncSession = Depends(get_session)) -> FeatureFlagService:
    return FeatureFlagService(session)


@router.get("/admin/feature-flags", response_model=FeatureFlagListOut)
async def list_flags(
    _staff: User = Depends(get_current_staff_user),
    service: FeatureFlagService = Depends(get_flag_service),
) -> FeatureFlagListOut:
    return await service.list_admin()


@router.patch("/admin/feature-flags/{flag_id}", response_model=FeatureFlagOut)
async def patch_flag(
    flag_id: UUID,
    body: FeatureFlagPatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: FeatureFlagService = Depends(get_flag_service),
) -> FeatureFlagOut:
    return await service.patch(flag_id, body, actor_user_id=actor_id)
