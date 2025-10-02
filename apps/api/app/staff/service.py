"""Staff create and permission management."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.models.staff import STAFF_PERMISSIONS
from app.problems import PROBLEM_CONFLICT, PROBLEM_VALIDATION, DuplicateEmailError, ProblemError
from app.rbac import KNOWN_PERMISSIONS, ensure_super_admin
from app.security.passwords import hash_password, validate_password_policy
from app.staff.repository import StaffPermissionRepository
from app.users.repository import UserRepository


class StaffService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.permissions = StaffPermissionRepository(session)
        self.audit = AuditService(session)

    async def create_staff(
        self,
        *,
        actor_id: UUID,
        email: str,
        password: str,
        permissions: list[str],
    ) -> UUID:
        actor = await self.users.get_by_id(actor_id)
        if actor is None:
            raise ProblemError(401, "Unauthorized", "Sign in again.", "https://store.local/problems/unauthorized")
        ensure_super_admin(actor)

        normalized = email.strip().lower()
        policy_error = validate_password_policy(password)
        if policy_error:
            raise ProblemError(
                422,
                "Validation error",
                policy_error,
                PROBLEM_VALIDATION,
                errors=[{"field": "password", "message": policy_error}],
            )
        cleaned = _validate_permissions(permissions)
        try:
            user = await self.users.add(
                email=normalized,
                password_hash=hash_password(password),
                role_name="staff",
            )
        except DuplicateEmailError as exc:
            raise ProblemError(
                409,
                "Conflict",
                "That email is already registered.",
                PROBLEM_CONFLICT,
            ) from exc
        # Staff must verify email or be treated verified for local invites.
        user.email_verified_at = datetime.now(UTC)
        await self.permissions.replace(user.id, cleaned)
        await self.audit.record(
            action="staff_created",
            actor_user_id=actor_id,
            subject_type="user",
            subject_id=str(user.id),
            meta={"permissions": cleaned},
        )
        return user.id

    async def replace_permissions(
        self, *, actor_id: UUID, staff_user_id: UUID, permissions: list[str]
    ) -> None:
        actor = await self.users.get_by_id(actor_id)
        if actor is None:
            raise ProblemError(401, "Unauthorized", "Sign in again.", "https://store.local/problems/unauthorized")
        ensure_super_admin(actor)
        staff = await self.users.get_by_id(staff_user_id)
        if staff is None:
            raise ProblemError(404, "Not found", "Staff user not found.", "https://store.local/problems/not-found")
        cleaned = _validate_permissions(permissions)
        await self.permissions.replace(staff_user_id, cleaned)
        await self.audit.record(
            action="staff_permissions_replaced",
            actor_user_id=actor_id,
            subject_type="user",
            subject_id=str(staff_user_id),
            meta={"permissions": cleaned},
        )


def _validate_permissions(permissions: list[str]) -> list[str]:
    cleaned = sorted({p.strip() for p in permissions if p.strip()})
    unknown = [p for p in cleaned if p not in KNOWN_PERMISSIONS]
    if unknown:
        raise ProblemError(
            422,
            "Validation error",
            f"Unknown permissions: {', '.join(unknown)}. Allowed: {', '.join(STAFF_PERMISSIONS)}",
            PROBLEM_VALIDATION,
        )
    return cleaned
