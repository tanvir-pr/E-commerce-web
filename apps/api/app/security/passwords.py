"""Argon2id password hashing and breach stub."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def password_is_breached(password: str) -> bool:
    """Have I Been Pwned hook. Stub mode never blocks."""
    settings = get_settings()
    if settings.breach_check == "stub":
        return False
    _ = password
    return False


def validate_password_policy(password: str) -> str | None:
    if len(password) < 10:
        return "Password must be at least 10 characters."
    if password_is_breached(password):
        return "Choose a different password."
    return None
