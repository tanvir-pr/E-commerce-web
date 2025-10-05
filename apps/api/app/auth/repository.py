"""Token persistence for auth."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import EmailVerificationToken, PasswordResetToken, RefreshToken


class VerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        self.session.add(
            EmailVerificationToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )

    async def get_valid(self, token_hash: str) -> EmailVerificationToken | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.used_at.is_(None),
                EmailVerificationToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: EmailVerificationToken) -> None:
        token.used_at = datetime.now(UTC)


class PasswordResetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        self.session.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )

    async def get_valid(self, token_hash: str) -> PasswordResetToken | None:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordResetToken) -> None:
        token.used_at = datetime.now(UTC)


class RefreshRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> RefreshToken:
        row = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
            ip=ip,
            user_agent=user_agent,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: UUID) -> list[RefreshToken]:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_family(self, family_id: UUID) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def mark_replaced(self, token: RefreshToken, *, replaced_by_id: UUID) -> None:
        token.revoked_at = datetime.now(UTC)
        token.replaced_by_id = replaced_by_id
