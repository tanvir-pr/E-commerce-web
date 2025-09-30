"""Seed roles and the owner account. Idempotent."""

import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.models.role import Role, UserRole
from app.models.user import User
from app.security.passwords import hash_password
from app.session import SessionFactory


async def seed() -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        for name in ("customer", "super_admin", "staff"):
            exists = await session.execute(select(Role).where(Role.name == name))
            if exists.scalar_one_or_none() is None:
                session.add(Role(name=name))
        await session.flush()

        email = settings.seed_superadmin_email.strip().lower()
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(settings.seed_superadmin_password),
                email_verified_at=None,
            )
            # Mark verified so the owner can sign in immediately for local ops.
            from datetime import UTC, datetime

            user.email_verified_at = datetime.now(UTC)
            session.add(user)
            await session.flush()
            role = (
                await session.execute(select(Role).where(Role.name == "super_admin"))
            ).scalar_one()
            session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()
        print(f"super admin ready: {email}")


if __name__ == "__main__":
    asyncio.run(seed())
