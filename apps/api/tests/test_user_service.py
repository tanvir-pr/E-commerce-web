"""UserService profile and address helpers with fakes."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.problems import ProblemError
from app.users.schemas import AddressIn, MePatchIn
from app.users.service import UserService


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeUsers:
    def __init__(self, user: SimpleNamespace) -> None:
        self.user = user

    async def get_by_id(self, user_id: UUID) -> SimpleNamespace | None:
        if user_id != self.user.id:
            return None
        return self.user


class FakeAddresses:
    def __init__(self) -> None:
        self.rows: list[SimpleNamespace] = []

    async def list_for_user(self, user_id: UUID) -> list[SimpleNamespace]:
        return [row for row in self.rows if row.user_id == user_id]

    async def get_owned(self, user_id: UUID, address_id: UUID) -> SimpleNamespace:
        for row in self.rows:
            if row.user_id == user_id and row.id == address_id:
                return row
        raise ProblemError(404, "Not found", "Address not found.", "x")

    async def add(self, address: SimpleNamespace) -> SimpleNamespace:
        address.id = uuid4()
        self.rows.append(address)
        return address

    async def save(self, address: SimpleNamespace) -> SimpleNamespace:
        return address

    async def delete(self, address: SimpleNamespace) -> None:
        self.rows = [row for row in self.rows if row.id != address.id]


class FakeRefresh:
    def __init__(self) -> None:
        self.rows: list[SimpleNamespace] = []

    async def list_active_for_user(self, user_id: UUID) -> list[SimpleNamespace]:
        now = datetime.now(UTC)
        return [
            row
            for row in self.rows
            if row.user_id == user_id and row.revoked_at is None and row.expires_at > now
        ]

    async def revoke_family(self, family_id: UUID) -> None:
        now = datetime.now(UTC)
        for row in self.rows:
            if row.family_id == family_id:
                row.revoked_at = now

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        now = datetime.now(UTC)
        for row in self.rows:
            if row.user_id == user_id:
                row.revoked_at = now


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        email="me@example.com",
        display_name=None,
        email_verified_at=None,
        phone=None,
        phone_verified_at=None,
        roles=[SimpleNamespace(name="customer")],
        totp_confirmed_at=None,
        skin_type=None,
        skin_concerns=[],
        deleted_at=None,
    )


def _service(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[UserService, SimpleNamespace, FakeAddresses, FakeRefresh, FakeAudit]:
    user = _user()
    service = UserService(FakeSession())  # type: ignore[arg-type]
    addresses = FakeAddresses()
    refresh = FakeRefresh()
    audit = FakeAudit()
    service.users = FakeUsers(user)  # type: ignore[assignment]
    service.addresses = addresses  # type: ignore[assignment]
    service.refresh_tokens = refresh  # type: ignore[assignment]
    service.audit = audit  # type: ignore[assignment]

    async def _perms(_session: object, _user_id: UUID) -> list[str]:
        return []

    monkeypatch.setattr("app.users.service.user_permissions", _perms)
    monkeypatch.setattr("app.users.service.is_super_admin", lambda _u: False)
    return service, user, addresses, refresh, audit


@pytest.mark.asyncio
async def test_patch_skin_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    service, user, _a, _r, audit = _service(monkeypatch)
    me = await service.patch_me(
        user.id,
        MePatchIn(display_name="Asha", skin_type="oily", skin_concerns=["acne", "barrier"]),
    )
    assert me.display_name == "Asha"
    assert me.skin_type == "oily"
    assert me.skin_concerns == ["acne", "barrier"]
    assert "account.profile_updated" in audit.actions


@pytest.mark.asyncio
async def test_address_create_and_list(monkeypatch: pytest.MonkeyPatch) -> None:
    service, user, addresses, _r, _a = _service(monkeypatch)
    created = await service.create_address(
        user.id,
        AddressIn(line1="12 Road 3", city="Dhaka", district="Dhaka", is_default=True),
    )
    assert created.city == "Dhaka"
    assert created.is_default is True
    listed = await service.list_addresses(user.id)
    assert len(listed) == 1
    assert len(addresses.rows) == 1


@pytest.mark.asyncio
async def test_soft_delete_revokes_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    service, user, _a, refresh, audit = _service(monkeypatch)
    refresh.rows.append(
        SimpleNamespace(
            id=uuid4(),
            user_id=user.id,
            family_id=uuid4(),
            token_hash="abc",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=1),
            revoked_at=None,
            ip=None,
            user_agent=None,
        )
    )
    await service.soft_delete(user.id)
    assert user.deleted_at is not None
    assert refresh.rows[0].revoked_at is not None
    assert "account.soft_deleted" in audit.actions
