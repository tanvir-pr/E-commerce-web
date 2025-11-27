"""bKash sandbox adapter — hosted redirect + validation payload (no live HTTP)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from app.config import Settings
from app.payments.protocol import InitiateResult, ValidateResult
from app.payments.tokens import (
    bdt_to_poisha,
    parse_order_id,
    poisha_to_bdt,
    sign_payment_token,
    verify_payment_token,
)


class SandboxBkashGateway:
    method = "bkash"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._secret = settings.bkash_app_secret or settings.jwt_secret

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
        provider_ref = f"BK{uuid4().hex[:16].upper()}"
        token = sign_payment_token(
            {
                "method": self.method,
                "order_id": str(order_id),
                "order_number": order_number,
                "amount_poisha": amount_poisha,
                "amount": poisha_to_bdt(amount_poisha),
                "provider_ref": provider_ref,
            },
            secret=self._secret,
        )
        base = self.settings.public_web_url.rstrip("/")
        redirect_url = (
            f"{base}/en/pay/sandbox?method=bkash&token={token}"
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
                    reason="Invalid or forged bKash sandbox token",
                )
            status = str(payload.get("status") or payload.get("transactionStatus") or "").lower()
            ok = status in {"success", "completed", "completed_payment"}
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
                reason=None if ok else f"bKash status not successful: {status or 'missing'}",
            )

        order_id = parse_order_id(payload.get("order_id") or payload.get("merchantInvoiceNumber"))
        provider_ref = str(payload.get("paymentID") or payload.get("payment_id") or "")
        status = str(payload.get("transactionStatus") or payload.get("status") or "").lower()
        amount_raw = payload.get("amount")
        if order_id is None or not provider_ref or amount_raw is None:
            return ValidateResult(
                ok=False,
                order_id=order_id or UUID(int=0),
                provider_ref=provider_ref,
                amount_poisha=0,
                reason="paymentID, order_id, and amount are required",
            )
        amount_poisha = bdt_to_poisha(amount_raw)
        ok = status in {"completed", "success"}
        return ValidateResult(
            ok=ok,
            order_id=order_id,
            provider_ref=provider_ref,
            amount_poisha=amount_poisha,
            reason=None if ok else f"bKash status not successful: {status or 'missing'}",
        )
