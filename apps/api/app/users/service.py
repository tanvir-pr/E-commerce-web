"""Current-user profile, addresses, sessions, privacy."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.auth.repository import RefreshRepository
from app.models.address import Address
from app.problems import PROBLEM_UNAUTHORIZED, PROBLEM_VALIDATION, ProblemError
from app.rbac import is_super_admin, user_permissions
from app.security.tokens import hash_token
from app.users.addresses import AddressRepository
from app.users.repository import UserRepository
from app.users.schemas import (
    SKIN_CONCERNS,
    SKIN_TYPES,
    AddressIn,
    AddressOut,
    MeOut,
    MePatchIn,
    SessionListOut,
    SessionOut,
)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.addresses = AddressRepository(session)
        self.refresh_tokens = RefreshRepository(session)
        self.audit = AuditService(session)

    async def get_me(self, user_id: UUID) -> MeOut:
        user = await self._require_active(user_id)
        permissions = await user_permissions(self.session, user.id)
        if is_super_admin(user):
            permissions = ["support", "warehouse", "moderation", "admin"]
        concerns = user.skin_concerns if isinstance(user.skin_concerns, list) else []
        return MeOut(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            email_verified_at=user.email_verified_at,
            roles=[role.name for role in user.roles],
            permissions=permissions,
            totp_enabled=user.totp_confirmed_at is not None,
            skin_type=user.skin_type,
            skin_concerns=[str(c) for c in concerns],
        )

    async def patch_me(self, user_id: UUID, body: MePatchIn) -> MeOut:
        user = await self._require_active(user_id)
        if body.display_name is not None:
            user.display_name = body.display_name.strip() or None
        if body.skin_type is not None:
            if body.skin_type != "" and body.skin_type not in SKIN_TYPES:
                raise ProblemError(
                    422,
                    "Validation error",
                    f"skin_type must be one of: {', '.join(SKIN_TYPES)}",
                    PROBLEM_VALIDATION,
                )
            user.skin_type = body.skin_type or None
        if body.skin_concerns is not None:
            cleaned = [c for c in body.skin_concerns if c in SKIN_CONCERNS]
            unknown = [c for c in body.skin_concerns if c not in SKIN_CONCERNS]
            if unknown:
                raise ProblemError(
                    422,
                    "Validation error",
                    f"Unknown skin concerns: {', '.join(unknown)}",
                    PROBLEM_VALIDATION,
                )
            user.skin_concerns = cleaned
        await self.audit.record(
            action="account.profile_updated",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
        )
        return await self.get_me(user.id)

    async def list_addresses(self, user_id: UUID) -> list[AddressOut]:
        await self._require_active(user_id)
        rows = await self.addresses.list_for_user(user_id)
        return [_address_out(row) for row in rows]

    async def create_address(self, user_id: UUID, body: AddressIn) -> AddressOut:
        await self._require_active(user_id)
        row = Address(
            user_id=user_id,
            label=body.label,
            line1=body.line1,
            line2=body.line2,
            city=body.city,
            district=body.district,
            postal_code=body.postal_code,
            country=body.country.upper(),
            phone=body.phone,
            is_default=body.is_default,
        )
        saved = await self.addresses.add(row)
        await self.audit.record(
            action="account.address_created",
            actor_user_id=user_id,
            subject_type="address",
            subject_id=str(saved.id),
        )
        return _address_out(saved)

    async def update_address(
        self, user_id: UUID, address_id: UUID, body: AddressIn
    ) -> AddressOut:
        await self._require_active(user_id)
        row = await self.addresses.get_owned(user_id, address_id)
        row.label = body.label
        row.line1 = body.line1
        row.line2 = body.line2
        row.city = body.city
        row.district = body.district
        row.postal_code = body.postal_code
        row.country = body.country.upper()
        row.phone = body.phone
        row.is_default = body.is_default
        saved = await self.addresses.save(row)
        return _address_out(saved)

    async def delete_address(self, user_id: UUID, address_id: UUID) -> None:
        await self._require_active(user_id)
        row = await self.addresses.get_owned(user_id, address_id)
        await self.addresses.delete(row)
        await self.audit.record(
            action="account.address_deleted",
            actor_user_id=user_id,
            subject_type="address",
            subject_id=str(address_id),
        )

    async def list_sessions(
        self, user_id: UUID, *, current_refresh: str | None
    ) -> SessionListOut:
        await self._require_active(user_id)
        current_hash = hash_token(current_refresh) if current_refresh else None
        rows = await self.refresh_tokens.list_active_for_user(user_id)
        items = [
            SessionOut(
                id=row.id,
                family_id=row.family_id,
                created_at=row.created_at,
                expires_at=row.expires_at,
                ip=row.ip,
                user_agent=row.user_agent,
                current=bool(current_hash and row.token_hash == current_hash),
            )
            for row in rows
        ]
        return SessionListOut(items=items)

    async def revoke_session(self, user_id: UUID, session_id: UUID) -> None:
        await self._require_active(user_id)
        rows = await self.refresh_tokens.list_active_for_user(user_id)
        match = next((row for row in rows if row.id == session_id), None)
        if match is None:
            return
        await self.refresh_tokens.revoke_family(match.family_id)
        await self.audit.record(
            action="account.session_revoked",
            actor_user_id=user_id,
            subject_type="refresh_family",
            subject_id=str(match.family_id),
        )

    async def logout_everywhere(self, user_id: UUID) -> None:
        await self._require_active(user_id)
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.audit.record(
            action="account.logout_everywhere",
            actor_user_id=user_id,
            subject_type="user",
            subject_id=str(user_id),
        )

    async def export(self, user_id: UUID) -> dict[str, Any]:
        me = await self.get_me(user_id)
        addresses = await self.list_addresses(user_id)
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": me.model_dump(mode="json"),
            "addresses": [a.model_dump(mode="json") for a in addresses],
            "note": "Orders and payments will appear here in later parts.",
        }

    async def soft_delete(self, user_id: UUID) -> None:
        user = await self._require_active(user_id)
        user.deleted_at = datetime.now(UTC)
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.audit.record(
            action="account.soft_deleted",
            actor_user_id=user_id,
            subject_type="user",
            subject_id=str(user_id),
        )

    async def _require_active(self, user_id: UUID) -> Any:
        user = await self.users.get_by_id(user_id)
        if user is None or user.deleted_at is not None:
            raise ProblemError(
                401,
                "Unauthorized",
                "Sign in again.",
                PROBLEM_UNAUTHORIZED,
            )
        return user


def _address_out(row: Address) -> AddressOut:
    return AddressOut(
        id=row.id,
        label=row.label,
        line1=row.line1,
        line2=row.line2,
        city=row.city,
        district=row.district,
        postal_code=row.postal_code,
        country=row.country,
        phone=row.phone,
        is_default=row.is_default,
    )
