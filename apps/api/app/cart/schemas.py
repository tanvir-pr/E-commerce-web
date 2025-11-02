"""Cart API schemas. Money fields are integer poisha."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CartItemOut(BaseModel):
    id: UUID
    variant_id: UUID
    product_id: UUID
    product_slug: str
    product_name: str
    size_label: str | None
    shade_name: str | None
    spf: int | None
    sku: str
    qty: int
    unit_price_poisha: int
    line_total_poisha: int
    routine_step: str | None
    category_slug: str | None
    qty_available: int | None = None


class CartOut(BaseModel):
    id: UUID
    status: str
    item_count: int
    subtotal_poisha: int
    currency: str = "BDT"
    is_guest: bool
    updated_at: datetime
    last_activity_at: datetime
    items: list[CartItemOut]


class CartItemIn(BaseModel):
    variant_id: UUID
    qty: int = Field(default=1, ge=1, le=20)


class CartItemPatchIn(BaseModel):
    qty: int = Field(ge=0, le=20)


class UpsellProductOut(BaseModel):
    product_id: UUID
    slug: str
    name: str
    subtitle: str | None
    category_slug: str
    from_price_poisha: int | None
    reason: str


class UpsellOut(BaseModel):
    items: list[UpsellProductOut]
    missing_steps: list[str]


class AdminCartSummaryOut(BaseModel):
    id: UUID
    status: str
    user_id: UUID | None
    user_email: str | None
    is_guest: bool
    item_count: int
    subtotal_poisha: int
    last_activity_at: datetime
    created_at: datetime
    abandoned_at: datetime | None
    cleared_at: datetime | None


class AdminCartListOut(BaseModel):
    items: list[AdminCartSummaryOut]
    abandon_after_hours: int


class AdminCartDetailOut(AdminCartSummaryOut):
    items: list[CartItemOut]


class MessageOut(BaseModel):
    message: str
