"""Delivery zone CRUD and weight-based shipping quotes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.config import Settings, get_settings
from app.models.shipping import DeliveryWeightTier, DeliveryZone
from app.problems import PROBLEM_VALIDATION, ProblemError
from app.shipping.repository import ShippingRepository
from app.shipping.schemas import (
    DeliveryZoneIn,
    DeliveryZoneListOut,
    DeliveryZoneOut,
    DeliveryZonePatchIn,
    DeliveryZoneSummaryOut,
    ShippingQuoteIn,
    ShippingQuoteOut,
    WeightTierIn,
    WeightTierOut,
)


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


class ShippingService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = ShippingRepository(session)
        self.audit = AuditService(session)

    async def list_public_zones(self) -> list[DeliveryZoneSummaryOut]:
        rows = await self.repo.list_zones(include_inactive=False)
        return [
            DeliveryZoneSummaryOut(
                id=row.id,
                slug=row.slug,
                name=row.name,
                is_default=row.is_default,
                sort_order=row.sort_order,
            )
            for row in rows
        ]

    async def admin_list(self) -> DeliveryZoneListOut:
        rows = await self.repo.list_zones(include_inactive=True)
        return DeliveryZoneListOut(
            items=[self._zone_out(row) for row in rows],
            free_shipping_threshold_poisha=self.settings.free_shipping_threshold_poisha,
            default_variant_weight_grams=self.settings.shipping_default_variant_weight_grams,
        )

    async def admin_get(self, zone_id: UUID) -> DeliveryZoneOut:
        return self._zone_out(await self.repo.require(zone_id))

    async def create_zone(
        self, body: DeliveryZoneIn, *, actor_user_id: UUID
    ) -> DeliveryZoneOut:
        self._validate_tiers(body.tiers)
        if body.is_default:
            await self.repo.clear_default_flags()
        zone = DeliveryZone(
            slug=body.slug.strip().lower(),
            name=body.name.strip(),
            match_districts=self._clean_districts(body.match_districts),
            is_default=body.is_default,
            is_active=body.is_active,
            sort_order=body.sort_order,
            free_shipping_threshold_poisha=body.free_shipping_threshold_poisha,
        )
        zone = await self.repo.add_zone(zone)
        await self.repo.replace_tiers(
            zone,
            [
                DeliveryWeightTier(
                    max_weight_grams=tier.max_weight_grams,
                    charge_poisha=tier.charge_poisha,
                )
                for tier in sorted(body.tiers, key=lambda t: t.max_weight_grams)
            ],
        )
        zone = await self.repo.require(zone.id)
        await self.audit.record(
            action="shipping.zone.created",
            actor_user_id=actor_user_id,
            subject_type="delivery_zone",
            subject_id=str(zone.id),
            meta={"slug": zone.slug},
        )
        return self._zone_out(zone)

    async def patch_zone(
        self, zone_id: UUID, body: DeliveryZonePatchIn, *, actor_user_id: UUID
    ) -> DeliveryZoneOut:
        zone = await self.repo.require(zone_id)
        data = body.model_dump(exclude_unset=True)
        if "tiers" in data and data["tiers"] is not None:
            tiers = [WeightTierIn.model_validate(t) for t in data.pop("tiers")]
            self._validate_tiers(tiers)
            await self.repo.replace_tiers(
                zone,
                [
                    DeliveryWeightTier(
                        max_weight_grams=tier.max_weight_grams,
                        charge_poisha=tier.charge_poisha,
                    )
                    for tier in sorted(tiers, key=lambda t: t.max_weight_grams)
                ],
            )
        if "slug" in data and data["slug"] is not None:
            zone.slug = str(data["slug"]).strip().lower()
        if "name" in data and data["name"] is not None:
            zone.name = str(data["name"]).strip()
        if "match_districts" in data and data["match_districts"] is not None:
            zone.match_districts = self._clean_districts(list(data["match_districts"]))
        if "is_active" in data and data["is_active"] is not None:
            zone.is_active = bool(data["is_active"])
        if "sort_order" in data and data["sort_order"] is not None:
            zone.sort_order = int(data["sort_order"])
        if "free_shipping_threshold_poisha" in data:
            zone.free_shipping_threshold_poisha = data["free_shipping_threshold_poisha"]
        if data.get("is_default") is True:
            await self.repo.clear_default_flags(except_id=zone.id)
            zone.is_default = True
        elif data.get("is_default") is False:
            zone.is_default = False
        zone = await self.repo.save(zone)
        await self.audit.record(
            action="shipping.zone.updated",
            actor_user_id=actor_user_id,
            subject_type="delivery_zone",
            subject_id=str(zone.id),
        )
        return self._zone_out(zone)

    async def delete_zone(self, zone_id: UUID, *, actor_user_id: UUID) -> None:
        zone = await self.repo.require(zone_id)
        if zone.is_default:
            raise ProblemError(
                422,
                "Validation error",
                "Set another default zone before deleting this one.",
                PROBLEM_VALIDATION,
            )
        await self.repo.soft_delete(zone)
        await self.audit.record(
            action="shipping.zone.deleted",
            actor_user_id=actor_user_id,
            subject_type="delivery_zone",
            subject_id=str(zone_id),
        )

    async def quote(self, body: ShippingQuoteIn) -> ShippingQuoteOut:
        zone, matched_by = await self._resolve_zone(body.district, body.city)
        weight = await self._total_weight(body)
        charge = self._charge_for_weight(zone, weight)
        threshold = (
            zone.free_shipping_threshold_poisha
            if zone.free_shipping_threshold_poisha is not None
            else self.settings.free_shipping_threshold_poisha
        )
        free = body.subtotal_poisha >= threshold and threshold > 0
        return ShippingQuoteOut(
            zone_id=zone.id,
            zone_slug=zone.slug,
            zone_name=zone.name,
            total_weight_grams=weight,
            charge_poisha=0 if free else charge,
            free_shipping_applied=free,
            free_shipping_threshold_poisha=threshold,
            matched_by=matched_by,
        )

    async def _resolve_zone(
        self, district: str | None, city: str | None
    ) -> tuple[DeliveryZone, str]:
        rows = await self.repo.list_zones(include_inactive=False)
        if not rows:
            raise ProblemError(
                422,
                "Validation error",
                "No active delivery zones are configured.",
                PROBLEM_VALIDATION,
            )
        needle_district = _norm(district)
        needle_city = _norm(city)
        for zone in rows:
            districts = {_norm(str(d)) for d in (zone.match_districts or []) if str(d).strip()}
            if needle_district and needle_district in districts:
                return zone, "district"
            if needle_city and needle_city in districts:
                return zone, "city"
        default = next((z for z in rows if z.is_default), None) or rows[-1]
        return default, "default"

    async def _total_weight(self, body: ShippingQuoteIn) -> int:
        if body.weight_grams is not None and not body.lines:
            return body.weight_grams
        if not body.lines:
            if body.weight_grams is not None:
                return body.weight_grams
            raise ProblemError(
                422,
                "Validation error",
                "Provide weight_grams or cart lines to quote shipping.",
                PROBLEM_VALIDATION,
            )
        variants = await self.repo.get_variants([line.variant_id for line in body.lines])
        missing = [str(line.variant_id) for line in body.lines if line.variant_id not in variants]
        if missing:
            raise ProblemError(
                422,
                "Validation error",
                f"Unknown variant(s): {', '.join(missing[:5])}",
                PROBLEM_VALIDATION,
            )
        default_w = self.settings.shipping_default_variant_weight_grams
        total = 0
        for line in body.lines:
            variant = variants[line.variant_id]
            unit = variant.weight_grams if variant.weight_grams is not None else default_w
            total += int(unit) * line.qty
        if body.weight_grams is not None:
            return body.weight_grams
        return total

    def _charge_for_weight(self, zone: DeliveryZone, weight_grams: int) -> int:
        tiers = sorted(zone.tiers, key=lambda t: t.max_weight_grams)
        if not tiers:
            raise ProblemError(
                422,
                "Validation error",
                f"Zone {zone.slug} has no weight tiers.",
                PROBLEM_VALIDATION,
            )
        for tier in tiers:
            if weight_grams <= tier.max_weight_grams:
                return int(tier.charge_poisha)
        return int(tiers[-1].charge_poisha)

    def _validate_tiers(self, tiers: list[WeightTierIn]) -> None:
        if not tiers:
            raise ProblemError(
                422,
                "Validation error",
                "At least one weight tier is required.",
                PROBLEM_VALIDATION,
            )
        maxes = [t.max_weight_grams for t in tiers]
        if len(maxes) != len(set(maxes)):
            raise ProblemError(
                422,
                "Validation error",
                "Weight tier max_weight_grams values must be unique.",
                PROBLEM_VALIDATION,
            )

    def _clean_districts(self, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            name = raw.strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(name)
        return cleaned

    def _zone_out(self, zone: DeliveryZone) -> DeliveryZoneOut:
        return DeliveryZoneOut(
            id=zone.id,
            slug=zone.slug,
            name=zone.name,
            match_districts=[str(d) for d in (zone.match_districts or [])],
            is_default=zone.is_default,
            is_active=zone.is_active,
            sort_order=zone.sort_order,
            free_shipping_threshold_poisha=zone.free_shipping_threshold_poisha,
            created_at=zone.created_at,
            updated_at=zone.updated_at,
            tiers=[
                WeightTierOut(
                    id=tier.id,
                    max_weight_grams=tier.max_weight_grams,
                    charge_poisha=tier.charge_poisha,
                )
                for tier in sorted(zone.tiers, key=lambda t: t.max_weight_grams)
            ],
        )
