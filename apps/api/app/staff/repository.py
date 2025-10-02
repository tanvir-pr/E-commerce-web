"""Staff permissions and recovery codes."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staff import RecoveryCode, StaffPermission
from app.security.tokens import hash_token


class StaffPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[str]:
        result = await self.session.execute(
            select(StaffPermission.permission).where(StaffPermission.user_id == user_id)
        )
        return list(result.scalars().all())

    async def replace(self, user_id: UUID, permissions: list[str]) -> None:
        await self.session.execute(
            delete(StaffPermission).where(StaffPermission.user_id == user_id)
        )
        for permission in permissions:
            self.session.add(StaffPermission(user_id=user_id, permission=permission))


class RecoveryCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_all(self, user_id: UUID, raw_codes: list[str]) -> None:
        await self.session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user_id))
        for raw in raw_codes:
            self.session.add(RecoveryCode(user_id=user_id, code_hash=hash_token(raw)))

    async def consume(self, user_id: UUID, raw_code: str) -> bool:
        result = await self.session.execute(
            select(RecoveryCode).where(
                RecoveryCode.user_id == user_id,
                RecoveryCode.code_hash == hash_token(raw_code.strip().lower()),
                RecoveryCode.used_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.used_at = datetime.now(UTC)
        return True
