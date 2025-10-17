"""Inventory API schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StockBatchOut(BaseModel):
    id: UUID
    variant_id: UUID
    lot_code: str | None
    qty_on_hand: int
    expires_on: date | None
    received_at: datetime
    note: str | None


class VariantStockOut(BaseModel):
    variant_id: UUID
    sku: str
    product_id: UUID
    qty_on_hand: int
    batch_count: int
    nearest_expiry: date | None
    batches: list[StockBatchOut]


class ReceiptIn(BaseModel):
    variant_id: UUID
    qty: int = Field(gt=0)
    lot_code: str | None = Field(default=None, max_length=64)
    expires_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class AdjustmentIn(BaseModel):
    batch_id: UUID
    qty_delta: int = Field(description="Positive increases stock; negative decreases.")
    note: str | None = Field(default=None, max_length=500)


class FefoIssueIn(BaseModel):
    variant_id: UUID
    qty: int = Field(gt=0)
    reason: str = Field(default="fefo_issue", max_length=32)
    note: str | None = Field(default=None, max_length=500)


class FefoAllocationLine(BaseModel):
    batch_id: UUID
    lot_code: str | None
    expires_on: date | None
    qty: int


class FefoPreviewOut(BaseModel):
    variant_id: UUID
    requested_qty: int
    allocated_qty: int
    shortfall: int
    lines: list[FefoAllocationLine]


class StockMovementOut(BaseModel):
    id: UUID
    variant_id: UUID
    batch_id: UUID | None
    qty_delta: int
    reason: str
    note: str | None
    actor_user_id: UUID | None
    created_at: datetime


class StockMovementListOut(BaseModel):
    items: list[StockMovementOut]


class LowStockItemOut(BaseModel):
    variant_id: UUID
    sku: str
    product_id: UUID
    product_slug: str | None
    qty_on_hand: int
    nearest_expiry: date | None


class LowStockListOut(BaseModel):
    items: list[LowStockItemOut]
    threshold: int
