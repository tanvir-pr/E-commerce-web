"""User and role persistence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Role, UserRole
from app.models.user import User
from app.problems import DuplicateEmailError, RoleMissingError


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_role_by_name(self, name: str) -> Role | None:
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def add(self, *, email: str, password_hash: str, role_name: str = "customer") -> User:
        role = await self.get_role_by_name(role_name)
        if role is None:
            raise RoleMissingError(role_name)
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        self.session.add(UserRole(user_id=user.id, role_id=role.id))
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateEmailError from exc
        await self.session.refresh(user, attribute_names=["roles"])
        return user

    async def mark_email_verified(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)
        if user is None:
            return
        if user.email_verified_at is None:
            user.email_verified_at = datetime.now(UTC)

    async def set_totp_secret(self, user_id: UUID, encrypted: str) -> None:
        user = await self.get_by_id(user_id)
        if user is None:
            return
        user.totp_secret_encrypted = encrypted
        user.totp_confirmed_at = None

    async def confirm_totp(self, user_id: UUID) -> None:
        user = await self.get_by_id(user_id)
        if user is None:
            return
        user.totp_confirmed_at = datetime.now(UTC)
