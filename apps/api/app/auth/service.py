"""Auth use cases: register, verify, login, refresh, logout."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.audit.service import AuditService
from app.auth.mailer import Mailer
from app.auth.repository import RefreshRepository, VerificationRepository
from app.config import Settings
from app.models.user import User
from app.problems import (
    PROBLEM_CREDENTIALS,
    PROBLEM_SESSION,
    PROBLEM_VERIFY,
    DuplicateEmailError,
    ProblemError,
)
from app.security.passwords import hash_password, validate_password_policy, verify_password
from app.security.tokens import create_access_token, generate_opaque_token, hash_token
from app.users.repository import UserRepository

REGISTER_MESSAGE = "If that email can be used, we sent a verification link."


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings,
        mailer: Mailer,
        audit: AuditService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.mailer = mailer
        self.users = UserRepository(session)
        self.verifications = VerificationRepository(session)
        self.refresh_tokens = RefreshRepository(session)
        self.audit = audit or AuditService(session)

    async def register(
        self,
        *,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        normalized = email.strip().lower()
        policy_error = validate_password_policy(password)
        if policy_error:
            raise ProblemError(
                422,
                "Validation error",
                policy_error,
                "https://store.local/problems/validation-error",
                errors=[{"field": "password", "message": policy_error}],
            )

        existing = await self.users.get_by_email(normalized)
        if existing is not None:
            await self.audit.record(
                action="auth.register.duplicate",
                subject_type="email",
                subject_id=normalized.split("@")[-1],
                ip=ip,
                user_agent=user_agent,
            )
            return REGISTER_MESSAGE

        try:
            user = await self.users.add(
                email=normalized,
                password_hash=hash_password(password),
                role_name="customer",
            )
        except DuplicateEmailError:
            return REGISTER_MESSAGE

        raw = generate_opaque_token()
        await self.verifications.add(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self.settings.email_verification_ttl_hours),
        )
        await self.audit.record(
            action="auth.register",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        await self.session.flush()
        await self.mailer.send_verification(email=normalized, token=raw)
        return REGISTER_MESSAGE

    async def verify_email(self, *, token: str) -> None:
        row = await self.verifications.get_valid(hash_token(token))
        if row is None:
            raise ProblemError(
                400,
                "Invalid verification token",
                "This verification link is invalid or has expired.",
                PROBLEM_VERIFY,
            )
        await self.verifications.mark_used(row)
        await self.users.mark_email_verified(row.user_id)
        await self.audit.record(
            action="auth.verify_email",
            actor_user_id=row.user_id,
            subject_type="user",
            subject_id=str(row.user_id),
        )

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        normalized = email.strip().lower()
        user = await self.users.get_by_email(normalized)
        if user is None or not verify_password(password, user.password_hash):
            await self.audit.record(
                action="auth.login.failed",
                subject_type="email",
                subject_id=normalized.split("@")[-1],
                ip=ip,
                user_agent=user_agent,
            )
            raise ProblemError(
                401,
                "Invalid credentials",
                "Email or password is incorrect.",
                PROBLEM_CREDENTIALS,
            )

        access, refresh = await self._issue_session(user)
        await self.audit.record(
            action="auth.login",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        return user, access, refresh

    async def refresh(self, *, raw_refresh: str | None) -> tuple[User, str, str]:
        if not raw_refresh:
            raise ProblemError(
                401,
                "Invalid session",
                "Sign in again.",
                PROBLEM_SESSION,
            )
        current = await self.refresh_tokens.get_by_hash(hash_token(raw_refresh))
        now = datetime.now(UTC)
        if current is None:
            raise ProblemError(401, "Invalid session", "Sign in again.", PROBLEM_SESSION)

        if current.revoked_at is not None or current.expires_at <= now:
            await self.refresh_tokens.revoke_family(current.family_id)
            await self.audit.record(
                action="auth.refresh.reuse_or_expired",
                actor_user_id=current.user_id,
                subject_type="refresh_family",
                subject_id=str(current.family_id),
            )
            raise ProblemError(401, "Invalid session", "Sign in again.", PROBLEM_SESSION)

        user = await self.users.get_by_id(current.user_id)
        if user is None:
            await self.refresh_tokens.revoke_family(current.family_id)
            raise ProblemError(401, "Invalid session", "Sign in again.", PROBLEM_SESSION)

        raw_new = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days)
        replacement = await self.refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_token(raw_new),
            family_id=current.family_id,
            expires_at=expires_at,
        )
        await self.refresh_tokens.mark_replaced(current, replaced_by_id=replacement.id)
        access = create_access_token(
            user_id=user.id,
            roles=[role.name for role in user.roles],
        )
        return user, access, raw_new

    async def logout(self, *, raw_refresh: str | None, user_id: UUID | None = None) -> None:
        if raw_refresh:
            current = await self.refresh_tokens.get_by_hash(hash_token(raw_refresh))
            if current is not None:
                await self.refresh_tokens.revoke_family(current.family_id)
                user_id = current.user_id
        await self.audit.record(
            action="auth.logout",
            actor_user_id=user_id,
            subject_type="user",
            subject_id=str(user_id) if user_id else None,
        )

    async def _issue_session(self, user: User) -> tuple[str, str]:
        family_id = UUID(str(uuid7()))
        raw_refresh = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days)
        await self.refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id,
            expires_at=expires_at,
        )
        access = create_access_token(
            user_id=user.id,
            roles=[role.name for role in user.roles],
        )
        return access, raw_refresh


def client_meta(request_headers: dict[str, str]) -> tuple[str | None, str | None]:
    ip = request_headers.get("x-forwarded-for", "").split(",")[0].strip() or None
    user_agent = request_headers.get("user-agent")
    return ip, user_agent


def request_header_map(headers: Any) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}
