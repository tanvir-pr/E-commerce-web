"""Delivery zone persistence."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.models.product import ProductVariant
from app.models.shipping import DeliveryWeightTier, DeliveryZone
from app.problems import PROBLEM_CONFLICT, PROBLEM_NOT_FOUND, ProblemError


class ShippingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _zone_options(self) -> Sequence[ExecutableOption]:
        return (selectinload(DeliveryZone.tiers),)

    async def list_zones(self, *, include_inactive: bool) -> list[DeliveryZone]:
        stmt = (
            select(DeliveryZone)
            .options(*self._zone_options())
            .where(DeliveryZone.deleted_at.is_(None))
            .order_by(DeliveryZone.sort_order.asc(), DeliveryZone.name.asc())
        )
        if not include_inactive:
            stmt = stmt.where(DeliveryZone.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_id(self, zone_id: UUID) -> DeliveryZone | None:
        result = await self.session.execute(
            select(DeliveryZone)
            .options(*self._zone_options())
            .where(DeliveryZone.id == zone_id, DeliveryZone.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def require(self, zone_id: UUID) -> DeliveryZone:
        row = await self.get_by_id(zone_id)
        if row is None:
            raise ProblemError(404, "Not found", "Delivery zone not found.", PROBLEM_NOT_FOUND)
        return row

    async def get_by_slug(self, slug: str) -> DeliveryZone | None:
        result = await self.session.execute(
            select(DeliveryZone)
            .options(*self._zone_options())
            .where(DeliveryZone.slug == slug, DeliveryZone.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def add_zone(self, zone: DeliveryZone) -> DeliveryZone:
        self.session.add(zone)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A delivery zone with that slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return await self.require(zone.id)

    async def save(self, zone: DeliveryZone) -> DeliveryZone:
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A delivery zone with that slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return await self.require(zone.id)

    async def soft_delete(self, zone: DeliveryZone) -> None:
        zone.deleted_at = datetime.now(UTC)
        zone.is_active = False
        zone.is_default = False
        await self.session.flush()

    async def clear_default_flags(self, *, except_id: UUID | None = None) -> None:
        result = await self.session.execute(
            select(DeliveryZone).where(
                DeliveryZone.is_default.is_(True),
                DeliveryZone.deleted_at.is_(None),
            )
        )
        for row in result.scalars().all():
            if except_id is not None and row.id == except_id:
                continue
            row.is_default = False
        await self.session.flush()

    async def replace_tiers(
        self, zone: DeliveryZone, tiers: list[DeliveryWeightTier]
    ) -> None:
        for existing in list(zone.tiers):
            await self.session.delete(existing)
        await self.session.flush()
        for tier in tiers:
            tier.zone_id = zone.id
            self.session.add(tier)
        await self.session.flush()

    async def get_variants(self, variant_ids: list[UUID]) -> dict[UUID, ProductVariant]:
        if not variant_ids:
            return {}
        result = await self.session.execute(
            select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
        )
        return {row.id: row for row in result.scalars().all()}
