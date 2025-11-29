"""HMAC signatures for gateway webhooks."""

from __future__ import annotations

import hashlib
import hmac


def webhook_signature(body: bytes, *, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_webhook_signature(body: bytes, header: str | None, *, secret: str) -> bool:
    if not header:
        return False
    expected = webhook_signature(body, secret=secret)
    return hmac.compare_digest(expected, header.strip())


def gateway_secret(method: str, *, bkash_secret: str, ssl_secret: str, fallback: str) -> str:
    key = method.strip().lower()
    if key == "bkash":
        return bkash_secret or fallback
    if key == "sslcommerz":
        return ssl_secret or fallback
    return fallback
