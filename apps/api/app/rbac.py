"""Role and permission checks. Deny by default."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.problems import PROBLEM_FORBIDDEN, ProblemError
from app.staff.repository import StaffPermissionRepository

STAFF_ROLES = frozenset({"super_admin", "staff"})
KNOWN_PERMISSIONS = frozenset({"support", "warehouse", "moderation"})


def role_names(user: User) -> set[str]:
    return {role.name for role in user.roles}


def is_staff_user(user: User) -> bool:
    return bool(role_names(user) & STAFF_ROLES)


def requires_totp(user: User) -> bool:
    return is_staff_user(user)


def is_super_admin(user: User) -> bool:
    return "super_admin" in role_names(user)


async def user_permissions(session: AsyncSession, user_id: UUID) -> list[str]:
    return await StaffPermissionRepository(session).list_for_user(user_id)


def ensure_staff(user: User) -> None:
    if not is_staff_user(user):
        raise ProblemError(
            403,
            "Forbidden",
            "Staff access required.",
            PROBLEM_FORBIDDEN,
        )


def ensure_super_admin(user: User) -> None:
    if not is_super_admin(user):
        raise ProblemError(
            403,
            "Forbidden",
            "Super admin access required.",
            PROBLEM_FORBIDDEN,
        )


async def ensure_permission(session: AsyncSession, user: User, permission: str) -> None:
    ensure_staff(user)
    if is_super_admin(user):
        return
    if permission not in KNOWN_PERMISSIONS:
        raise ProblemError(403, "Forbidden", "Unknown permission.", PROBLEM_FORBIDDEN)
    held = await user_permissions(session, user.id)
    if permission not in held:
        raise ProblemError(
            403,
            "Forbidden",
            "You do not have permission for this action.",
            PROBLEM_FORBIDDEN,
        )
