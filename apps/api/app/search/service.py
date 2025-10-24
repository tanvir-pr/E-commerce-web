"""Public product search against Meilisearch."""

from __future__ import annotations

from uuid import UUID

from app.config import Settings, get_settings
from app.problems import PROBLEM_UNAVAILABLE, ProblemError
from app.search.client import MeilisearchClient, MeilisearchError
from app.search.schemas import FacetValueOut, SearchHitOut, SearchOut

FACET_KEYS = ("concerns", "ingredients", "skin_types", "category_slug")


class SearchService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: MeilisearchClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or MeilisearchClient(self.settings)

    async def search(
        self,
        *,
        q: str = "",
        concern: str | None = None,
        ingredient: str | None = None,
        skin_type: str | None = None,
        category: str | None = None,
        limit: int = 24,
        offset: int = 0,
    ) -> SearchOut:
        if not self.settings.search_enabled:
            raise ProblemError(
                503,
                "Search unavailable",
                "Product search is disabled.",
                PROBLEM_UNAVAILABLE,
            )

        filters: list[str] = ['status = "published"']
        if concern:
            filters.append(f'concerns = "{_escape(concern)}"')
        if ingredient:
            filters.append(f'ingredients = "{_escape(ingredient)}"')
        if skin_type:
            filters.append(f'skin_types = "{_escape(skin_type)}"')
        if category:
            filters.append(f'category_slug = "{_escape(category)}"')

        body = {
            "q": q.strip(),
            "limit": limit,
            "offset": offset,
            "filter": filters,
            "facets": list(FACET_KEYS),
            "sort": ["name:asc"],
        }
        try:
            raw = await self.client.search(body)
        except MeilisearchError as exc:
            raise ProblemError(
                503,
                "Search unavailable",
                "The search index is temporarily unavailable.",
                PROBLEM_UNAVAILABLE,
            ) from exc

        hits = [_hit(item) for item in raw.get("hits") or []]
        facet_dist = raw.get("facetDistribution") or {}
        facets: dict[str, list[FacetValueOut]] = {}
        for key in FACET_KEYS:
            bucket = facet_dist.get(key) or {}
            facets[key] = [
                FacetValueOut(value=str(value), count=int(count))
                for value, count in sorted(bucket.items(), key=lambda pair: pair[0])
            ]

        return SearchOut(
            query=q.strip(),
            total=int(raw.get("estimatedTotalHits") or raw.get("totalHits") or len(hits)),
            offset=offset,
            limit=limit,
            processing_time_ms=raw.get("processingTimeMs"),
            items=hits,
            facets=facets,
        )


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _hit(item: dict) -> SearchHitOut:
    return SearchHitOut(
        id=UUID(str(item["id"])),
        slug=str(item.get("slug") or ""),
        name=str(item.get("name") or ""),
        subtitle=(item.get("subtitle") or None) or None,
        category_slug=(item.get("category_slug") or None) or None,
        category_name=(item.get("category_name") or None) or None,
        routine_step=(item.get("routine_step") or None) or None,
        from_price_poisha=item.get("from_price_poisha"),
        skin_types=list(item.get("skin_types") or []),
        concerns=list(item.get("concerns") or []),
        ingredients=list(item.get("ingredients") or []),
    )
