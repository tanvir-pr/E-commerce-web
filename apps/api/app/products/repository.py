"""Product and variant persistence."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.models.catalog import Attribute
from app.models.product import Product, ProductAttribute, ProductVariant
from app.problems import PROBLEM_CONFLICT, PROBLEM_NOT_FOUND, ProblemError
from app.products.constants import PUBLIC_LIST_STATUS


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _detail_options(self) -> Sequence[ExecutableOption]:
        return (
            selectinload(Product.variants),
            selectinload(Product.attributes),
            selectinload(Product.category),
        )

    async def list_products(
        self,
        *,
        category_id: UUID | None = None,
        status: str | None = None,
        attribute_id: UUID | None = None,
        include_deleted: bool = False,
        public_only: bool = False,
    ) -> list[Product]:
        stmt = (
            select(Product)
            .options(*self._detail_options())
            .order_by(Product.name.asc())
        )
        if not include_deleted:
            stmt = stmt.where(Product.deleted_at.is_(None))
        if public_only:
            stmt = stmt.where(Product.status == PUBLIC_LIST_STATUS)
        elif status is not None:
            stmt = stmt.where(Product.status == status)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if attribute_id is not None:
            stmt = stmt.join(ProductAttribute).where(
                ProductAttribute.attribute_id == attribute_id
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_slug(
        self, slug: str, *, public_only: bool = False
    ) -> Product | None:
        stmt = (
            select(Product)
            .options(*self._detail_options())
            .where(Product.slug == slug, Product.deleted_at.is_(None))
        )
        if public_only:
            stmt = stmt.where(Product.status == PUBLIC_LIST_STATUS)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, product_id: UUID) -> Product | None:
        result = await self.session.execute(
            select(Product)
            .options(*self._detail_options())
            .where(Product.id == product_id, Product.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def require(self, product_id: UUID) -> Product:
        row = await self.get_by_id(product_id)
        if row is None:
            raise ProblemError(404, "Not found", "Product not found.", PROBLEM_NOT_FOUND)
        return row

    async def add(self, product: Product) -> Product:
        self.session.add(product)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A product with that slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return await self.require(product.id)

    async def save(self, product: Product) -> Product:
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A product with that slug already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return await self.require(product.id)

    async def soft_delete(self, product: Product) -> None:
        product.deleted_at = datetime.now(UTC)
        if product.status == "published":
            product.status = "archived"
        await self.session.flush()

    async def replace_attributes(
        self, product: Product, attribute_ids: list[UUID]
    ) -> Product:
        await self.session.execute(
            delete(ProductAttribute).where(ProductAttribute.product_id == product.id)
        )
        for attribute_id in attribute_ids:
            attr = await self.session.get(Attribute, attribute_id)
            if attr is None:
                raise ProblemError(
                    404,
                    "Not found",
                    f"Attribute {attribute_id} not found.",
                    PROBLEM_NOT_FOUND,
                )
            self.session.add(
                ProductAttribute(product_id=product.id, attribute_id=attribute_id)
            )
        await self.session.flush()
        return await self.require(product.id)

    async def add_variant(self, variant: ProductVariant) -> ProductVariant:
        self.session.add(variant)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A variant with that SKU already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return variant

    async def get_variant(self, variant_id: UUID) -> ProductVariant | None:
        result = await self.session.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        return result.scalar_one_or_none()

    async def require_variant(self, variant_id: UUID) -> ProductVariant:
        row = await self.get_variant(variant_id)
        if row is None:
            raise ProblemError(404, "Not found", "Variant not found.", PROBLEM_NOT_FOUND)
        return row

    async def save_variant(self, variant: ProductVariant) -> ProductVariant:
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "A variant with that SKU already exists.",
                PROBLEM_CONFLICT,
            ) from exc
        return variant

    async def delete_variant(self, variant: ProductVariant) -> None:
        await self.session.delete(variant)
        await self.session.flush()
