"""Public catalog read routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.schemas import (
    AttributeListOut,
    CategoryDetailOut,
    CategoryListOut,
    CategoryTreeOut,
)
from app.catalog.service import CatalogService
from app.session import get_session

router = APIRouter(prefix="/catalog", tags=["catalog"])


def get_catalog_service(session: AsyncSession = Depends(get_session)) -> CatalogService:
    return CatalogService(session)


@router.get("/categories", response_model=list[CategoryTreeOut] | CategoryListOut)
async def list_categories(
    tree: bool = Query(default=True),
    service: CatalogService = Depends(get_catalog_service),
) -> list[CategoryTreeOut] | CategoryListOut:
    if tree:
        return await service.list_category_tree()
    return await service.list_categories_flat()


@router.get("/categories/{slug}", response_model=CategoryDetailOut)
async def get_category(
    slug: str,
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryDetailOut:
    return await service.get_category(slug)


@router.get("/attributes", response_model=AttributeListOut)
async def list_attributes(
    kind: str | None = Query(default=None),
    service: CatalogService = Depends(get_catalog_service),
) -> AttributeListOut:
    return await service.list_attributes(kind=kind)
