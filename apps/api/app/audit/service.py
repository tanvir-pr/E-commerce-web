"""Append-only audit writer."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        actor_user_id: UUID | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                subject_type=subject_type,
                subject_id=subject_id,
                ip=ip,
                user_agent=user_agent,
                meta=meta,
            )
        )
