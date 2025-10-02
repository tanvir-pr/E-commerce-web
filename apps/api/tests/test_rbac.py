"""RBAC helpers."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.problems import ProblemError
from app.rbac import ensure_staff, ensure_super_admin, is_staff_user, requires_totp


def test_customer_is_not_staff() -> None:
    user = SimpleNamespace(roles=[SimpleNamespace(name="customer")])
    assert not is_staff_user(user)  # type: ignore[arg-type]
    assert not requires_totp(user)  # type: ignore[arg-type]
    with pytest.raises(ProblemError) as exc:
        ensure_staff(user)  # type: ignore[arg-type]
    assert exc.value.status == 403


def test_super_admin_is_staff() -> None:
    user = SimpleNamespace(id=uuid4(), roles=[SimpleNamespace(name="super_admin")])
    assert is_staff_user(user)  # type: ignore[arg-type]
    ensure_super_admin(user)  # type: ignore[arg-type]
