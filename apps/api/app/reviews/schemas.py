"""Review and wishlist API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=120)
    body: str = Field(min_length=8, max_length=4000)
    skin_type: str | None = Field(default=None, max_length=32)


class ReviewOut(BaseModel):
    id: UUID
    product_id: UUID
    product_slug: str | None = None
    product_name: str | None = None
    rating: int
    title: str | None
    body: str
    skin_type: str | None
    is_verified: bool
    is_published: bool
    created_at: datetime
    author_display: str | None = None


class ReviewListOut(BaseModel):
    items: list[ReviewOut]
    rating_avg: float | None = None
    rating_count: int = 0
    can_review: bool = False


class ReviewModerationIn(BaseModel):
    is_published: bool
    note: str | None = Field(default=None, max_length=500)


class WishlistItemOut(BaseModel):
    id: UUID
    product_id: UUID
    product_slug: str
    product_name: str
    subtitle: str | None
    from_price_poisha: int | None
    created_at: datetime


class WishlistOut(BaseModel):
    items: list[WishlistItemOut]


class WishlistAddIn(BaseModel):
    product_id: UUID
