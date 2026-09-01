"""Admin API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateStaffIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    permissions: list[str] = Field(default_factory=list)


class CreateStaffOut(BaseModel):
    id: UUID


class ReplacePermissionsIn(BaseModel):
    permissions: list[str]


class AuditEventOut(BaseModel):
    id: UUID
    action: str
    actor_user_id: UUID | None
    subject_type: str | None
    subject_id: str | None
    created_at: datetime


class AuditListOut(BaseModel):
    items: list[AuditEventOut]


class LaunchCheckOut(BaseModel):
    key: str
    title: str
    status: str
    detail: str


class LaunchReadinessOut(BaseModel):
    ready_for_launch: bool
    blocking_failures: int
    manual_items: int
    expected_alembic: str
    checks: list[LaunchCheckOut]
