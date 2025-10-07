"""Staff catalog write routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.schemas import (
    AttributeIn,
    AttributeListOut,
    AttributeOut,
    AttributePatchIn,
    CategoryDetailOut,
    CategoryIn,
    CategoryPatchIn,
    CategoryTreeOut,
    MessageOut,
)
from app.catalog.service import CatalogService
from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.session import get_session

router = APIRouter(prefix="/admin/catalog", tags=["admin-catalog"])


def get_catalog_service(session: AsyncSession = Depends(get_session)) -> CatalogService:
    return CatalogService(session)


@router.get("/categories", response_model=list[CategoryTreeOut])
async def admin_list_categories(
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> list[CategoryTreeOut]:
    return await service.list_category_tree(include_inactive=True)


@router.post("/categories", response_model=CategoryDetailOut, status_code=201)
async def admin_create_category(
    body: CategoryIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryDetailOut:
    return await service.create_category(body, actor_user_id=actor_id)


@router.patch("/categories/{category_id}", response_model=CategoryDetailOut)
async def admin_patch_category(
    category_id: UUID,
    body: CategoryPatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> CategoryDetailOut:
    return await service.patch_category(category_id, body, actor_user_id=actor_id)


@router.delete("/categories/{category_id}", response_model=MessageOut)
async def admin_delete_category(
    category_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> MessageOut:
    await service.delete_category(category_id, actor_user_id=actor_id)
    return MessageOut(message="Category soft-deleted.")


@router.get("/attributes", response_model=AttributeListOut)
async def admin_list_attributes(
    kind: str | None = None,
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> AttributeListOut:
    return await service.list_attributes(kind=kind, include_inactive=True)


@router.post("/attributes", response_model=AttributeOut, status_code=201)
async def admin_create_attribute(
    body: AttributeIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> AttributeOut:
    return await service.create_attribute(body, actor_user_id=actor_id)


@router.patch("/attributes/{attribute_id}", response_model=AttributeOut)
async def admin_patch_attribute(
    attribute_id: UUID,
    body: AttributePatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CatalogService = Depends(get_catalog_service),
) -> AttributeOut:
    return await service.patch_attribute(attribute_id, body, actor_user_id=actor_id)
