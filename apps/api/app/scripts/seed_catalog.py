"""Seed skincare category tree and filter attributes. Idempotent."""

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.constants import (
    DEFAULT_CLAIMS,
    DEFAULT_CONCERNS,
    DEFAULT_INGREDIENTS,
    DEFAULT_LEAF_CATEGORIES,
    DEFAULT_SKIN_TYPES,
    DEFAULT_TEXTURES,
)
from app.models.catalog import Attribute, Category, CategoryAttribute
from app.session import SessionFactory


async def _ensure_attribute(
    session: AsyncSession,
    *,
    kind: str,
    slug: str,
    name: str,
    sort_order: int,
) -> Attribute:
    result = await session.execute(
        select(Attribute).where(Attribute.kind == kind, Attribute.slug == slug)
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    row = Attribute(kind=kind, slug=slug, name=name, sort_order=sort_order, is_active=True)
    session.add(row)
    await session.flush()
    return row


async def seed() -> None:
    async with SessionFactory() as session:
        attribute_ids: list[UUID] = []
        for kind, rows in (
            ("skin_type", DEFAULT_SKIN_TYPES),
            ("concern", DEFAULT_CONCERNS),
            ("ingredient", DEFAULT_INGREDIENTS),
            ("texture", DEFAULT_TEXTURES),
            ("claim", DEFAULT_CLAIMS),
        ):
            for slug, name, sort_order in rows:
                attr = await _ensure_attribute(
                    session, kind=kind, slug=slug, name=name, sort_order=sort_order
                )
                attribute_ids.append(attr.id)

        root = (
            await session.execute(select(Category).where(Category.slug == "skincare"))
        ).scalar_one_or_none()
        if root is None:
            root = Category(
                slug="skincare",
                name="Skincare",
                description="Skincare categories for the storefront.",
                sort_order=0,
                is_active=True,
            )
            session.add(root)
            await session.flush()

        leaf_ids: list[UUID] = []
        for slug, name, sort_order, description in DEFAULT_LEAF_CATEGORIES:
            existing = (
                await session.execute(select(Category).where(Category.slug == slug))
            ).scalar_one_or_none()
            if existing is None:
                existing = Category(
                    parent_id=root.id,
                    slug=slug,
                    name=name,
                    description=description,
                    sort_order=sort_order,
                    is_active=True,
                )
                session.add(existing)
                await session.flush()
            leaf_ids.append(existing.id)

        for category_id in leaf_ids:
            for attribute_id in attribute_ids:
                link = (
                    await session.execute(
                        select(CategoryAttribute).where(
                            CategoryAttribute.category_id == category_id,
                            CategoryAttribute.attribute_id == attribute_id,
                        )
                    )
                ).scalar_one_or_none()
                if link is None:
                    session.add(
                        CategoryAttribute(
                            category_id=category_id,
                            attribute_id=attribute_id,
                        )
                    )

        await session.commit()
        print(
            f"catalog ready: root=skincare leaves={len(DEFAULT_LEAF_CATEGORIES)} "
            f"attributes={len(attribute_ids)}"
        )


if __name__ == "__main__":
    asyncio.run(seed())
