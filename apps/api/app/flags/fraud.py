"""COD fraud / risk score (0–100)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def score_cod_risk(
    *,
    total_poisha: int,
    high_value_poisha: int,
    email_verified: bool,
    phone_verified: bool,
    address_phone: str | None,
    address_district: str | None,
    account_created_at: datetime | None,
    cancelled_cod_count: int,
) -> tuple[int, list[str]]:
    """Return (score, reasons). Higher = riskier."""
    score = 0
    reasons: list[str] = []

    if total_poisha >= high_value_poisha:
        score += 25
        reasons.append("high_order_value")

    if not phone_verified:
        score += 20
        reasons.append("phone_unverified")

    if not email_verified:
        score += 10
        reasons.append("email_unverified")

    if not (address_phone or "").strip():
        score += 15
        reasons.append("missing_delivery_phone")

    if not (address_district or "").strip():
        score += 10
        reasons.append("missing_district")

    if account_created_at is not None:
        age = datetime.now(UTC) - (
            account_created_at
            if account_created_at.tzinfo
            else account_created_at.replace(tzinfo=UTC)
        )
        if age < timedelta(days=7):
            score += 15
            reasons.append("new_account")

    cancelled = min(cancelled_cod_count, 3)
    if cancelled:
        score += cancelled * 15
        reasons.append(f"cancelled_cod_x{cancelled}")

    return min(score, 100), reasons


def fraud_config_from_flag_value(value: dict[str, Any] | None) -> tuple[int, int]:
    raw = value or {}
    threshold = int(raw.get("block_threshold", 70))
    high_value = int(raw.get("high_value_poisha", 500000))
    return threshold, high_value


def method_flag_key(method: str) -> str:
    return {
        "cod": "cod_enabled",
        "bkash": "bkash_enabled",
        "sslcommerz": "sslcommerz_enabled",
    }.get(method, f"{method}_enabled")
