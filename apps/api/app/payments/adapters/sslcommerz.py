"""SSLCommerz sandbox adapter — hosted redirect + validation payload (no live HTTP)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from app.config import Settings
from app.payments.protocol import InitiateResult, RefundResult, ValidateResult
from app.payments.tokens import (
    bdt_to_poisha,
    parse_order_id,
    poisha_to_bdt,
    sign_payment_token,
    verify_payment_token,
)


class SandboxSslcommerzGateway:
    method = "sslcommerz"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._secret = settings.sslcommerz_store_password or settings.jwt_secret

    def initiate(
        self,
        *,
        order_id: UUID,
        order_number: str,
        amount_poisha: int,
        currency: str,
        return_url: str,
        cancel_url: str,
    ) -> InitiateResult:
        _ = (currency, cancel_url)
        provider_ref = f"SSL{uuid4().hex[:16].upper()}"
        token = sign_payment_token(
            {
                "method": self.method,
                "order_id": str(order_id),
                "order_number": order_number,
                "amount_poisha": amount_poisha,
                "amount": poisha_to_bdt(amount_poisha),
                "provider_ref": provider_ref,
                "tran_id": order_number,
            },
            secret=self._secret,
        )
        base = self.settings.public_web_url.rstrip("/")
        redirect_url = (
            f"{base}/en/pay/sandbox?method=sslcommerz&token={token}"
            f"&return={quote(return_url, safe='')}"
        )
        return InitiateResult(redirect_url=redirect_url, provider_ref=provider_ref)

    def validate(self, payload: dict[str, Any]) -> ValidateResult:
        token = payload.get("token")
        if isinstance(token, str) and token:
            data = verify_payment_token(token, secret=self._secret)
            if data is None or data.get("method") != self.method:
                return ValidateResult(
                    ok=False,
                    order_id=UUID(int=0),
                    provider_ref="",
                    amount_poisha=0,
                    reason="Invalid or forged SSLCommerz sandbox token",
                )
            status = str(payload.get("status") or "").upper()
            ok = status in {"VALID", "SUCCESS", "COMPLETED"}
            order_id = parse_order_id(data.get("order_id"))
            if order_id is None:
                return ValidateResult(
                    ok=False,
                    order_id=UUID(int=0),
                    provider_ref="",
                    amount_poisha=0,
                    reason="Token missing order_id",
                )
            return ValidateResult(
                ok=ok,
                order_id=order_id,
                provider_ref=str(data.get("provider_ref") or ""),
                amount_poisha=int(data.get("amount_poisha") or 0),
                reason=None if ok else f"SSLCommerz status not VALID: {status or 'missing'}",
            )

        order_id = parse_order_id(payload.get("order_id"))
        provider_ref = str(payload.get("val_id") or payload.get("provider_ref") or "")
        tran_id = str(payload.get("tran_id") or "")
        status = str(payload.get("status") or "").upper()
        amount_raw = payload.get("amount")
        if (order_id is None and not tran_id) or not provider_ref or amount_raw is None:
            return ValidateResult(
                ok=False,
                order_id=order_id or UUID(int=0),
                provider_ref=provider_ref,
                amount_poisha=0,
                reason="val_id, amount, and order_id or tran_id are required",
            )
        amount_poisha = bdt_to_poisha(amount_raw)
        ok = status == "VALID"
        return ValidateResult(
            ok=ok,
            order_id=order_id or UUID(int=0),
            provider_ref=provider_ref,
            amount_poisha=amount_poisha,
            reason=None if ok else f"SSLCommerz status not VALID: {status or 'missing'}",
        )

    def refund(
        self,
        *,
        provider_ref: str,
        amount_poisha: int,
        order_number: str,
    ) -> RefundResult:
        _ = (amount_poisha, order_number)
        ref = provider_ref.strip() or "SSLUNKNOWN"
        return RefundResult(ok=True, refund_ref=f"RF-{ref[:24]}")
