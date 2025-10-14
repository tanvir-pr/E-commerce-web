"""Media API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ImageSlot = Literal["product", "texture", "lifestyle"]


class ImageDerivativeOut(BaseModel):
    size_key: str
    width: int
    height: int
    webp_url: str
    avif_url: str | None


class ProductImageOut(BaseModel):
    id: UUID
    product_id: UUID
    slot: str
    alt_text: str | None
    sort_order: int
    width: int
    height: int
    derivatives: list[ImageDerivativeOut]
    created_at: datetime


class ProductImagePatchIn(BaseModel):
    alt_text: str | None = Field(default=None, max_length=240)
    sort_order: int | None = None
    slot: ImageSlot | None = None


class MessageOut(BaseModel):
    message: str
