"""Build Meilisearch documents from Product rows."""

from __future__ import annotations

from typing import Any

from app.models.product import Product
from app.products.constants import PUBLIC_LIST_STATUS


def product_document(row: Product) -> dict[str, Any] | None:
    """Return an index document for a publicly searchable product, else None."""
    if row.deleted_at is not None or row.status != PUBLIC_LIST_STATUS:
        return None

    by_kind: dict[str, list[str]] = {
        "skin_type": [],
        "concern": [],
        "ingredient": [],
        "texture": [],
        "claim": [],
    }
    for attr in row.attributes or []:
        if attr.kind in by_kind and attr.is_active:
            by_kind[attr.kind].append(attr.slug)

    active = [v for v in (row.variants or []) if v.is_active]
    prices = [v.price_poisha for v in active] or [
        v.price_poisha for v in (row.variants or [])
    ]

    return {
        "id": str(row.id),
        "slug": row.slug,
        "name": row.name,
        "subtitle": row.subtitle or "",
        "description": row.description or "",
        "ingredients_text": row.ingredients_text or "",
        "category_slug": row.category.slug if row.category else "",
        "category_name": row.category.name if row.category else "",
        "routine_step": row.routine_step or "",
        "status": row.status,
        "from_price_poisha": min(prices) if prices else None,
        "skin_types": sorted(set(by_kind["skin_type"])),
        "concerns": sorted(set(by_kind["concern"])),
        "ingredients": sorted(set(by_kind["ingredient"])),
        "textures": sorted(set(by_kind["texture"])),
        "claims": sorted(set(by_kind["claim"])),
        "published_at": int(row.published_at.timestamp()) if row.published_at else 0,
    }
