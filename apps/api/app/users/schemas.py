"""User API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

SKIN_TYPES = ("dry", "oily", "combination", "sensitive", "acne-prone")
SKIN_CONCERNS = ("acne", "pigmentation", "aging", "barrier", "hydration")


class MeOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    email_verified_at: datetime | None
    roles: list[str]
    permissions: list[str]
    totp_enabled: bool
    skin_type: str | None
    skin_concerns: list[str]


class MePatchIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    skin_type: str | None = Field(default=None, max_length=32)
    skin_concerns: list[str] | None = None


class AddressIn(BaseModel):
    label: str | None = Field(default=None, max_length=64)
    line1: str = Field(min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(default="BD", min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)
    is_default: bool = False


class AddressOut(BaseModel):
    id: UUID
    label: str | None
    line1: str
    line2: str | None
    city: str
    district: str | None
    postal_code: str | None
    country: str
    phone: str | None
    is_default: bool


class SessionOut(BaseModel):
    id: UUID
    family_id: UUID
    created_at: datetime
    expires_at: datetime
    ip: str | None
    user_agent: str | None
    current: bool


class SessionListOut(BaseModel):
    items: list[SessionOut]


class MessageOut(BaseModel):
    message: str
