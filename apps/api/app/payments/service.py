"""Start hosted checkout and validate gateway returns."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.orders.mailer import NullOrderMailer, OrderMailer
from app.orders.service import OrderService
from app.payments.factory import GATEWAY_METHODS, get_gateway
from app.payments.schemas import PayStartOut, PayValidateOut
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_VALIDATION, ProblemError


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

        order = await self.orders.repo.require_owned(result.order_id, user_id)
        if (order.payment_method or "").strip().lower() != key:
            raise ProblemError(
                422,
                "Validation error",
                "Payment method does not match this order.",
                PROBLEM_VALIDATION,
            )
        if order.status != "pending_payment":
            # Idempotent success if already confirmed+paid for same flow.
            if order.status == "confirmed" and order.payment_status == "paid":
                return PayValidateOut(
                    order_id=order.id,
                    order_number=order.order_number,
                    status=order.status,
                    payment_status=order.payment_status,
                    provider_ref=result.provider_ref,
                    method=key,
                    meta={"idempotent": True},
                )
            raise ProblemError(
                422,
                "Validation error",
                "Order is not awaiting payment.",
                PROBLEM_VALIDATION,
            )
        if result.amount_poisha != order.total_poisha:
            raise ProblemError(
                422,
                "Validation error",
                "Paid amount does not match order total.",
                PROBLEM_VALIDATION,
            )

        out = await self.orders.confirm_prepaid(
            order,
            actor_user_id=user_id,
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
            meta={},
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
