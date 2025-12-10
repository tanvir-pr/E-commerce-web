"""Staff review moderation."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.reviews.schemas import ReviewListOut, ReviewModerationIn, ReviewOut
from app.reviews.service import ReviewService
from app.session import get_session

router = APIRouter(tags=["admin-reviews"])


def get_review_service(session: AsyncSession = Depends(get_session)) -> ReviewService:
    return ReviewService(session)


@router.get("/admin/reviews", response_model=ReviewListOut)
async def list_reviews(
    published: bool | None = Query(default=None),
    _staff: User = Depends(get_current_staff_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListOut:
    return await service.admin_list(published=published)


@router.patch("/admin/reviews/{review_id}", response_model=ReviewOut)
async def moderate_review(
    review_id: UUID,
    body: ReviewModerationIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    return await service.moderate(review_id, body, actor_user_id=actor_id)
