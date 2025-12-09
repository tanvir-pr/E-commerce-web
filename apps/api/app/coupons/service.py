"""Coupon admin CRUD and checkout apply."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.cart.schemas import CartOut
from app.coupons.repository import CouponRepository
from app.coupons.schemas import CouponApplyResult, CouponIn, CouponListOut, CouponOut
from app.models.coupon import Coupon, CouponRedemption
from app.problems import PROBLEM_VALIDATION, ProblemError


class CouponService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CouponRepository(session)
        self.audit = AuditService(session)

    async def list_admin(self) -> CouponListOut:
        rows = await self.repo.list_all()
        items: list[CouponOut] = []
        for row in rows:
            items.append(await self._out(row))
        return CouponListOut(items=items)

    async def create(self, body: CouponIn, *, actor_user_id: UUID) -> CouponOut:
        code = body.code.strip().upper()
        await self._validate_values(body)
        if await self.repo.get_by_code(code) is not None:
            raise ProblemError(
                422, "Validation error", "Coupon code already exists.", PROBLEM_VALIDATION
            )
        row = Coupon(
            code=code,
            discount_type=body.discount_type,
            value=body.value,
            min_spend_poisha=body.min_spend_poisha,
            category_id=body.category_id,
            starts_at=body.starts_at,
            expires_at=body.expires_at,
            max_redemptions=body.max_redemptions,
            max_per_user=body.max_per_user,
            is_active=body.is_active,
        )
        await self.repo.add(row)
        await self.audit.record(
            action="coupon.created",
            actor_user_id=actor_user_id,
            subject_type="coupon",
            subject_id=str(row.id),
            meta={"code": code},
        )
        return await self._out(row)

    async def update(
        self, coupon_id: UUID, body: CouponIn, *, actor_user_id: UUID
    ) -> CouponOut:
        row = await self.repo.require(coupon_id)
        await self._validate_values(body)
        code = body.code.strip().upper()
        existing = await self.repo.get_by_code(code)
        if existing is not None and existing.id != row.id:
            raise ProblemError(
                422, "Validation error", "Coupon code already exists.", PROBLEM_VALIDATION
            )
        row.code = code
        row.discount_type = body.discount_type
        row.value = body.value
        row.min_spend_poisha = body.min_spend_poisha
        row.category_id = body.category_id
        row.starts_at = body.starts_at
        row.expires_at = body.expires_at
        row.max_redemptions = body.max_redemptions
        row.max_per_user = body.max_per_user
        row.is_active = body.is_active
        await self.repo.save(row)
        await self.audit.record(
            action="coupon.updated",
            actor_user_id=actor_user_id,
            subject_type="coupon",
            subject_id=str(row.id),
            meta={"code": code},
        )
        return await self._out(row)

    async def delete(self, coupon_id: UUID, *, actor_user_id: UUID) -> None:
        row = await self.repo.require(coupon_id)
        await self.repo.delete(row)
        await self.audit.record(
            action="coupon.deleted",
            actor_user_id=actor_user_id,
            subject_type="coupon",
            subject_id=str(coupon_id),
            meta={},
        )

    async def apply_to_cart(
        self,
        code: str | None,
        *,
        cart: CartOut,
        user_id: UUID,
        strict: bool = False,
    ) -> CouponApplyResult:
        """Compute discount. Quote uses soft fail; place uses strict=True."""
        raw = (code or "").strip()
        if not raw:
            return CouponApplyResult(ok=True, discount_poisha=0)

        normalized = raw.upper()
        coupon = await self.repo.get_by_code(normalized)
        if coupon is None or not coupon.is_active:
            return self._fail("Coupon not found or inactive.", strict=strict, code=normalized)

        now = datetime.now(UTC)
        if coupon.starts_at is not None and now < coupon.starts_at:
            return self._fail("Coupon is not active yet.", strict=strict, code=normalized)
        if coupon.expires_at is not None and now > coupon.expires_at:
            return self._fail("Coupon has expired.", strict=strict, code=normalized)

        if coupon.max_redemptions is not None:
            used = await self.repo.redemption_count(coupon.id)
            if used >= coupon.max_redemptions:
                return self._fail("Coupon usage limit reached.", strict=strict, code=normalized)
        if coupon.max_per_user is not None:
            used_user = await self.repo.user_redemption_count(coupon.id, user_id)
            if used_user >= coupon.max_per_user:
                return self._fail(
                    "You have already used this coupon.", strict=strict, code=normalized
                )

        eligible = await self._eligible_subtotal(cart, coupon)
        if coupon.min_spend_poisha is not None and eligible < coupon.min_spend_poisha:
            return self._fail(
                f"Minimum spend is {coupon.min_spend_poisha} poisha on eligible items.",
                strict=strict,
                code=normalized,
            )
        if eligible <= 0:
            return self._fail(
                "No eligible items for this coupon.", strict=strict, code=normalized
            )

        if coupon.discount_type == "percent":
            discount = (eligible * coupon.value) // 100
        else:
            discount = coupon.value
        discount = max(0, min(discount, eligible))
        if discount <= 0:
            return self._fail("Coupon discount is zero.", strict=strict, code=normalized)

        return CouponApplyResult(
            ok=True,
            code=normalized,
            coupon_id=coupon.id,
            discount_poisha=discount,
            message=None,
        )

    async def record_redemption(
        self,
        *,
        coupon_id: UUID,
        order_id: UUID,
        user_id: UUID,
        discount_poisha: int,
    ) -> None:
        await self.repo.add_redemption(
            CouponRedemption(
                coupon_id=coupon_id,
                order_id=order_id,
                user_id=user_id,
                discount_poisha=discount_poisha,
            )
        )

    async def _eligible_subtotal(self, cart: CartOut, coupon: Coupon) -> int:
        if coupon.category_id is None:
            return cart.subtotal_poisha
        slug = await self.repo.category_slug(coupon.category_id)
        if not slug:
            return 0
        return sum(
            item.line_total_poisha
            for item in cart.items
            if (item.category_slug or "") == slug
        )

    def _fail(
        self, message: str, *, strict: bool, code: str
    ) -> CouponApplyResult:
        if strict:
            raise ProblemError(422, "Validation error", message, PROBLEM_VALIDATION)
        return CouponApplyResult(ok=False, code=code, discount_poisha=0, message=message)

    async def _validate_values(self, body: CouponIn) -> None:
        if body.discount_type == "percent" and not (1 <= body.value <= 100):
            raise ProblemError(
                422,
                "Validation error",
                "Percent coupons must have value between 1 and 100.",
                PROBLEM_VALIDATION,
            )
        if body.starts_at and body.expires_at and body.starts_at >= body.expires_at:
            raise ProblemError(
                422,
                "Validation error",
                "starts_at must be before expires_at.",
                PROBLEM_VALIDATION,
            )

    async def _out(self, row: Coupon) -> CouponOut:
        return CouponOut(
            id=row.id,
            code=row.code,
            discount_type=row.discount_type,
            value=row.value,
            min_spend_poisha=row.min_spend_poisha,
            category_id=row.category_id,
            starts_at=row.starts_at,
            expires_at=row.expires_at,
            max_redemptions=row.max_redemptions,
            max_per_user=row.max_per_user,
            is_active=row.is_active,
            redemption_count=await self.repo.redemption_count(row.id),
            created_at=row.created_at,
        )
