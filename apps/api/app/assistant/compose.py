"""Grounded answer composition from retrieved context (no external LLM required)."""

from __future__ import annotations

from app.assistant.retrieval import RetrievedChunk, RetrievedProduct
from app.assistant.schemas import AssistantCitationOut, AssistantProductCardOut


def compose_reply(
    *,
    intent: str,
    message: str,
    chunks: list[RetrievedChunk],
    products: list[tuple[RetrievedProduct, int | None, int]],
) -> tuple[str, float, bool, list[AssistantCitationOut], list[AssistantProductCardOut]]:
    citations = [
        AssistantCitationOut(
            source=c.source,
            title=c.title,
            excerpt=_excerpt(c.body),
        )
        for c in chunks[:3]
    ]
    cards: list[AssistantProductCardOut] = []
    for item, price, qty in products[:4]:
        p = item.product
        cards.append(
            AssistantProductCardOut(
                id=p.id,
                slug=p.slug,
                name=p.name,
                subtitle=p.subtitle,
                from_price_poisha=price,
                qty_available=qty,
                in_stock=qty > 0,
                routine_step=p.routine_step,
                concerns=item.concerns,
                ingredients=item.ingredients,
            )
        )

    if intent == "order":
        reply = (
            "I can help with catalog and store policies, but I cannot look up a live order "
            "status here yet. Open Orders in your account for tracking, or ask me to hand "
            "this to support and a staff member will follow up."
        )
        return reply, 0.35, True, citations, cards

    if intent == "policy" and chunks:
        parts = [f"**{c.title}.** {c.body}" for c in chunks[:2]]
        reply = "Here’s what our store policy says:\n\n" + "\n\n".join(parts)
        if "return" in message.lower() or "refund" in message.lower():
            reply += "\n\nYou can start a return from the order page after delivery."
        return reply, min(0.55 + 0.15 * len(chunks), 0.95), False, citations, cards

    if intent in {"product", "routine", "ingredient"} and (cards or chunks):
        lines: list[str] = []
        if intent == "routine" and any(c.source == "routine" for c in chunks):
            routine = next(c for c in chunks if c.source == "routine")
            lines.append(routine.body)
        if intent == "ingredient" and any(c.source == "ingredients" for c in chunks):
            ing = next(c for c in chunks if c.source == "ingredients")
            lines.append(ing.body)
        if cards:
            lines.append("Based on the catalog, these look relevant (prices and stock refreshed live):")
            for card in cards:
                stock = "in stock" if card.in_stock else "currently out of stock"
                price = (
                    f"from ৳{card.from_price_poisha / 100:.0f}"
                    if card.from_price_poisha is not None
                    else "price on product page"
                )
                detail_bits: list[str] = []
                if card.routine_step:
                    detail_bits.append(f"step {card.routine_step}")
                if card.concerns:
                    detail_bits.append("concerns: " + ", ".join(card.concerns[:3]))
                extra = f" ({'; '.join(detail_bits)})" if detail_bits else ""
                lines.append(f"• {card.name} — {price}, {stock}{extra}")
                if item_how_to(products, card.slug):
                    lines.append(f"  How to use: {item_how_to(products, card.slug)}")
        elif chunks:
            lines.append(chunks[0].body)
        reply = "\n".join(lines)
        conf = 0.5 + (0.1 * len(cards)) + (0.1 if chunks else 0)
        return reply, min(conf, 0.92), conf < 0.55, citations, cards

    if chunks:
        reply = chunks[0].body + "\n\nIf this does not answer your question, I can connect you to support."
        return reply, 0.5, True, citations, cards

    reply = (
        "I’m not sure I have a solid answer from our catalog or policies. "
        "Try rephrasing with a product name, ingredient, or concern — "
        "or ask me to hand this to a human support agent."
    )
    return reply, 0.2, True, citations, cards


def item_how_to(
    products: list[tuple[RetrievedProduct, int | None, int]], slug: str
) -> str | None:
    for item, _price, _qty in products:
        if item.product.slug == slug and item.product.how_to_use:
            text = item.product.how_to_use.strip()
            return text if len(text) <= 180 else text[:177] + "…"
    return None


def _excerpt(body: str, limit: int = 160) -> str:
    text = " ".join(body.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"
