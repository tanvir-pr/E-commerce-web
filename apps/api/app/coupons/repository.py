"""Coupon persistence."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Category
from app.models.coupon import Coupon, CouponRedemption
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class CouponRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: Coupon) -> Coupon:
        self.session.add(row)
        await self.session.flush()
        return row

    async def save(self, row: Coupon) -> Coupon:
        await self.session.flush()
        return row

    async def get(self, coupon_id: UUID) -> Coupon | None:
        result = await self.session.execute(select(Coupon).where(Coupon.id == coupon_id))
        return result.scalar_one_or_none()

    async def require(self, coupon_id: UUID) -> Coupon:
        row = await self.get(coupon_id)
        if row is None:
            raise ProblemError(404, "Not found", "Coupon not found.", PROBLEM_NOT_FOUND)
        return row

    async def get_by_code(self, code: str) -> Coupon | None:
        result = await self.session.execute(
            select(Coupon).where(Coupon.code == code.strip().upper())
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Coupon]:
        result = await self.session.execute(
            select(Coupon).order_by(Coupon.created_at.desc()).limit(200)
        )
        return list(result.scalars().all())

    async def delete(self, row: Coupon) -> None:
        await self.session.delete(row)
        await self.session.flush()

    async def redemption_count(self, coupon_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(CouponRedemption)
            .where(CouponRedemption.coupon_id == coupon_id)
        )
        return int(result.scalar_one() or 0)

    async def user_redemption_count(self, coupon_id: UUID, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(CouponRedemption)
            .where(
                CouponRedemption.coupon_id == coupon_id,
                CouponRedemption.user_id == user_id,
            )
        )
        return int(result.scalar_one() or 0)

    async def add_redemption(self, row: CouponRedemption) -> CouponRedemption:
        self.session.add(row)
        await self.session.flush()
        return row

    async def category_slug(self, category_id: UUID) -> str | None:
        result = await self.session.execute(
            select(Category.slug).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()
