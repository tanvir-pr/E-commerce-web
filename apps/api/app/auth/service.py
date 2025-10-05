"""Auth use cases: register, verify, login, TOTP, refresh, logout."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.audit.service import AuditService
from app.auth.mailer import Mailer
from app.auth.repository import (
    PasswordResetRepository,
    RefreshRepository,
    VerificationRepository,
)
from app.config import Settings
from app.models.user import User
from app.problems import (
    PROBLEM_CREDENTIALS,
    PROBLEM_PHONE_DISABLED,
    PROBLEM_RESET,
    PROBLEM_SECOND_FACTOR,
    PROBLEM_SESSION,
    PROBLEM_VERIFY,
    DuplicateEmailError,
    ProblemError,
)
from app.rbac import requires_totp
from app.security.passwords import hash_password, validate_password_policy, verify_password
from app.security.pending import create_pending_token, decode_pending_token
from app.security.tokens import create_access_token, generate_opaque_token, hash_token
from app.security.totp import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    new_totp_secret,
    provisioning_uri,
    verify_totp_code,
)
from app.staff.repository import RecoveryCodeRepository
from app.users.repository import UserRepository

REGISTER_MESSAGE = "If that email can be used, we sent a verification link."
RESET_MESSAGE = "If that account exists, we sent a password reset link."
LoginNext = Literal["session", "enroll", "challenge"]


@dataclass
class LoginResult:
    next: LoginNext
    user: User | None = None
    access: str | None = None
    refresh: str | None = None
    pending_token: str | None = None


@dataclass
class TotpSetupResult:
    secret: str
    otpauth_url: str
    qr_svg: str


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
        self.password_resets = PasswordResetRepository(session)
        self.refresh_tokens = RefreshRepository(session)
        self.recovery_codes = RecoveryCodeRepository(session)
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
    ) -> LoginResult:
        normalized = email.strip().lower()
        user = await self.users.get_by_email(normalized)
        if (
            user is None
            or user.deleted_at is not None
            or not verify_password(password, user.password_hash)
        ):
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

        if requires_totp(user):
            if user.totp_confirmed_at is None:
                pending = create_pending_token(user_id=user.id, purpose="enroll")
                await self.audit.record(
                    action="auth.login.enroll_required",
                    actor_user_id=user.id,
                    subject_type="user",
                    subject_id=str(user.id),
                    ip=ip,
                    user_agent=user_agent,
                )
                return LoginResult(next="enroll", pending_token=pending)
            pending = create_pending_token(user_id=user.id, purpose="challenge")
            await self.audit.record(
                action="auth.login.challenge_required",
                actor_user_id=user.id,
                subject_type="user",
                subject_id=str(user.id),
                ip=ip,
                user_agent=user_agent,
            )
            return LoginResult(next="challenge", pending_token=pending)

        access, refresh = await self._issue_session(user, ip=ip, user_agent=user_agent)
        await self.audit.record(
            action="auth.login",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
            ip=ip,
            user_agent=user_agent,
        )
        return LoginResult(next="session", user=user, access=access, refresh=refresh)

    async def totp_setup(self, *, enroll_token: str | None) -> TotpSetupResult:
        user_id = decode_pending_token(enroll_token or "", purpose="enroll")
        user = await self.users.get_by_id(user_id)
        if user is None or not requires_totp(user):
            raise ProblemError(
                401,
                "Invalid second factor step",
                "Sign in again to continue.",
                PROBLEM_SECOND_FACTOR,
            )
        if user.totp_confirmed_at is not None:
            raise ProblemError(
                400,
                "Invalid second factor step",
                "Authenticator is already enrolled.",
                PROBLEM_SECOND_FACTOR,
            )
        secret = new_totp_secret()
        await self.users.set_totp_secret(user.id, encrypt_totp_secret(secret))
        otpauth = provisioning_uri(secret=secret, email=user.email)
        qr_svg = _qr_svg(otpauth)
        await self.audit.record(
            action="auth.totp.setup",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
        )
        return TotpSetupResult(secret=secret, otpauth_url=otpauth, qr_svg=qr_svg)

    async def totp_confirm(
        self, *, enroll_token: str | None, code: str
    ) -> tuple[User, str, str, list[str]]:
        user_id = decode_pending_token(enroll_token or "", purpose="enroll")
        user = await self.users.get_by_id(user_id)
        if user is None or not user.totp_secret_encrypted:
            raise ProblemError(
                401,
                "Invalid second factor step",
                "Sign in again to continue.",
                PROBLEM_SECOND_FACTOR,
            )
        secret = decrypt_totp_secret(user.totp_secret_encrypted)
        if not verify_totp_code(secret, code):
            await self.audit.record(
                action="auth.totp.confirm_failed",
                actor_user_id=user.id,
                subject_type="user",
                subject_id=str(user.id),
            )
            raise ProblemError(
                401,
                "Invalid second factor",
                "That authenticator code is incorrect.",
                PROBLEM_SECOND_FACTOR,
            )
        await self.users.confirm_totp(user.id)
        raw_codes = [_recovery_code() for _ in range(10)]
        await self.recovery_codes.replace_all(user.id, raw_codes)
        access, refresh = await self._issue_session(user)
        await self.audit.record(
            action="auth.totp.confirmed",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
        )
        return user, access, refresh, raw_codes

    async def totp_challenge(
        self,
        *,
        challenge_token: str | None,
        code: str | None,
        recovery_code: str | None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
        user_id = decode_pending_token(challenge_token or "", purpose="challenge")
        user = await self.users.get_by_id(user_id)
        if user is None or not user.totp_secret_encrypted or user.totp_confirmed_at is None:
            raise ProblemError(
                401,
                "Invalid second factor step",
                "Sign in again to continue.",
                PROBLEM_SECOND_FACTOR,
            )

        ok = False
        if code:
            secret = decrypt_totp_secret(user.totp_secret_encrypted)
            ok = verify_totp_code(secret, code)
        elif recovery_code:
            ok = await self.recovery_codes.consume(user.id, recovery_code)
        if not ok:
            await self.audit.record(
                action="auth.totp.challenge_failed",
                actor_user_id=user.id,
                subject_type="user",
                subject_id=str(user.id),
            )
            raise ProblemError(
                401,
                "Invalid second factor",
                "That code is incorrect.",
                PROBLEM_SECOND_FACTOR,
            )

        access, refresh = await self._issue_session(user, ip=ip, user_agent=user_agent)
        await self.audit.record(
            action="auth.login",
            actor_user_id=user.id,
            subject_type="user",
            subject_id=str(user.id),
            meta={"via": "totp"},
        )
        return user, access, refresh

    async def request_password_reset(
        self,
        *,
        email: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        normalized = email.strip().lower()
        user = await self.users.get_by_email(normalized)
        if user is not None and user.deleted_at is None:
            raw = generate_opaque_token()
            await self.password_resets.add(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC)
                + timedelta(hours=self.settings.password_reset_ttl_hours),
            )
            await self.audit.record(
                action="auth.password_reset.requested",
                actor_user_id=user.id,
                subject_type="user",
                subject_id=str(user.id),
                ip=ip,
                user_agent=user_agent,
            )
            await self.session.flush()
            await self.mailer.send_password_reset(email=normalized, token=raw)
        else:
            await self.audit.record(
                action="auth.password_reset.unknown",
                subject_type="email",
                subject_id=normalized.split("@")[-1],
                ip=ip,
                user_agent=user_agent,
            )
        return RESET_MESSAGE

    async def reset_password(
        self,
        *,
        token: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        policy_error = validate_password_policy(password)
        if policy_error:
            raise ProblemError(
                422,
                "Validation error",
                policy_error,
                "https://store.local/problems/validation-error",
                errors=[{"field": "password", "message": policy_error}],
            )
        row = await self.password_resets.get_valid(hash_token(token))
        if row is None:
            raise ProblemError(
                400,
                "Invalid reset token",
                "This reset link is invalid or has expired.",
                PROBLEM_RESET,
            )
        await self.password_resets.mark_used(row)
        await self.users.set_password(row.user_id, hash_password(password))
        await self.refresh_tokens.revoke_all_for_user(row.user_id)
        await self.audit.record(
            action="auth.password_reset.completed",
            actor_user_id=row.user_id,
            subject_type="user",
            subject_id=str(row.user_id),
            ip=ip,
            user_agent=user_agent,
        )

    async def phone_start(self, *, phone: str) -> None:
        _ = phone
        if not self.settings.phone_registration_enabled:
            raise ProblemError(
                403,
                "Phone registration disabled",
                "Phone OTP registration is not available yet.",
                PROBLEM_PHONE_DISABLED,
            )
        raise ProblemError(
            501,
            "Not implemented",
            "Phone OTP is not implemented yet.",
            PROBLEM_PHONE_DISABLED,
        )

    async def phone_confirm(self, *, phone: str, code: str) -> None:
        _ = (phone, code)
        if not self.settings.phone_registration_enabled:
            raise ProblemError(
                403,
                "Phone registration disabled",
                "Phone OTP registration is not available yet.",
                PROBLEM_PHONE_DISABLED,
            )
        raise ProblemError(
            501,
            "Not implemented",
            "Phone OTP is not implemented yet.",
            PROBLEM_PHONE_DISABLED,
        )

    async def refresh(
        self,
        *,
        raw_refresh: str | None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[User, str, str]:
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
        if user is None or user.deleted_at is not None:
            await self.refresh_tokens.revoke_family(current.family_id)
            raise ProblemError(401, "Invalid session", "Sign in again.", PROBLEM_SESSION)

        raw_new = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days)
        replacement = await self.refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_token(raw_new),
            family_id=current.family_id,
            expires_at=expires_at,
            ip=ip or current.ip,
            user_agent=user_agent or current.user_agent,
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

    async def logout_everywhere(self, *, user_id: UUID) -> None:
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.audit.record(
            action="auth.logout_everywhere",
            actor_user_id=user_id,
            subject_type="user",
            subject_id=str(user_id),
        )

    async def _issue_session(
        self,
        user: User,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        family_id = UUID(str(uuid7()))
        raw_refresh = generate_opaque_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days)
        await self.refresh_tokens.add(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id,
            expires_at=expires_at,
            ip=ip,
            user_agent=user_agent,
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


def _recovery_code() -> str:
    # 8 hex chars, lowercased for storage/compare
    return generate_opaque_token(6).replace("-", "").replace("_", "")[:8].lower()


def _qr_svg(otpauth_url: str) -> str:
    import segno

    return segno.make(otpauth_url).svg_inline(scale=4)
