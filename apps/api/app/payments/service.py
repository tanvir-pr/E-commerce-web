"""Start hosted checkout, validate returns, and process signed webhooks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.config import Settings, get_settings
from app.models.payment import PaymentEvent
from app.orders.mailer import NullOrderMailer, OrderMailer
from app.orders.service import OrderService
from app.payments.factory import GATEWAY_METHODS, get_gateway
from app.payments.protocol import ValidateResult
from app.payments.repository import PaymentEventRepository
from app.payments.schemas import PayStartOut, PayValidateOut
from app.payments.signatures import gateway_secret, verify_webhook_signature
from app.problems import (
    PROBLEM_FORBIDDEN,
    PROBLEM_NOT_FOUND,
    PROBLEM_VALIDATION,
    ProblemError,
)


def _event_id_from_result(method: str, result: ValidateResult, payload: dict[str, Any]) -> str:
    raw = (
        payload.get("gateway_event_id")
        or payload.get("paymentID")
        or payload.get("payment_id")
        or payload.get("val_id")
        or payload.get("trxID")
        or result.provider_ref
    )
    value = str(raw or "").strip()
    if not value:
        value = f"{method}:{result.order_id}:{result.amount_poisha}"
    return value[:128]


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        mailer: OrderMailer | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.orders = OrderService(
            session, settings=self.settings, mailer=mailer or NullOrderMailer()
        )
        self.events = PaymentEventRepository(session)

    def _secret_for(self, method: str) -> str:
        return gateway_secret(
            method,
            bkash_secret=self.settings.bkash_app_secret,
            ssl_secret=self.settings.sslcommerz_store_password,
            fallback=self.settings.jwt_secret,
        )

    async def start_pay(self, order_id: UUID, *, user_id: UUID) -> PayStartOut:
        order = await self.orders.repo.require_owned(order_id, user_id)
        method = (order.payment_method or "").strip().lower()
        if method not in GATEWAY_METHODS:
            raise ProblemError(
                422,
                "Validation error",
                "Only bKash and SSLCommerz orders can start hosted payment.",
                PROBLEM_VALIDATION,
            )
        if order.status != "pending_payment":
            raise ProblemError(
                422,
                "Validation error",
                "Order is not awaiting payment.",
                PROBLEM_VALIDATION,
            )
        if (
            order.reservation_expires_at is not None
            and order.reservation_expires_at <= datetime.now(UTC)
        ):
            raise ProblemError(
                422,
                "Validation error",
                "Stock reservation expired. Place a new order.",
                PROBLEM_VALIDATION,
            )

        gateway = get_gateway(method, self.settings)
        base = self.settings.public_web_url.rstrip("/")
        # Browser return hits API (session-less) then 303s to the order page.
        return_url = f"{base}/en/orders/{order.id}"
        cancel_url = return_url
        result = gateway.initiate(
            order_id=order.id,
            order_number=order.order_number,
            amount_poisha=order.total_poisha,
            currency=order.currency or "BDT",
            return_url=return_url,
            cancel_url=cancel_url,
        )
        return PayStartOut(
            order_id=order.id,
            method=method,
            redirect_url=result.redirect_url,
            provider_ref=result.provider_ref,
            sandbox=self.settings.payment_gateway_mode == "sandbox",
        )

    async def validate(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        user_id: UUID,
    ) -> PayValidateOut:
        return await self._process_payload(
            method,
            payload,
            source="validate",
            user_id=user_id,
        )

    async def validate_owned_or_forbidden(
        self, method: str, payload: dict[str, Any], *, user_id: UUID
    ) -> PayValidateOut:
        try:
            return await self.validate(method, payload, user_id=user_id)
        except ProblemError as exc:
            if exc.status == 404:
                raise ProblemError(
                    403,
                    "Forbidden",
                    "You cannot validate payment for this order.",
                    PROBLEM_FORBIDDEN,
                ) from exc
            raise

    async def process_return(
        self, method: str, payload: dict[str, Any]
    ) -> PayValidateOut:
        """Session-less browser return — trust signed token / gateway fields."""
        return await self._process_payload(
            method,
            payload,
            source="return",
            user_id=None,
        )

    async def process_webhook(
        self,
        method: str,
        *,
        body: bytes,
        signature_header: str | None,
        payload: dict[str, Any],
    ) -> PayValidateOut:
        key = method.strip().lower()
        if key not in GATEWAY_METHODS:
            raise ProblemError(
                422,
                "Validation error",
                f"Unknown payment method: {method}",
                PROBLEM_VALIDATION,
            )
        if not verify_webhook_signature(
            body, signature_header, secret=self._secret_for(key)
        ):
            raise ProblemError(
                403,
                "Forbidden",
                "Invalid webhook signature.",
                PROBLEM_FORBIDDEN,
            )
        return await self._process_payload(
            key,
            payload,
            source="webhook",
            user_id=None,
        )

    async def _process_payload(
        self,
        method: str,
        payload: dict[str, Any],
        *,
        source: str,
        user_id: UUID | None,
    ) -> PayValidateOut:
        key = method.strip().lower()
        if key not in GATEWAY_METHODS:
            raise ProblemError(
                422,
                "Validation error",
                f"Unknown payment method: {method}",
                PROBLEM_VALIDATION,
            )
        gateway = get_gateway(key, self.settings)
        result = gateway.validate(payload)
        if not result.ok:
            raise ProblemError(
                422,
                "Validation error",
                result.reason or "Payment validation failed.",
                PROBLEM_VALIDATION,
            )
        if result.order_id.int == 0:
            raise ProblemError(
                422,
                "Validation error",
                "Validated payload did not include a usable order id.",
                PROBLEM_VALIDATION,
            )

        event_id = _event_id_from_result(key, result, payload)
        existing = await self.events.get_by_gateway_event(
            gateway=key, gateway_event_id=event_id
        )
        if existing is not None:
            order = await self.orders.repo.require(existing.order_id)
            if user_id is not None and order.user_id != user_id:
                raise ProblemError(
                    404, "Not found", "Order not found.", PROBLEM_NOT_FOUND
                )
            return PayValidateOut(
                order_id=order.id,
                order_number=order.order_number,
                status=order.status,
                payment_status=order.payment_status,
                provider_ref=existing.provider_ref or result.provider_ref,
                method=key,
                meta={"idempotent": True, "source": source},
            )

        if user_id is not None:
            order = await self.orders.repo.require_owned(result.order_id, user_id)
        else:
            order = await self.orders.repo.require(result.order_id)

        if (order.payment_method or "").strip().lower() != key:
            raise ProblemError(
                422,
                "Validation error",
                "Payment method does not match this order.",
                PROBLEM_VALIDATION,
            )
        if result.amount_poisha != order.total_poisha:
            raise ProblemError(
                422,
                "Validation error",
                "Paid amount does not match order total.",
                PROBLEM_VALIDATION,
            )

        if order.status != "pending_payment":
            if order.status == "confirmed" and order.payment_status == "paid":
                await self._record_event(
                    gateway=key,
                    gateway_event_id=event_id,
                    order_id=order.id,
                    provider_ref=result.provider_ref,
                    amount_poisha=result.amount_poisha,
                    status="processed",
                    source=source,
                    raw_payload=payload,
                )
                return PayValidateOut(
                    order_id=order.id,
                    order_number=order.order_number,
                    status=order.status,
                    payment_status=order.payment_status,
                    provider_ref=result.provider_ref,
                    method=key,
                    meta={"idempotent": True, "source": source},
                )
            raise ProblemError(
                422,
                "Validation error",
                "Order is not awaiting payment.",
                PROBLEM_VALIDATION,
            )

        inserted = await self._record_event(
            gateway=key,
            gateway_event_id=event_id,
            order_id=order.id,
            provider_ref=result.provider_ref,
            amount_poisha=result.amount_poisha,
            status="processed",
            source=source,
            raw_payload=payload,
        )
        if inserted is None:
            # Lost race — another request processed the same event id.
            order = await self.orders.repo.require(order.id)
            return PayValidateOut(
                order_id=order.id,
                order_number=order.order_number,
                status=order.status,
                payment_status=order.payment_status,
                provider_ref=result.provider_ref,
                method=key,
                meta={"idempotent": True, "source": source},
            )

        out = await self.orders.confirm_prepaid(
            order,
            actor_user_id=order.user_id,
            provider_ref=result.provider_ref,
            gateway=key,
        )
        return PayValidateOut(
            order_id=out.id,
            order_number=out.order_number,
            status=out.status,
            payment_status=out.payment_status,
            provider_ref=result.provider_ref,
            method=key,
            meta={"source": source, "gateway_event_id": event_id},
        )

    async def _record_event(
        self,
        *,
        gateway: str,
        gateway_event_id: str,
        order_id: UUID,
        provider_ref: str | None,
        amount_poisha: int,
        status: str,
        source: str,
        raw_payload: dict[str, Any],
    ) -> PaymentEvent | None:
        return await self.events.try_insert(
            id=UUID(str(uuid7())),
            gateway=gateway,
            gateway_event_id=gateway_event_id,
            order_id=order_id,
            provider_ref=provider_ref,
            amount_poisha=amount_poisha,
            status=status,
            source=source,
            raw_payload=raw_payload,
        )
