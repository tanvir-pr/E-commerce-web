"""Short-lived pending-auth JWTs for TOTP enroll/challenge."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import jwt

from app.config import get_settings
from app.problems import PROBLEM_SECOND_FACTOR, ProblemError
from app.security.tokens import ALGORITHM

PendingPurpose = Literal["enroll", "challenge"]


def create_pending_token(*, user_id: UUID, purpose: PendingPurpose) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.pending_auth_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_pending_token(token: str, *, purpose: PendingPurpose) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ProblemError(
            401,
            "Invalid second factor step",
            "Sign in again to continue.",
            PROBLEM_SECOND_FACTOR,
        ) from exc
    if payload.get("purpose") != purpose or "sub" not in payload:
        raise ProblemError(
            401,
            "Invalid second factor step",
            "Sign in again to continue.",
            PROBLEM_SECOND_FACTOR,
        )
    try:
        return UUID(str(payload["sub"]))
    except ValueError as exc:
        raise ProblemError(
            401,
            "Invalid second factor step",
            "Sign in again to continue.",
            PROBLEM_SECOND_FACTOR,
        ) from exc
