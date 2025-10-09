"""Public product read routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.products.schemas import ProductListOut, ProductOut
from app.products.service import ProductService
from app.session import get_session

router = APIRouter(prefix="/catalog", tags=["catalog-products"])


def get_product_service(session: AsyncSession = Depends(get_session)) -> ProductService:
    return ProductService(session)


@router.get("/products", response_model=ProductListOut)
async def list_products(
    category: str | None = Query(default=None, description="Category slug"),
    attribute_kind: str | None = Query(default=None),
    attribute: str | None = Query(default=None, description="Attribute slug"),
    service: ProductService = Depends(get_product_service),
) -> ProductListOut:
    return await service.list_public(
        category_slug=category,
        attribute_kind=attribute_kind,
        attribute_slug=attribute,
    )


@router.get("/products/{slug}", response_model=ProductOut)
async def get_product(
    slug: str,
    service: ProductService = Depends(get_product_service),
) -> ProductOut:
    return await service.get_public(slug)
