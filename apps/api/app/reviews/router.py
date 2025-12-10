"""Public reviews and wishlist routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user_id, get_optional_user_id
from app.reviews.schemas import (
    ReviewIn,
    ReviewListOut,
    ReviewOut,
    WishlistAddIn,
    WishlistItemOut,
    WishlistOut,
)
from app.reviews.service import ReviewService
from app.session import get_session

router = APIRouter(tags=["reviews-wishlist"])


def get_review_service(session: AsyncSession = Depends(get_session)) -> ReviewService:
    return ReviewService(session)


@router.get("/catalog/products/{slug}/reviews", response_model=ReviewListOut)
async def list_product_reviews(
    slug: str,
    user_id: UUID | None = Depends(get_optional_user_id),
    service: ReviewService = Depends(get_review_service),
) -> ReviewListOut:
    return await service.list_for_product(slug, user_id=user_id)


@router.post(
    "/catalog/products/{slug}/reviews",
    response_model=ReviewOut,
    status_code=201,
)
async def create_product_review(
    slug: str,
    body: ReviewIn,
    user_id: UUID = Depends(get_current_user_id),
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    return await service.create_for_product(slug, body, user_id=user_id)


@router.get("/wishlist", response_model=WishlistOut)
async def get_wishlist(
    user_id: UUID = Depends(get_current_user_id),
    service: ReviewService = Depends(get_review_service),
) -> WishlistOut:
    return await service.list_wishlist(user_id)


@router.post("/wishlist", response_model=WishlistItemOut, status_code=201)
async def add_wishlist(
    body: WishlistAddIn,
    user_id: UUID = Depends(get_current_user_id),
    service: ReviewService = Depends(get_review_service),
) -> WishlistItemOut:
    return await service.add_wishlist(body, user_id=user_id)


@router.delete("/wishlist/{product_id}", status_code=204)
async def remove_wishlist(
    product_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: ReviewService = Depends(get_review_service),
) -> None:
    await service.remove_wishlist(product_id, user_id=user_id)
