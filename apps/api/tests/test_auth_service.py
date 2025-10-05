"""AuthService with in-memory fakes (no Postgres)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.auth.mailer import NullMailer
from app.auth.service import REGISTER_MESSAGE, RESET_MESSAGE, AuthService
from app.config import Settings
from app.problems import ProblemError
from app.security.passwords import hash_password, verify_password
from app.security.tokens import hash_token


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeUsers:
    def __init__(self) -> None:
        self.by_email: dict[str, SimpleNamespace] = {}
        self.by_id: dict[UUID, SimpleNamespace] = {}

    async def get_by_email(self, email: str) -> SimpleNamespace | None:
        return self.by_email.get(email)

    async def get_by_id(self, user_id: UUID) -> SimpleNamespace | None:
        return self.by_id.get(user_id)

    async def add(
        self, *, email: str, password_hash: str, role_name: str = "customer"
    ) -> SimpleNamespace:
        user = SimpleNamespace(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            roles=[SimpleNamespace(name=role_name)],
            email_verified_at=None,
            totp_secret_encrypted=None,
            totp_confirmed_at=None,
            deleted_at=None,
        )
        self.by_email[email] = user
        self.by_id[user.id] = user
        return user

    async def mark_email_verified(self, user_id: UUID) -> None:
        user = self.by_id[user_id]
        user.email_verified_at = datetime.now(UTC)

    async def set_totp_secret(self, user_id: UUID, encrypted: str) -> None:
        user = self.by_id[user_id]
        user.totp_secret_encrypted = encrypted
        user.totp_confirmed_at = None

    async def confirm_totp(self, user_id: UUID) -> None:
        self.by_id[user_id].totp_confirmed_at = datetime.now(UTC)

    async def set_password(self, user_id: UUID, password_hash: str) -> None:
        self.by_id[user_id].password_hash = password_hash


class FakeVerifications:
    def __init__(self) -> None:
        self.rows: dict[str, SimpleNamespace] = {}

    async def add(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        self.rows[token_hash] = SimpleNamespace(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=None,
        )

    async def get_valid(self, token_hash: str) -> SimpleNamespace | None:
        row = self.rows.get(token_hash)
        if row is None or row.used_at is not None:
            return None
        if row.expires_at <= datetime.now(UTC):
            return None
        return row

    async def mark_used(self, token: SimpleNamespace) -> None:
        token.used_at = datetime.now(UTC)


class FakeRefresh:
    def __init__(self) -> None:
        self.rows: dict[str, SimpleNamespace] = {}

    async def add(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> SimpleNamespace:
        row = SimpleNamespace(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
            revoked_at=None,
            replaced_by_id=None,
            ip=ip,
            user_agent=user_agent,
        )
        self.rows[token_hash] = row
        return row

    async def get_by_hash(self, token_hash: str) -> SimpleNamespace | None:
        return self.rows.get(token_hash)

    async def revoke_family(self, family_id: UUID) -> None:
        now = datetime.now(UTC)
        for row in self.rows.values():
            if row.family_id == family_id and row.revoked_at is None:
                row.revoked_at = now

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        now = datetime.now(UTC)
        for row in self.rows.values():
            if row.user_id == user_id and row.revoked_at is None:
                row.revoked_at = now

    async def mark_replaced(self, token: SimpleNamespace, *, replaced_by_id: UUID) -> None:
        token.revoked_at = datetime.now(UTC)
        token.replaced_by_id = replaced_by_id


class FakePasswordResets:
    def __init__(self) -> None:
        self.rows: dict[str, SimpleNamespace] = {}

    async def add(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> None:
        self.rows[token_hash] = SimpleNamespace(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=None,
        )

    async def get_valid(self, token_hash: str) -> SimpleNamespace | None:
        row = self.rows.get(token_hash)
        if row is None or row.used_at is not None:
            return None
        if row.expires_at <= datetime.now(UTC):
            return None
        return row

    async def mark_used(self, token: SimpleNamespace) -> None:
        token.used_at = datetime.now(UTC)


class FakeRecovery:
    async def replace_all(self, user_id: UUID, raw_codes: list[str]) -> None:
        _ = (user_id, raw_codes)

    async def consume(self, user_id: UUID, raw_code: str) -> bool:
        _ = (user_id, raw_code)
        return False


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://store:store@localhost:5432/store",
        redis_url="redis://localhost:6379/0",
        jwt_secret="test-secret",
        breach_check="stub",
        totp_encryption_key="_-Ya7B3qukwFBFcl2y52RF4qvs52ThkeoxVKWZ9Jnq8=",
    )


def _service() -> tuple[AuthService, FakeUsers, FakeVerifications, FakeRefresh, FakeAudit]:
    service = AuthService(
        FakeSession(),  # type: ignore[arg-type]
        settings=_settings(),
        mailer=NullMailer(),
        audit=FakeAudit(),  # type: ignore[arg-type]
    )
    users = FakeUsers()
    verifications = FakeVerifications()
    refresh = FakeRefresh()
    audit = FakeAudit()
    service.users = users  # type: ignore[assignment]
    service.verifications = verifications  # type: ignore[assignment]
    service.password_resets = FakePasswordResets()  # type: ignore[assignment]
    service.refresh_tokens = refresh  # type: ignore[assignment]
    service.recovery_codes = FakeRecovery()  # type: ignore[assignment]
    service.audit = audit  # type: ignore[assignment]
    return service, users, verifications, refresh, audit


@pytest.mark.asyncio
async def test_register_is_enumeration_safe() -> None:
    service, users, _v, _r, audit = _service()
    await users.add(email="a@example.com", password_hash=hash_password("password123"))
    message = await service.register(email="a@example.com", password="password123")
    assert message == REGISTER_MESSAGE
    assert "auth.register.duplicate" in audit.actions


@pytest.mark.asyncio
async def test_verify_email_single_use() -> None:
    service, users, verifications, _r, _a = _service()
    user = await users.add(email="b@example.com", password_hash=hash_password("password123"))
    raw = "verify-token-value-1234567890"
    await verifications.add(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await service.verify_email(token=raw)
    assert users.by_id[user.id].email_verified_at is not None
    with pytest.raises(ProblemError) as exc:
        await service.verify_email(token=raw)
    assert exc.value.status == 400


@pytest.mark.asyncio
async def test_login_rejects_bad_password() -> None:
    service, users, _v, _r, audit = _service()
    await users.add(email="c@example.com", password_hash=hash_password("password123"))
    with pytest.raises(ProblemError) as exc:
        await service.login(email="c@example.com", password="nope-nope-no")
    assert exc.value.status == 401
    assert "auth.login.failed" in audit.actions


@pytest.mark.asyncio
async def test_customer_login_issues_session() -> None:
    service, users, _v, _r, _a = _service()
    await users.add(email="cust@example.com", password_hash=hash_password("password123"))
    result = await service.login(email="cust@example.com", password="password123")
    assert result.next == "session"
    assert result.access and result.refresh


@pytest.mark.asyncio
async def test_staff_login_requires_enroll() -> None:
    service, users, _v, _r, audit = _service()
    await users.add(
        email="staff@example.com",
        password_hash=hash_password("password123"),
        role_name="super_admin",
    )
    result = await service.login(email="staff@example.com", password="password123")
    assert result.next == "enroll"
    assert result.pending_token
    assert result.access is None
    assert "auth.login.enroll_required" in audit.actions


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family() -> None:
    service, users, _v, refresh, audit = _service()
    user = await users.add(email="d@example.com", password_hash=hash_password("password123"))
    result = await service.login(email="d@example.com", password="password123")
    assert result.refresh
    raw = result.refresh
    _u2, _a2, raw2 = await service.refresh(raw_refresh=raw)
    assert raw2 != raw
    with pytest.raises(ProblemError):
        await service.refresh(raw_refresh=raw)
    family = next(iter(refresh.rows.values())).family_id
    assert all(
        row.revoked_at is not None for row in refresh.rows.values() if row.family_id == family
    )
    assert "auth.refresh.reuse_or_expired" in audit.actions
    assert user.id == result.user.id if result.user else True


@pytest.mark.asyncio
async def test_password_reset_flow() -> None:
    service, users, _v, refresh, audit = _service()
    user = await users.add(email="reset@example.com", password_hash=hash_password("password123"))
    login = await service.login(email="reset@example.com", password="password123")
    assert login.refresh
    message = await service.request_password_reset(email="reset@example.com")
    assert message == RESET_MESSAGE
    assert "auth.password_reset.requested" in audit.actions
    known = "reset-token-value-1234567890ab"
    service.password_resets.rows.clear()  # type: ignore[attr-defined]
    await service.password_resets.add(  # type: ignore[attr-defined]
        user_id=user.id,
        token_hash=hash_token(known),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await service.reset_password(token=known, password="newpassword99")
    assert verify_password("newpassword99", users.by_id[user.id].password_hash)
    assert all(row.revoked_at is not None for row in refresh.rows.values())
    assert "auth.password_reset.completed" in audit.actions


@pytest.mark.asyncio
async def test_phone_start_disabled() -> None:
    service, _u, _v, _r, _a = _service()
    with pytest.raises(ProblemError) as exc:
        await service.phone_start(phone="+8801712345678")
    assert exc.value.status == 403


@pytest.mark.asyncio
async def test_deleted_user_cannot_login() -> None:
    service, users, _v, _r, _a = _service()
    user = await users.add(email="gone@example.com", password_hash=hash_password("password123"))
    user.deleted_at = datetime.now(UTC)
    with pytest.raises(ProblemError) as exc:
        await service.login(email="gone@example.com", password="password123")
    assert exc.value.status == 401
