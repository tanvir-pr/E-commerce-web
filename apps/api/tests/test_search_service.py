"""SearchService filter assembly with a fake Meilisearch client."""

from types import SimpleNamespace

import pytest
from app.search.service import SearchService


class FakeClient:
    def __init__(self) -> None:
        self.last_body: dict | None = None

    async def search(self, body: dict) -> dict:
        self.last_body = body
        return {
            "hits": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "slug": "niacinamide-serum",
                    "name": "Niacinamide Serum",
                    "subtitle": "",
                    "category_slug": "serum",
                    "category_name": "Serum",
                    "routine_step": "am",
                    "from_price_poisha": 120000,
                    "skin_types": ["oily"],
                    "concerns": ["barrier"],
                    "ingredients": ["niacinamide"],
                }
            ],
            "estimatedTotalHits": 1,
            "processingTimeMs": 2,
            "facetDistribution": {
                "concerns": {"barrier": 1, "acne": 0},
                "ingredients": {"niacinamide": 1},
                "skin_types": {"oily": 1},
                "category_slug": {"serum": 1},
            },
        }


@pytest.mark.asyncio
async def test_search_builds_facet_filters() -> None:
    client = FakeClient()
    service = SearchService(
        settings=SimpleNamespace(search_enabled=True),  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )
    out = await service.search(
        q="niacinamide",
        concern="barrier",
        ingredient="niacinamide",
        skin_type="oily",
        category="serum",
        limit=12,
        offset=0,
    )
    assert client.last_body is not None
    assert client.last_body["q"] == "niacinamide"
    assert 'concerns = "barrier"' in client.last_body["filter"]
    assert 'ingredients = "niacinamide"' in client.last_body["filter"]
    assert 'skin_types = "oily"' in client.last_body["filter"]
    assert 'category_slug = "serum"' in client.last_body["filter"]
    assert out.total == 1
    assert out.items[0].slug == "niacinamide-serum"
    assert any(f.value == "barrier" for f in out.facets["concerns"])


@pytest.mark.asyncio
async def test_search_price_and_sort() -> None:
    client = FakeClient()
    service = SearchService(
        settings=SimpleNamespace(search_enabled=True),  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )
    out = await service.search(
        q="",
        min_price_poisha=100000,
        max_price_poisha=200000,
        sort="price_asc",
    )
    assert client.last_body is not None
    assert "from_price_poisha >= 100000" in client.last_body["filter"]
    assert "from_price_poisha <= 200000" in client.last_body["filter"]
    assert client.last_body["sort"] == ["from_price_poisha:asc"]
    assert out.sort == "price_asc"


@pytest.mark.asyncio
async def test_suggest_skips_short_query() -> None:
    client = FakeClient()
    service = SearchService(
        settings=SimpleNamespace(search_enabled=True),  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )
    out = await service.suggest(q="n")
    assert out.items == []
    assert client.last_body is None
