"""Feature flag persistence."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feature_flag import FeatureFlag
from app.models.order import Order
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class FeatureFlagRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[FeatureFlag]:
        result = await self.session.execute(
            select(FeatureFlag).order_by(FeatureFlag.key.asc())
        )
        return list(result.scalars().all())

    async def get_by_key(self, key: str) -> FeatureFlag | None:
        result = await self.session.execute(
            select(FeatureFlag).where(FeatureFlag.key == key)
        )
        return result.scalar_one_or_none()

    async def require(self, flag_id: UUID) -> FeatureFlag:
        result = await self.session.execute(
            select(FeatureFlag).where(FeatureFlag.id == flag_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ProblemError(404, "Not found", "Flag not found.", PROBLEM_NOT_FOUND)
        return row

    async def save(self, row: FeatureFlag) -> FeatureFlag:
        await self.session.flush()
        return row

    async def count_cancelled_cod(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(
                Order.user_id == user_id,
                Order.payment_method == "cod",
                Order.status == "cancelled",
            )
        )
        return int(result.scalar_one() or 0)
