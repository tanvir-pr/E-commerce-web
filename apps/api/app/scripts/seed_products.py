"""Seed a couple of published skincare products. Idempotent."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Attribute, Category
from app.models.product import Product, ProductAttribute, ProductVariant
from app.session import SessionFactory


async def _attr(session: AsyncSession, kind: str, slug: str) -> Attribute | None:
    result = await session.execute(
        select(Attribute).where(Attribute.kind == kind, Attribute.slug == slug)
    )
    return result.scalar_one_or_none()


async def seed() -> None:
    async with SessionFactory() as session:
        serum = (
            await session.execute(select(Category).where(Category.slug == "serum"))
        ).scalar_one_or_none()
        sunscreen = (
            await session.execute(select(Category).where(Category.slug == "sunscreen"))
        ).scalar_one_or_none()
        if serum is None or sunscreen is None:
            print("catalog categories missing; run seed_catalog first")
            return

        niacinamide = await _attr(session, "ingredient", "niacinamide")
        oily = await _attr(session, "skin_type", "oily")
        acne = await _attr(session, "concern", "acne")
        hydration = await _attr(session, "concern", "hydration")

        samples: list[dict[str, Any]] = [
            {
                "slug": "daily-barrier-serum",
                "name": "Daily Barrier Serum",
                "subtitle": "Niacinamide 10% for oil control",
                "category_id": serum.id,
                "routine_step": "am",
                "how_to_use": "Apply 2–3 drops after toner, before moisturizer.",
                "ingredients_text": "Aqua, Niacinamide, Glycerin, Panthenol.",
                "warnings": "Patch test before first use.",
                "pao_months": 12,
                "shelf_life_months": 36,
                "attrs": [a for a in (niacinamide, oily, acne) if a is not None],
                "variants": [
                    {
                        "sku": "SER-BAR-30",
                        "size_label": "30 ml",
                        "price_poisha": 145000,
                        "compare_at_poisha": 165000,
                        "weight_grams": 45,
                    }
                ],
            },
            {
                "slug": "clear-guard-spf50",
                "name": "Clear Guard SPF 50",
                "subtitle": "Lightweight daily sunscreen",
                "category_id": sunscreen.id,
                "routine_step": "am",
                "how_to_use": "Apply as the last step of your morning routine.",
                "ingredients_text": "Aqua, Zinc Oxide, Caprylic/Capric Triglyceride.",
                "warnings": "Reapply every 2 hours outdoors.",
                "pao_months": 12,
                "shelf_life_months": 24,
                "attrs": [a for a in (hydration, oily) if a is not None],
                "variants": [
                    {
                        "sku": "SUN-CG-50",
                        "size_label": "50 ml",
                        "spf": 50,
                        "price_poisha": 120000,
                        "weight_grams": 70,
                    }
                ],
            },
        ]

        created = 0
        for sample in samples:
            existing = (
                await session.execute(select(Product).where(Product.slug == sample["slug"]))
            ).scalar_one_or_none()
            if existing is not None:
                continue
            category_id: UUID = sample["category_id"]
            product = Product(
                category_id=category_id,
                slug=sample["slug"],
                name=sample["name"],
                subtitle=sample["subtitle"],
                how_to_use=sample["how_to_use"],
                ingredients_text=sample["ingredients_text"],
                warnings=sample["warnings"],
                routine_step=sample["routine_step"],
                pao_months=sample["pao_months"],
                shelf_life_months=sample["shelf_life_months"],
                status="published",
                published_at=datetime.now(UTC),
            )
            session.add(product)
            await session.flush()
            attrs: list[Attribute] = sample["attrs"]
            for attribute in attrs:
                session.add(
                    ProductAttribute(product_id=product.id, attribute_id=attribute.id)
                )
            variants: list[dict[str, Any]] = sample["variants"]
            for index, variant in enumerate(variants):
                session.add(
                    ProductVariant(
                        product_id=product.id,
                        sku=str(variant["sku"]),
                        size_label=variant.get("size_label"),
                        spf=variant.get("spf"),
                        price_poisha=int(variant["price_poisha"]),
                        compare_at_poisha=variant.get("compare_at_poisha"),
                        weight_grams=variant.get("weight_grams"),
                        sort_order=index * 10,
                        is_active=True,
                    )
                )
            created += 1

        await session.commit()
        print(f"products ready: created={created}")


if __name__ == "__main__":
    asyncio.run(seed())
