"""Cart persistence."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.models.cart import Cart, CartItem
from app.models.catalog import Category
from app.models.inventory import StockBatch
from app.models.product import Product, ProductVariant
from app.problems import PROBLEM_CONFLICT, PROBLEM_NOT_FOUND, ProblemError


class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _cart_options(self) -> Sequence[ExecutableOption]:
        return (
            selectinload(Cart.items)
            .selectinload(CartItem.variant)
            .selectinload(ProductVariant.product)
            .selectinload(Product.category),
            selectinload(Cart.user),
        )

    async def get_active_for_user(self, user_id: UUID) -> Cart | None:
        result = await self.session.execute(
            select(Cart)
            .options(*self._cart_options())
            .where(Cart.user_id == user_id, Cart.status == "active")
            .order_by(Cart.last_activity_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_guest_token(self, token: str) -> Cart | None:
        result = await self.session.execute(
            select(Cart)
            .options(*self._cart_options())
            .where(Cart.guest_token == token, Cart.status == "active")
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, cart_id: UUID) -> Cart | None:
        result = await self.session.execute(
            select(Cart)
            .options(*self._cart_options())
            .where(Cart.id == cart_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def require(self, cart_id: UUID) -> Cart:
        row = await self.get_by_id(cart_id)
        if row is None:
            raise ProblemError(404, "Not found", "Cart not found.", PROBLEM_NOT_FOUND)
        return row

    async def add_cart(self, cart: Cart) -> Cart:
        self.session.add(cart)
        await self.session.flush()
        return await self.require(cart.id)

    async def save(self, cart: Cart) -> Cart:
        await self.session.flush()
        return await self.require(cart.id)

    async def touch(self, cart: Cart) -> None:
        cart.last_activity_at = datetime.now(UTC)
        cart.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def get_item(self, cart_id: UUID, item_id: UUID) -> CartItem | None:
        result = await self.session.execute(
            select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart_id)
        )
        return result.scalar_one_or_none()

    async def require_item(self, cart_id: UUID, item_id: UUID) -> CartItem:
        row = await self.get_item(cart_id, item_id)
        if row is None:
            raise ProblemError(404, "Not found", "Cart item not found.", PROBLEM_NOT_FOUND)
        return row

    async def add_item(self, item: CartItem) -> CartItem:
        self.session.add(item)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProblemError(
                409,
                "Conflict",
                "That variant is already in the cart.",
                PROBLEM_CONFLICT,
            ) from exc
        return item

    async def delete_item(self, item: CartItem) -> None:
        await self.session.delete(item)
        await self.session.flush()

    async def clear_items(self, cart_id: UUID) -> None:
        await self.session.execute(delete(CartItem).where(CartItem.cart_id == cart_id))
        await self.session.flush()

    async def require_sellable_variant(self, variant_id: UUID) -> ProductVariant:
        result = await self.session.execute(
            select(ProductVariant)
            .options(
                selectinload(ProductVariant.product).selectinload(Product.category),
                selectinload(ProductVariant.product).selectinload(Product.attributes),
            )
            .where(ProductVariant.id == variant_id)
        )
        row = result.scalar_one_or_none()
        if row is None or not row.is_active:
            raise ProblemError(404, "Not found", "Variant not found.", PROBLEM_NOT_FOUND)
        product = row.product
        if product is None or product.deleted_at is not None or product.status != "published":
            raise ProblemError(404, "Not found", "Product not found.", PROBLEM_NOT_FOUND)
        return row

    async def qty_on_hand(self, variant_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(StockBatch.qty_on_hand), 0)).where(
                StockBatch.variant_id == variant_id
            )
        )
        return int(result.scalar_one())

    async def list_admin(
        self,
        *,
        status: str,
        abandon_cutoff: datetime,
        limit: int = 100,
    ) -> list[Cart]:
        stmt = select(Cart).options(*self._cart_options()).order_by(Cart.last_activity_at.desc())
        if status == "cleared":
            stmt = stmt.where(Cart.status == "cleared")
        elif status == "abandoned":
            stmt = stmt.where(
                Cart.status.in_(("active", "abandoned")),
                Cart.last_activity_at < abandon_cutoff,
            )
        elif status == "active":
            stmt = stmt.where(
                Cart.status == "active",
                Cart.last_activity_at >= abandon_cutoff,
            )
        elif status != "all":
            stmt = stmt.where(Cart.status == status)
        stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def list_stale_active(self, cutoff: datetime) -> list[Cart]:
        result = await self.session.execute(
            select(Cart).where(Cart.status == "active", Cart.last_activity_at < cutoff)
        )
        return list(result.scalars().all())

    async def products_for_category_slug(self, slug: str, *, limit: int = 3) -> list[Product]:
        result = await self.session.execute(
            select(Product)
            .join(Category, Product.category_id == Category.id)
            .options(selectinload(Product.variants), selectinload(Product.category))
            .where(
                Product.status == "published",
                Product.deleted_at.is_(None),
                Category.slug == slug,
                Category.deleted_at.is_(None),
            )
            .order_by(Product.name.asc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())
