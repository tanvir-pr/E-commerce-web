"""Staff inventory routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id, get_current_user_row
from app.inventory.schemas import (
    AdjustmentIn,
    FefoIssueIn,
    FefoPreviewOut,
    LowStockListOut,
    ReceiptIn,
    StockMovementListOut,
    VariantStockOut,
)
from app.inventory.service import InventoryService
from app.models.user import User
from app.rbac import ensure_permission
from app.session import get_session

router = APIRouter(prefix="/admin/inventory", tags=["admin-inventory"])


def get_inventory_service(
    session: AsyncSession = Depends(get_session),
) -> InventoryService:
    return InventoryService(session)


async def require_warehouse(
    user: User = Depends(get_current_user_row),
    session: AsyncSession = Depends(get_session),
) -> User:
    await ensure_permission(session, user, "warehouse")
    return user


@router.get("/variants/{variant_id}", response_model=VariantStockOut)
async def get_variant_stock(
    variant_id: UUID,
    include_empty: bool = Query(default=False),
    _staff: User = Depends(get_current_staff_user),
    service: InventoryService = Depends(get_inventory_service),
) -> VariantStockOut:
    return await service.get_variant_stock(variant_id, include_empty=include_empty)


@router.get("/variants/{variant_id}/movements", response_model=StockMovementListOut)
async def list_movements(
    variant_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    _staff: User = Depends(get_current_staff_user),
    service: InventoryService = Depends(get_inventory_service),
) -> StockMovementListOut:
    return await service.list_movements(variant_id, limit=limit)


@router.get("/low-stock", response_model=LowStockListOut)
async def low_stock(
    threshold: int = Query(default=10, ge=0),
    _staff: User = Depends(get_current_staff_user),
    service: InventoryService = Depends(get_inventory_service),
) -> LowStockListOut:
    return await service.low_stock(threshold=threshold)


@router.get("/fefo-preview", response_model=FefoPreviewOut)
async def fefo_preview(
    variant_id: UUID = Query(...),
    qty: int = Query(..., gt=0),
    _staff: User = Depends(get_current_staff_user),
    service: InventoryService = Depends(get_inventory_service),
) -> FefoPreviewOut:
    return await service.preview_fefo(variant_id, qty)


@router.post("/receipts", response_model=VariantStockOut, status_code=201)
async def create_receipt(
    body: ReceiptIn,
    actor_id: UUID = Depends(get_current_user_id),
    _warehouse: User = Depends(require_warehouse),
    service: InventoryService = Depends(get_inventory_service),
) -> VariantStockOut:
    return await service.receive(body, actor_user_id=actor_id)


@router.post("/adjustments", response_model=VariantStockOut)
async def create_adjustment(
    body: AdjustmentIn,
    actor_id: UUID = Depends(get_current_user_id),
    _warehouse: User = Depends(require_warehouse),
    service: InventoryService = Depends(get_inventory_service),
) -> VariantStockOut:
    return await service.adjust(body, actor_user_id=actor_id)


@router.post("/fefo-issue", response_model=FefoPreviewOut)
async def fefo_issue(
    body: FefoIssueIn,
    actor_id: UUID = Depends(get_current_user_id),
    _warehouse: User = Depends(require_warehouse),
    service: InventoryService = Depends(get_inventory_service),
) -> FefoPreviewOut:
    return await service.issue_fefo(body, actor_user_id=actor_id)
