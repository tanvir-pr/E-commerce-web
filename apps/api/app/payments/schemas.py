"""Payment API schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PayStartOut(BaseModel):
    order_id: UUID
    method: str
    redirect_url: str
    provider_ref: str
    sandbox: bool = True


class PayValidateIn(BaseModel):
    """Gateway-shaped return payload. Sandbox accepts a signed `token` + status."""

    model_config = {"extra": "allow"}

    token: str | None = None
    status: str | None = None
    transactionStatus: str | None = None
    paymentID: str | None = None
    order_id: UUID | None = None
    amount: str | float | int | None = None
    val_id: str | None = None
    tran_id: str | None = None


class PayValidateOut(BaseModel):
    order_id: UUID
    order_number: str
    status: str
    payment_status: str | None
    provider_ref: str
    method: str
    meta: dict[str, Any] = Field(default_factory=dict)
