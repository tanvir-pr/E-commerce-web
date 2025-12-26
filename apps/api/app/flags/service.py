"""Feature flags and COD risk gating."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.checkout.schemas import CheckoutQuoteOut
from app.flags.fraud import fraud_config_from_flag_value, method_flag_key, score_cod_risk
from app.flags.repository import FeatureFlagRepository
from app.flags.schemas import (
    CheckoutMethodsOut,
    FeatureFlagListOut,
    FeatureFlagOut,
    FeatureFlagPatchIn,
)
from app.problems import PROBLEM_VALIDATION, ProblemError
from app.users.repository import UserRepository


class FeatureFlagService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FeatureFlagRepository(session)
        self.audit = AuditService(session)
        self.users = UserRepository(session)

    async def list_admin(self) -> FeatureFlagListOut:
        rows = await self.repo.list_all()
        return FeatureFlagListOut(items=[self._out(row) for row in rows])

    async def patch(
        self, flag_id: UUID, body: FeatureFlagPatchIn, *, actor_user_id: UUID
    ) -> FeatureFlagOut:
        row = await self.repo.require(flag_id)
        if body.enabled is not None:
            row.enabled = body.enabled
        if body.value is not None:
            row.value = body.value
        if body.description is not None:
            row.description = body.description.strip() or None
        row.updated_at = datetime.now(UTC)
        await self.repo.save(row)
        await self.audit.record(
            action="feature_flag.updated",
            actor_user_id=actor_user_id,
            subject_type="feature_flag",
            subject_id=str(row.id),
            meta={"key": row.key, "enabled": row.enabled, "value": row.value},
        )
        return self._out(row)

    async def is_enabled(self, key: str, *, default: bool = True) -> bool:
        row = await self.repo.get_by_key(key)
        if row is None:
            return default
        return bool(row.enabled)

    async def checkout_methods(self) -> CheckoutMethodsOut:
        checkout_on = await self.is_enabled("checkout_enabled", default=True)
        methods: list[str] = []
        if await self.is_enabled("cod_enabled", default=True):
            methods.append("cod")
        if await self.is_enabled("bkash_enabled", default=True):
            methods.append("bkash")
        if await self.is_enabled("sslcommerz_enabled", default=True):
            methods.append("sslcommerz")
        fraud_on = await self.is_enabled("cod_fraud_check_enabled", default=True)
        return CheckoutMethodsOut(
            checkout_enabled=checkout_on,
            methods=methods,
            cod_fraud_check_enabled=fraud_on,
        )

    async def assert_can_place(self, method: str) -> None:
        if not await self.is_enabled("checkout_enabled", default=True):
            raise ProblemError(
                422,
                "Validation error",
                "Checkout is temporarily disabled.",
                PROBLEM_VALIDATION,
            )
        flag_key = method_flag_key(method)
        if not await self.is_enabled(flag_key, default=True):
            raise ProblemError(
                422,
                "Validation error",
                f"Payment method '{method}' is currently unavailable.",
                PROBLEM_VALIDATION,
            )

    async def evaluate_cod(
        self,
        *,
        user_id: UUID,
        quote: CheckoutQuoteOut,
    ) -> tuple[int, list[str]]:
        """Score COD risk. Raises if blocked by threshold."""
        if not await self.is_enabled("cod_fraud_check_enabled", default=True):
            return 0, []

        flag = await self.repo.get_by_key("cod_fraud_check_enabled")
        threshold, high_value = fraud_config_from_flag_value(
            flag.value if flag else None
        )
        user = await self.users.get_by_id(user_id)
        cancelled = await self.repo.count_cancelled_cod(user_id)
        score, reasons = score_cod_risk(
            total_poisha=quote.total_poisha,
            high_value_poisha=high_value,
            email_verified=bool(user and user.email_verified_at),
            phone_verified=bool(user and user.phone_verified_at),
            address_phone=quote.address.phone,
            address_district=quote.address.district,
            account_created_at=user.created_at if user else None,
            cancelled_cod_count=cancelled,
        )
        if score >= threshold:
            raise ProblemError(
                422,
                "Validation error",
                "COD is unavailable for this order. Please pay with bKash or SSLCommerz.",
                PROBLEM_VALIDATION,
            )
        return score, reasons

    def _out(self, row: object) -> FeatureFlagOut:
        return FeatureFlagOut(
            id=row.id,  # type: ignore[attr-defined]
            key=row.key,  # type: ignore[attr-defined]
            enabled=row.enabled,  # type: ignore[attr-defined]
            value=row.value,  # type: ignore[attr-defined]
            description=row.description,  # type: ignore[attr-defined]
            updated_at=row.updated_at,  # type: ignore[attr-defined]
        )

