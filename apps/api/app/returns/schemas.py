"""Return / ledger / invoice schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReturnItemIn(BaseModel):
    order_item_id: UUID
    qty: int = Field(ge=1, le=100)


class CreateReturnIn(BaseModel):
    reason_code: str = Field(max_length=32)
    customer_note: str | None = Field(default=None, max_length=2000)
    items: list[ReturnItemIn] = Field(min_length=1)


class ReviewReturnIn(BaseModel):
    staff_note: str | None = Field(default=None, max_length=2000)


class ReturnItemOut(BaseModel):
    id: UUID
    order_item_id: UUID
    qty: int
    unit_price_poisha: int


class ReturnPhotoOut(BaseModel):
    id: UUID
    relative_path: str
    url: str
    content_type: str
    created_at: datetime


class ReturnRequestOut(BaseModel):
    id: UUID
    order_id: UUID
    order_number: str | None = None
    status: str
    reason_code: str
    customer_note: str | None
    staff_note: str | None
    refund_poisha: int
    items: list[ReturnItemOut]
    photos: list[ReturnPhotoOut]
    created_at: datetime
    reviewed_at: datetime | None


class ReturnListOut(BaseModel):
    items: list[ReturnRequestOut]


class LedgerEntryOut(BaseModel):
    id: UUID
    entry_type: str
    amount_poisha: int
    currency: str
    note: str | None
    gateway_refund_ref: str | None
    created_at: datetime


class LedgerListOut(BaseModel):
    items: list[LedgerEntryOut]
