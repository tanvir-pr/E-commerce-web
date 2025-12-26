"""Feature flag API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FeatureFlagOut(BaseModel):
    id: UUID
    key: str
    enabled: bool
    value: dict[str, Any] | None
    description: str | None
    updated_at: datetime


class FeatureFlagListOut(BaseModel):
    items: list[FeatureFlagOut]


class FeatureFlagPatchIn(BaseModel):
    enabled: bool | None = None
    value: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=500)


class CheckoutMethodsOut(BaseModel):
    checkout_enabled: bool
    methods: list[str]
    cod_fraud_check_enabled: bool
