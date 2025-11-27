"""Signed sandbox payment tokens (no network, no DB)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any
from uuid import UUID


def sign_payment_token(payload: dict[str, Any], *, secret: str) -> str:
    raw = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).decode()
    sig = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def verify_payment_token(token: str, *, secret: str) -> dict[str, Any] | None:
    try:
        raw, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(raw.encode()))
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def poisha_to_bdt(amount_poisha: int) -> str:
    return f"{amount_poisha / 100:.2f}"


def bdt_to_poisha(amount: str | int | float) -> int:
    return int(round(float(amount) * 100))


def parse_order_id(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None
