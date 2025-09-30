"""Opaque tokens and short-lived access JWTs."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from app.config import get_settings
from app.problems import InvalidAccessToken

ALGORITHM = "HS256"


def generate_opaque_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def tokens_match(raw: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_token(raw), token_hash)


def create_access_token(*, user_id: UUID, roles: list[str]) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidAccessToken from exc
    if "sub" not in payload:
        raise InvalidAccessToken
    return dict(payload)
