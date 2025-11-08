"""Shipping API schemas. Money fields are integer poisha."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WeightTierOut(BaseModel):
    id: UUID
    max_weight_grams: int
    charge_poisha: int


class WeightTierIn(BaseModel):
    max_weight_grams: int = Field(ge=1, le=1_000_000)
    charge_poisha: int = Field(ge=0, le=50_000_000)


class DeliveryZoneOut(BaseModel):
    id: UUID
    slug: str
    name: str
    match_districts: list[str]
    is_default: bool
    is_active: bool
    sort_order: int
    free_shipping_threshold_poisha: int | None
    created_at: datetime
    updated_at: datetime
    tiers: list[WeightTierOut]


class DeliveryZoneSummaryOut(BaseModel):
    id: UUID
    slug: str
    name: str
    is_default: bool
    sort_order: int


class DeliveryZoneListOut(BaseModel):
    items: list[DeliveryZoneOut]
    free_shipping_threshold_poisha: int
    default_variant_weight_grams: int


class DeliveryZoneIn(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=128)
    match_districts: list[str] = Field(default_factory=list)
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    free_shipping_threshold_poisha: int | None = Field(default=None, ge=0)
    tiers: list[WeightTierIn] = Field(default_factory=list, min_length=1)


class DeliveryZonePatchIn(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    match_districts: list[str] | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    free_shipping_threshold_poisha: int | None = Field(default=None, ge=0)
    tiers: list[WeightTierIn] | None = Field(default=None, min_length=1)


class ShippingQuoteLineIn(BaseModel):
    variant_id: UUID
    qty: int = Field(ge=1, le=20)


class ShippingQuoteIn(BaseModel):
    district: str | None = Field(default=None, max_length=128)
    city: str | None = Field(default=None, max_length=128)
    weight_grams: int | None = Field(default=None, ge=0, le=1_000_000)
    subtotal_poisha: int = Field(default=0, ge=0)
    lines: list[ShippingQuoteLineIn] = Field(default_factory=list)


class ShippingQuoteOut(BaseModel):
    zone_id: UUID
    zone_slug: str
    zone_name: str
    total_weight_grams: int
    charge_poisha: int
    currency: str = "BDT"
    free_shipping_applied: bool
    free_shipping_threshold_poisha: int
    matched_by: str


class MessageOut(BaseModel):
    message: str
