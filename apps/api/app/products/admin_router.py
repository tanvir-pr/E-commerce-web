"""Staff product write routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.products.schemas import (
    MessageOut,
    ProductIn,
    ProductListOut,
    ProductOut,
    ProductPatchIn,
    VariantIn,
    VariantOut,
    VariantPatchIn,
)
from app.products.service import ProductService
from app.session import get_session

router = APIRouter(prefix="/admin/catalog", tags=["admin-products"])


def get_product_service(session: AsyncSession = Depends(get_session)) -> ProductService:
    return ProductService(session)


@router.get("/products", response_model=ProductListOut)
async def admin_list_products(
    status: str | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> ProductListOut:
    return await service.list_admin(status=status, category_id=category_id)


@router.get("/products/{product_id}", response_model=ProductOut)
async def admin_get_product(
    product_id: UUID,
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> ProductOut:
    return await service.get_admin(product_id)


@router.post("/products", response_model=ProductOut, status_code=201)
async def admin_create_product(
    body: ProductIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> ProductOut:
    return await service.create(body, actor_user_id=actor_id)


@router.patch("/products/{product_id}", response_model=ProductOut)
async def admin_patch_product(
    product_id: UUID,
    body: ProductPatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> ProductOut:
    return await service.patch(product_id, body, actor_user_id=actor_id)


@router.delete("/products/{product_id}", response_model=MessageOut)
async def admin_delete_product(
    product_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> MessageOut:
    await service.soft_delete(product_id, actor_user_id=actor_id)
    return MessageOut(message="Product soft-deleted.")


@router.post(
    "/products/{product_id}/variants",
    response_model=VariantOut,
    status_code=201,
)
async def admin_add_variant(
    product_id: UUID,
    body: VariantIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> VariantOut:
    return await service.add_variant(product_id, body, actor_user_id=actor_id)


@router.patch("/variants/{variant_id}", response_model=VariantOut)
async def admin_patch_variant(
    variant_id: UUID,
    body: VariantPatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> VariantOut:
    return await service.patch_variant(variant_id, body, actor_user_id=actor_id)


@router.delete("/variants/{variant_id}", response_model=MessageOut)
async def admin_delete_variant(
    variant_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: ProductService = Depends(get_product_service),
) -> MessageOut:
    await service.delete_variant(variant_id, actor_user_id=actor_id)
    return MessageOut(message="Variant deleted.")
