"""Catalog API schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AttributeKind = Literal["skin_type", "concern", "ingredient", "texture", "claim"]


class AttributeOut(BaseModel):
    id: UUID
    kind: str
    slug: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool


class AttributeIn(BaseModel):
    kind: AttributeKind
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True


class AttributePatchIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: UUID
    parent_id: UUID | None
    slug: str
    name: str
    description: str | None
    sort_order: int
    is_active: bool
    attribute_ids: list[UUID] = []


class CategoryTreeOut(CategoryOut):
    children: list["CategoryTreeOut"] = []


class CategoryDetailOut(CategoryOut):
    attributes: list[AttributeOut] = []


class CategoryIn(BaseModel):
    parent_id: UUID | None = None
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    sort_order: int = 0
    is_active: bool = True
    attribute_ids: list[UUID] = []


class CategoryPatchIn(BaseModel):
    parent_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    attribute_ids: list[UUID] | None = None


class MessageOut(BaseModel):
    message: str


class AttributeListOut(BaseModel):
    items: list[AttributeOut]


class CategoryListOut(BaseModel):
    items: list[CategoryOut]


CategoryTreeOut.model_rebuild()

