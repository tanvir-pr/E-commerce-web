"""TOTP secret encryption and verification."""

import pyotp
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.problems import PROBLEM_INTERNAL, ProblemError


def _fernet() -> Fernet:
    settings = get_settings()
    try:
        return Fernet(settings.totp_encryption_key.encode("utf-8"))
    except Exception as exc:
        raise ProblemError(
            500,
            "Internal Server Error",
            "TOTP encryption is misconfigured.",
            PROBLEM_INTERNAL,
        ) from exc


def encrypt_totp_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ProblemError(
            500,
            "Internal Server Error",
            "Could not read authenticator secret.",
            PROBLEM_INTERNAL,
        ) from exc


def new_totp_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(*, secret: str, email: str) -> str:
    settings = get_settings()
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=settings.totp_issuer)


def verify_totp_code(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)
