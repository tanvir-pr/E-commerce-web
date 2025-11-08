"""ShippingService zone match, weight tiers, and free-shipping threshold."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.config import Settings
from app.problems import ProblemError
from app.shipping.schemas import ShippingQuoteIn, ShippingQuoteLineIn
from app.shipping.service import ShippingService


class FakeSession:
    async def flush(self) -> None:
        return None

    async def delete(self, _obj: object) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeRepo:
    def __init__(self) -> None:
        self.zones: list[SimpleNamespace] = []
        self.variants: dict[UUID, SimpleNamespace] = {}

    async def list_zones(self, *, include_inactive: bool) -> list[SimpleNamespace]:
        rows = self.zones
        if not include_inactive:
            rows = [z for z in rows if z.is_active and z.deleted_at is None]
        return sorted(rows, key=lambda z: (z.sort_order, z.name))

    async def get_variants(self, variant_ids: list[UUID]) -> dict[UUID, SimpleNamespace]:
        return {vid: self.variants[vid] for vid in variant_ids if vid in self.variants}


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://x:x@localhost/x",
        redis_url="redis://localhost:6379/0",
        free_shipping_threshold_poisha=300000,
        shipping_default_variant_weight_grams=100,
    )


def _service(repo: FakeRepo) -> ShippingService:
    service = ShippingService(FakeSession(), settings=_settings())  # type: ignore[arg-type]
    service.repo = repo  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    return service


def _zone(
    *,
    slug: str,
    name: str,
    districts: list[str],
    is_default: bool,
    tiers: list[tuple[int, int]],
    threshold: int | None = None,
    sort_order: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        slug=slug,
        name=name,
        match_districts=districts,
        is_default=is_default,
        is_active=True,
        sort_order=sort_order,
        free_shipping_threshold_poisha=threshold,
        deleted_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        tiers=[
            SimpleNamespace(id=uuid4(), max_weight_grams=m, charge_poisha=c)
            for m, c in tiers
        ],
    )


@pytest.mark.asyncio
async def test_quote_matches_district_and_weight_tier() -> None:
    repo = FakeRepo()
    repo.zones = [
        _zone(
            slug="dhaka-metro",
            name="Dhaka metro",
            districts=["Dhaka", "Gazipur"],
            is_default=False,
            tiers=[(500, 6000), (1000, 8000), (50000, 12000)],
            threshold=250000,
            sort_order=10,
        ),
        _zone(
            slug="rest",
            name="Rest",
            districts=[],
            is_default=True,
            tiers=[(500, 12000), (50000, 20000)],
            threshold=350000,
            sort_order=100,
        ),
    ]
    service = _service(repo)
    quote = await service.quote(
        ShippingQuoteIn(district=" dhaka ", weight_grams=750, subtotal_poisha=100000)
    )
    assert quote.zone_slug == "dhaka-metro"
    assert quote.matched_by == "district"
    assert quote.charge_poisha == 8000
    assert quote.free_shipping_applied is False


@pytest.mark.asyncio
async def test_quote_falls_back_to_default_and_applies_free_shipping() -> None:
    repo = FakeRepo()
    repo.zones = [
        _zone(
            slug="dhaka-metro",
            name="Dhaka metro",
            districts=["Dhaka"],
            is_default=False,
            tiers=[(50000, 6000)],
            threshold=250000,
        ),
        _zone(
            slug="rest",
            name="Rest",
            districts=[],
            is_default=True,
            tiers=[(50000, 20000)],
            threshold=350000,
        ),
    ]
    service = _service(repo)
    quote = await service.quote(
        ShippingQuoteIn(district="Chattogram", weight_grams=200, subtotal_poisha=400000)
    )
    assert quote.zone_slug == "rest"
    assert quote.matched_by == "default"
    assert quote.free_shipping_applied is True
    assert quote.charge_poisha == 0


@pytest.mark.asyncio
async def test_quote_sums_line_weights_with_default_when_missing() -> None:
    repo = FakeRepo()
    vid_known = uuid4()
    vid_missing_weight = uuid4()
    repo.variants = {
        vid_known: SimpleNamespace(id=vid_known, weight_grams=45),
        vid_missing_weight: SimpleNamespace(id=vid_missing_weight, weight_grams=None),
    }
    repo.zones = [
        _zone(
            slug="rest",
            name="Rest",
            districts=[],
            is_default=True,
            tiers=[(500, 12000), (50000, 20000)],
        )
    ]
    service = _service(repo)
    quote = await service.quote(
        ShippingQuoteIn(
            lines=[
                ShippingQuoteLineIn(variant_id=vid_known, qty=2),
                ShippingQuoteLineIn(variant_id=vid_missing_weight, qty=1),
            ]
        )
    )
    # 45*2 + 100*1 = 190
    assert quote.total_weight_grams == 190
    assert quote.charge_poisha == 12000


@pytest.mark.asyncio
async def test_quote_requires_weight_or_lines() -> None:
    repo = FakeRepo()
    repo.zones = [
        _zone(
            slug="rest",
            name="Rest",
            districts=[],
            is_default=True,
            tiers=[(50000, 1000)],
        )
    ]
    service = _service(repo)
    with pytest.raises(ProblemError):
        await service.quote(ShippingQuoteIn(district="Dhaka"))
