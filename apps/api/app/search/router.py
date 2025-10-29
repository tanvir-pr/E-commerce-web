"""Public catalog search routes."""

from typing import Literal

from fastapi import APIRouter, Query

from app.search.schemas import SearchOut, SuggestOut
from app.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])

SortParam = Literal["relevance", "name_asc", "name_desc", "price_asc", "price_desc"]


def get_search_service() -> SearchService:
    return SearchService()


@router.get("", response_model=SearchOut)
async def search_products(
    q: str = Query(default="", max_length=200),
    concern: str | None = Query(default=None, max_length=80),
    ingredient: str | None = Query(default=None, max_length=80),
    skin_type: str | None = Query(default=None, max_length=80),
    category: str | None = Query(default=None, max_length=80),
    min_price_poisha: int | None = Query(default=None, ge=0),
    max_price_poisha: int | None = Query(default=None, ge=0),
    sort: SortParam = Query(default="relevance"),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SearchOut:
    service = get_search_service()
    return await service.search(
        q=q,
        concern=concern,
        ingredient=ingredient,
        skin_type=skin_type,
        category=category,
        min_price_poisha=min_price_poisha,
        max_price_poisha=max_price_poisha,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get("/suggest", response_model=SuggestOut)
async def suggest_products(
    q: str = Query(default="", max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
) -> SuggestOut:
    service = get_search_service()
    return await service.suggest(q=q, limit=limit)
