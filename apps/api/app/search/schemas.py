"""Search API schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class FacetValueOut(BaseModel):
    value: str
    count: int


class SearchHitOut(BaseModel):
    id: UUID
    slug: str
    name: str
    subtitle: str | None = None
    category_slug: str | None = None
    category_name: str | None = None
    routine_step: str | None = None
    from_price_poisha: int | None = None
    skin_types: list[str] = []
    concerns: list[str] = []
    ingredients: list[str] = []


class SearchOut(BaseModel):
    query: str
    total: int
    offset: int
    limit: int
    processing_time_ms: int | None = None
    items: list[SearchHitOut]
    facets: dict[str, list[FacetValueOut]]


class ReindexOut(BaseModel):
    indexed: int = Field(ge=0)
    removed: int = Field(ge=0)
    message: str
