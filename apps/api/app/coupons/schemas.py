"""Coupon API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CouponIn(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    discount_type: str = Field(pattern="^(percent|fixed)$")
    value: int = Field(ge=1)
    min_spend_poisha: int | None = Field(default=None, ge=0)
    category_id: UUID | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_redemptions: int | None = Field(default=None, ge=1)
    max_per_user: int | None = Field(default=None, ge=1)
    is_active: bool = True


class CouponOut(BaseModel):
    id: UUID
    code: str
    discount_type: str
    value: int
    min_spend_poisha: int | None
    category_id: UUID | None
    starts_at: datetime | None
    expires_at: datetime | None
    max_redemptions: int | None
    max_per_user: int | None
    is_active: bool
    redemption_count: int = 0
    created_at: datetime


class CouponListOut(BaseModel):
    items: list[CouponOut]


class CouponApplyResult(BaseModel):
    ok: bool
    code: str | None = None
    coupon_id: UUID | None = None
    discount_poisha: int = 0
    message: str | None = None
