"""Lexical retrieval over policy chunks and catalog (Meili + SQL fallback)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.assistant.repository import AssistantRepository
from app.models.assistant import KnowledgeChunk
from app.models.product import Product
from app.search.service import SearchService


@dataclass
class RetrievedChunk:
    source: str
    title: str
    body: str
    score: float


@dataclass
class RetrievedProduct:
    product: Product
    score: float
    concerns: list[str]
    ingredients: list[str]


_tokenize = re.compile(r"[a-z0-9]+", re.I)

POLICY_HINTS = {
    "return",
    "refund",
    "shipping",
    "delivery",
    "privacy",
    "payment",
    "cod",
    "bkash",
    "sslcommerz",
    "card",
    "policy",
    "unopened",
}
PRODUCT_HINTS = {
    "serum",
    "cleanser",
    "moisturizer",
    "sunscreen",
    "toner",
    "mask",
    "routine",
    "ingredient",
    "niacinamide",
    "retinol",
    "acne",
    "dry",
    "oily",
    "sensitive",
    "hydration",
    "barrier",
    "pigmentation",
    "aging",
    "spf",
    "how",
    "use",
    "am",
    "pm",
}
ORDER_HINTS = {"order", "tracking", "shipment", "courier", "delivered", "packed"}


def classify_intent(message: str) -> str:
    tokens = set(_tokenize.findall(message.lower()))
    if tokens & ORDER_HINTS and not (tokens & PRODUCT_HINTS):
        return "order"
    if tokens & POLICY_HINTS and not (tokens & PRODUCT_HINTS):
        return "policy"
    if tokens & {"routine", "am", "pm"}:
        return "routine"
    if tokens & {"ingredient", "niacinamide", "retinol", "acid", "ceramide"}:
        return "ingredient"
    if tokens & PRODUCT_HINTS:
        return "product"
    if tokens & POLICY_HINTS:
        return "policy"
    return "unknown"


def score_chunk(chunk: KnowledgeChunk, tokens: set[str]) -> float:
    hay = " ".join(
        [
            chunk.title.lower(),
            chunk.body.lower(),
            " ".join(str(t).lower() for t in (chunk.tags or [])),
        ]
    )
    score = 0.0
    for tok in tokens:
        if len(tok) < 3:
            continue
        if tok in hay:
            score += 1.0
        if chunk.tags and tok in [str(t).lower() for t in chunk.tags]:
            score += 1.5
    if chunk.source in tokens:
        score += 2.0
    return score


async def retrieve_policy(
    repo: AssistantRepository, message: str, *, locale: str, limit: int = 3
) -> list[RetrievedChunk]:
    tokens = set(_tokenize.findall(message.lower()))
    chunks = await repo.list_active_chunks(locale=locale)
    scored = [
        RetrievedChunk(
            source=c.source,
            title=c.title,
            body=c.body,
            score=score_chunk(c, tokens),
        )
        for c in chunks
    ]
    scored.sort(key=lambda r: r.score, reverse=True)
    return [r for r in scored if r.score > 0][:limit]


async def retrieve_products(
    repo: AssistantRepository,
    search: SearchService,
    message: str,
    *,
    limit: int = 4,
) -> list[RetrievedProduct]:
    hits: list[RetrievedProduct] = []
    try:
        out = await search.search(q=message, limit=limit, offset=0)
        ids = [h.id for h in out.items]
        products = await repo.get_published_products(ids)
        by_id = {p.id: p for p in products}
        for hit in out.items:
            product = by_id.get(hit.id)
            if product is None:
                continue
            hits.append(
                RetrievedProduct(
                    product=product,
                    score=1.0,
                    concerns=list(hit.concerns or []),
                    ingredients=list(hit.ingredients or []),
                )
            )
    except Exception:
        products = await repo.search_products_sql(message, limit=limit)
        for product in products:
            attrs = _attrs(product)
            hits.append(
                RetrievedProduct(
                    product=product,
                    score=0.7,
                    concerns=attrs["concerns"],
                    ingredients=attrs["ingredients"],
                )
            )
    return hits[:limit]


def _attrs(product: Product) -> dict[str, list[str]]:
    concerns: list[str] = []
    ingredients: list[str] = []
    for attr in product.attributes or []:
        if not getattr(attr, "is_active", True):
            continue
        if attr.kind == "concern":
            concerns.append(attr.slug)
        elif attr.kind == "ingredient":
            ingredients.append(attr.slug)
    return {"concerns": concerns, "ingredients": ingredients}


async def live_product_card(
    repo: AssistantRepository, item: RetrievedProduct
) -> tuple[UUID, int | None, int]:
    product = item.product
    price = await repo.min_price_poisha(product.id)
    qty = await repo.qty_on_hand_for_product(product.id)
    return product.id, price, qty
