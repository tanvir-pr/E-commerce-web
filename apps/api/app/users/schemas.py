"""User API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class MeOut(BaseModel):
    id: UUID
    email: EmailStr
    email_verified_at: datetime | None
    roles: list[str]
    permissions: list[str]
    totp_enabled: bool
