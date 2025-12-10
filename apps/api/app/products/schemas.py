"""Product API schemas. Money fields are integer poisha (1 BDT = 100 poisha)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

ProductStatus = Literal["draft", "published", "archived"]
RoutineStep = Literal["am", "pm", "both"]


class VariantOut(BaseModel):
    id: UUID
    sku: str
    size_label: str | None
    shade_name: str | None
    shade_hex: str | None
    spf: int | None
    price_poisha: int
    compare_at_poisha: int | None
    barcode: str | None
    weight_grams: int | None
    is_active: bool
    sort_order: int


class VariantIn(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    size_label: str | None = Field(default=None, max_length=64)
    shade_name: str | None = Field(default=None, max_length=64)
    shade_hex: str | None = Field(default=None, max_length=7)
    spf: int | None = Field(default=None, ge=0, le=100)
    price_poisha: int = Field(ge=0)
    compare_at_poisha: int | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=64)
    weight_grams: int | None = Field(default=None, ge=0)
    is_active: bool = True
    sort_order: int = 0

    @field_validator("shade_hex")
    @classmethod
    def validate_hex(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not value.startswith("#") or len(value) != 7:
            raise ValueError("shade_hex must look like #RRGGBB")
        return value.upper()


class VariantPatchIn(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    size_label: str | None = Field(default=None, max_length=64)
    shade_name: str | None = Field(default=None, max_length=64)
    shade_hex: str | None = Field(default=None, max_length=7)
    spf: int | None = Field(default=None, ge=0, le=100)
    price_poisha: int | None = Field(default=None, ge=0)
    compare_at_poisha: int | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=64)
    weight_grams: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    sort_order: int | None = None


class ProductAttributeRef(BaseModel):
    id: UUID
    kind: str
    slug: str
    name: str


class ProductSummaryOut(BaseModel):
    id: UUID
    category_id: UUID
    category_slug: str | None = None
    slug: str
    name: str
    subtitle: str | None
    routine_step: str | None
    status: str
    from_price_poisha: int | None
    published_at: datetime | None


class ProductImageSummaryOut(BaseModel):
    id: UUID
    slot: str
    alt_text: str | None
    sort_order: int
    width: int
    height: int
    thumb_webp_url: str | None = None
    thumb_avif_url: str | None = None
    card_webp_url: str | None = None
    card_avif_url: str | None = None
    full_webp_url: str | None = None
    full_avif_url: str | None = None


class ProductOut(BaseModel):
    id: UUID
    category_id: UUID
    category_slug: str | None = None
    slug: str
    name: str
    subtitle: str | None
    description: str | None
    how_to_use: str | None
    ingredients_text: str | None
    warnings: str | None
    routine_step: str | None
    pao_months: int | None
    shelf_life_months: int | None
    status: str
    published_at: datetime | None
    attributes: list[ProductAttributeRef]
    variants: list[VariantOut]
    images: list[ProductImageSummaryOut] = []
    rating_avg: float | None = None
    rating_count: int = 0


class ProductIn(BaseModel):
    category_id: UUID
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=240)
    description: str | None = None
    how_to_use: str | None = None
    ingredients_text: str | None = None
    warnings: str | None = None
    routine_step: RoutineStep | None = None
    pao_months: int | None = Field(default=None, ge=1, le=120)
    shelf_life_months: int | None = Field(default=None, ge=1, le=120)
    status: ProductStatus = "draft"
    attribute_ids: list[UUID] = []
    variants: list[VariantIn] = Field(default_factory=list, min_length=0)


class ProductPatchIn(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=240)
    description: str | None = None
    how_to_use: str | None = None
    ingredients_text: str | None = None
    warnings: str | None = None
    routine_step: RoutineStep | None = None
    pao_months: int | None = Field(default=None, ge=1, le=120)
    shelf_life_months: int | None = Field(default=None, ge=1, le=120)
    status: ProductStatus | None = None
    attribute_ids: list[UUID] | None = None


class ProductListOut(BaseModel):
    items: list[ProductSummaryOut]


class BulkStatusIn(BaseModel):
    product_ids: list[UUID] = Field(min_length=1, max_length=100)
    status: ProductStatus


class BulkStatusOut(BaseModel):
    updated: int
    status: ProductStatus


class MessageOut(BaseModel):
    message: str
