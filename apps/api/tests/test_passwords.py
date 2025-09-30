"""Password policy and Argon2."""

from app.security.passwords import hash_password, validate_password_policy, verify_password


def test_hash_and_verify() -> None:
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong-password", hashed)


def test_policy_min_length() -> None:
    assert validate_password_policy("short") is not None
    assert validate_password_policy("long-enough-password") is None
