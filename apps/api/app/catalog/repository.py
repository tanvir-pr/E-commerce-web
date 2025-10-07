"""Category and attribute persistence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Attribute, Category, CategoryAttribute
from app.problems import PROBLEM_CONFLICT, PROBLEM_NOT_FOUND, ProblemError


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories(self, *, include_inactive: bool = False) -> list[Category]:
        stmt = (
            select(Category)
            .options(selectinload(Category.attributes))
            .where(Category.deleted_at.is_(None))
            .order_by(Category.sort_order.asc(), Category.name.asc())
        )
        if not include_inactive:
            stmt = stmt.where(Category.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_category_by_slug(
        self, slug: str, *, include_inactive: bool = False
    ) -> Category | None:
        stmt = (
            select(Category)
            .options(selectinload(Category.attributes))
            .where(Category.slug == slug, Category.deleted_at.is_(None))
        )
        if not include_inactive:
            stmt = stmt.where(Category.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_category_by_id(self, category_id: UUID) -> Category | None:
        result = await self.session.execute(
            select(Category)
            .options(selectinload(Category.attributes))
            .where(Category.id == category_id, Category.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def require_category(self, category_id: UUID) -> Category:
        row = await self.get_category_by_id(category_id)
        if row is None:
            raise ProblemError(404, "Not found", "Category not found.", PROBLEM_NOT_FOUND)
        return row

    async def add_category(self, category: Category) -> Category:
        self.session.add(category)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A category with that slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return await self.require_category(category.id)

    async def save_category(self, category: Category) -> Category:
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A category with that slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return await self.require_category(category.id)

    async def soft_delete_category(self, category: Category) -> None:
        category.deleted_at = datetime.now(UTC)
        category.is_active = False
        await self.session.flush()

    async def replace_category_attributes(
        self, category: Category, attribute_ids: list[UUID]
    ) -> Category:
        await self.session.execute(
            delete(CategoryAttribute).where(CategoryAttribute.category_id == category.id)
        )
        for attribute_id in attribute_ids:
            attr = await self.get_attribute_by_id(attribute_id)
            if attr is None:
                raise ProblemError(
                    404,
                    "Not found",
                    f"Attribute {attribute_id} not found.",
                    PROBLEM_NOT_FOUND,
                )
            self.session.add(
                CategoryAttribute(category_id=category.id, attribute_id=attribute_id)
            )
        await self.session.flush()
        return await self.require_category(category.id)

    async def list_attributes(
        self, *, kind: str | None = None, include_inactive: bool = False
    ) -> list[Attribute]:
        stmt = select(Attribute).order_by(
            Attribute.kind.asc(), Attribute.sort_order.asc(), Attribute.name.asc()
        )
        if kind is not None:
            stmt = stmt.where(Attribute.kind == kind)
        if not include_inactive:
            stmt = stmt.where(Attribute.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_attribute_by_id(self, attribute_id: UUID) -> Attribute | None:
        result = await self.session.execute(
            select(Attribute).where(Attribute.id == attribute_id)
        )
        return result.scalar_one_or_none()

    async def get_attribute_by_kind_slug(self, kind: str, slug: str) -> Attribute | None:
        result = await self.session.execute(
            select(Attribute).where(Attribute.kind == kind, Attribute.slug == slug)
        )
        return result.scalar_one_or_none()

    async def require_attribute(self, attribute_id: UUID) -> Attribute:
        row = await self.get_attribute_by_id(attribute_id)
        if row is None:
            raise ProblemError(404, "Not found", "Attribute not found.", PROBLEM_NOT_FOUND)
        return row

    async def add_attribute(self, attribute: Attribute) -> Attribute:
        self.session.add(attribute)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "An attribute with that kind and slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return attribute

    async def save_attribute(self, attribute: Attribute) -> Attribute:
        await self.session.flush()
        return attribute
