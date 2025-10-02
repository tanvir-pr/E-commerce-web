"""Current-user reads."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.problems import PROBLEM_UNAUTHORIZED, ProblemError
from app.rbac import is_super_admin, user_permissions
from app.users.repository import UserRepository
from app.users.schemas import MeOut


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def get_me(self, user_id: UUID) -> MeOut:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise ProblemError(
                401,
                "Unauthorized",
                "Sign in again.",
                PROBLEM_UNAUTHORIZED,
            )
        permissions = await user_permissions(self.session, user.id)
        if is_super_admin(user):
            permissions = ["support", "warehouse", "moderation", "admin"]
        return MeOut(
            id=user.id,
            email=user.email,
            email_verified_at=user.email_verified_at,
            roles=[role.name for role in user.roles],
            permissions=permissions,
            totp_enabled=user.totp_confirmed_at is not None,
        )
