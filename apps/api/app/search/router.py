"""Public catalog search routes."""

from fastapi import APIRouter, Query

from app.search.schemas import SearchOut
from app.search.service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def get_search_service() -> SearchService:
    return SearchService()


@router.get("", response_model=SearchOut)
async def search_products(
    q: str = Query(default="", max_length=200),
    concern: str | None = Query(default=None, max_length=80),
    ingredient: str | None = Query(default=None, max_length=80),
    skin_type: str | None = Query(default=None, max_length=80),
    category: str | None = Query(default=None, max_length=80),
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
        limit=limit,
        offset=offset,
    )
