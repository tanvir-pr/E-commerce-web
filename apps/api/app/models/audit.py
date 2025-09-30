"""Append-only audit log."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7

from app.db import Base


def _uuid7() -> UUID:
    return UUID(str(uuid7()))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    subject_type: Mapped[str | None] = mapped_column(String(64))
    subject_id: Mapped[str | None] = mapped_column(String(64))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
