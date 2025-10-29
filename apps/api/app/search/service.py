"""Public product search against Meilisearch."""

from __future__ import annotations

from uuid import UUID

from app.config import Settings, get_settings
from app.problems import PROBLEM_UNAVAILABLE, PROBLEM_VALIDATION, ProblemError
from app.search.client import MeilisearchClient, MeilisearchError
from app.search.schemas import (
    FacetValueOut,
    SearchHitOut,
    SearchOut,
    SearchSort,
    SuggestHitOut,
    SuggestOut,
)

FACET_KEYS = ("concerns", "ingredients", "skin_types", "category_slug")
SORT_MAP: dict[SearchSort, list[str] | None] = {
    "relevance": None,
    "name_asc": ["name:asc"],
    "name_desc": ["name:desc"],
    "price_asc": ["from_price_poisha:asc"],
    "price_desc": ["from_price_poisha:desc"],
}


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
        min_price_poisha: int | None = None,
        max_price_poisha: int | None = None,
        sort: SearchSort = "relevance",
        limit: int = 24,
        offset: int = 0,
    ) -> SearchOut:
        self._require_enabled()
        if sort not in SORT_MAP:
            raise ProblemError(
                422,
                "Validation error",
                f"sort must be one of: {', '.join(sorted(SORT_MAP))}",
                PROBLEM_VALIDATION,
            )
        if (
            min_price_poisha is not None
            and max_price_poisha is not None
            and min_price_poisha > max_price_poisha
        ):
            raise ProblemError(
                422,
                "Validation error",
                "min_price_poisha cannot exceed max_price_poisha.",
                PROBLEM_VALIDATION,
            )

        filters = _filters(
            concern=concern,
            ingredient=ingredient,
            skin_type=skin_type,
            category=category,
            min_price_poisha=min_price_poisha,
            max_price_poisha=max_price_poisha,
        )
        body: dict = {
            "q": q.strip(),
            "limit": limit,
            "offset": offset,
            "filter": filters,
            "facets": list(FACET_KEYS),
        }
        sort_keys = SORT_MAP[sort]
        # Empty query needs an explicit sort; relevance with no query is unstable.
        if sort_keys is not None:
            body["sort"] = sort_keys
        elif not q.strip():
            body["sort"] = ["name:asc"]

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
                if int(count) > 0
            ]

        return SearchOut(
            query=q.strip(),
            total=int(raw.get("estimatedTotalHits") or raw.get("totalHits") or len(hits)),
            offset=offset,
            limit=limit,
            sort=sort,
            processing_time_ms=raw.get("processingTimeMs"),
            items=hits,
            facets=facets,
        )

    async def suggest(self, *, q: str, limit: int = 8) -> SuggestOut:
        self._require_enabled()
        query = q.strip()
        if len(query) < 2:
            return SuggestOut(query=query, items=[])
        body = {
            "q": query,
            "limit": limit,
            "filter": ['status = "published"'],
            "attributesToRetrieve": [
                "slug",
                "name",
                "subtitle",
                "category_slug",
                "from_price_poisha",
            ],
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
        items = [
            SuggestHitOut(
                slug=str(item.get("slug") or ""),
                name=str(item.get("name") or ""),
                subtitle=(item.get("subtitle") or None) or None,
                category_slug=(item.get("category_slug") or None) or None,
                from_price_poisha=item.get("from_price_poisha"),
            )
            for item in raw.get("hits") or []
            if item.get("slug") and item.get("name")
        ]
        return SuggestOut(query=query, items=items)

    def _require_enabled(self) -> None:
        if not self.settings.search_enabled:
            raise ProblemError(
                503,
                "Search unavailable",
                "Product search is disabled.",
                PROBLEM_UNAVAILABLE,
            )


def _filters(
    *,
    concern: str | None,
    ingredient: str | None,
    skin_type: str | None,
    category: str | None,
    min_price_poisha: int | None,
    max_price_poisha: int | None,
) -> list[str]:
    filters: list[str] = ['status = "published"']
    if concern:
        filters.append(f'concerns = "{_escape(concern)}"')
    if ingredient:
        filters.append(f'ingredients = "{_escape(ingredient)}"')
    if skin_type:
        filters.append(f'skin_types = "{_escape(skin_type)}"')
    if category:
        filters.append(f'category_slug = "{_escape(category)}"')
    if min_price_poisha is not None:
        filters.append(f"from_price_poisha >= {int(min_price_poisha)}")
    if max_price_poisha is not None:
        filters.append(f"from_price_poisha <= {int(max_price_poisha)}")
    return filters


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
