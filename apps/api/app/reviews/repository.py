"""Review and wishlist persistence."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.review import ProductReview, WishlistItem
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_review(self, row: ProductReview) -> ProductReview:
        self.session.add(row)
        await self.session.flush()
        return row

    async def save_review(self, row: ProductReview) -> ProductReview:
        await self.session.flush()
        return row

    async def get_review(self, review_id: UUID) -> ProductReview | None:
        result = await self.session.execute(
            select(ProductReview).where(ProductReview.id == review_id)
        )
        return result.scalar_one_or_none()

    async def require_review(self, review_id: UUID) -> ProductReview:
        row = await self.get_review(review_id)
        if row is None:
            raise ProblemError(404, "Not found", "Review not found.", PROBLEM_NOT_FOUND)
        return row

    async def get_user_review(
        self, *, user_id: UUID, product_id: UUID
    ) -> ProductReview | None:
        result = await self.session.execute(
            select(ProductReview).where(
                ProductReview.user_id == user_id,
                ProductReview.product_id == product_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_published_for_product(self, product_id: UUID) -> list[ProductReview]:
        result = await self.session.execute(
            select(ProductReview)
            .where(
                ProductReview.product_id == product_id,
                ProductReview.is_published.is_(True),
            )
            .order_by(ProductReview.created_at.desc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def list_admin(self, *, published: bool | None = None) -> list[ProductReview]:
        stmt = select(ProductReview).order_by(ProductReview.created_at.desc()).limit(200)
        if published is not None:
            stmt = stmt.where(ProductReview.is_published.is_(published))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def rating_stats(self, product_id: UUID) -> tuple[float | None, int]:
        result = await self.session.execute(
            select(
                func.avg(ProductReview.rating),
                func.count(ProductReview.id),
            ).where(
                ProductReview.product_id == product_id,
                ProductReview.is_published.is_(True),
            )
        )
        avg, count = result.one()
        if not count:
            return None, 0
        return float(avg), int(count)

    async def delivered_order_for_product(
        self, *, user_id: UUID, product_id: UUID
    ) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == user_id,
                Order.status == "delivered",
                OrderItem.product_id == product_id,
            )
            .order_by(Order.delivered_at.desc().nullslast(), Order.placed_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_product_by_slug(self, slug: str) -> Product | None:
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_product(self, product_id: UUID) -> Product | None:
        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.id == product_id)
        )
        return result.scalar_one_or_none()

    async def require_published_product(self, product_id: UUID) -> Product:
        row = await self.get_product(product_id)
        if row is None or row.status != "published":
            raise ProblemError(404, "Not found", "Product not found.", PROBLEM_NOT_FOUND)
        return row

    async def add_wishlist(self, row: WishlistItem) -> WishlistItem:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_wishlist_item(
        self, *, user_id: UUID, product_id: UUID
    ) -> WishlistItem | None:
        result = await self.session.execute(
            select(WishlistItem).where(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_wishlist(self, user_id: UUID) -> list[tuple[WishlistItem, Product]]:
        result = await self.session.execute(
            select(WishlistItem, Product)
            .join(Product, Product.id == WishlistItem.product_id)
            .options(selectinload(Product.variants))
            .where(WishlistItem.user_id == user_id)
            .order_by(WishlistItem.created_at.desc())
            .limit(200)
        )
        return list(result.all())

    async def delete_wishlist(self, row: WishlistItem) -> None:
        await self.session.delete(row)
        await self.session.flush()

    async def user_display_names(self, user_ids: list[UUID]) -> dict[UUID, str | None]:
        if not user_ids:
            return {}
        from app.models.user import User

        result = await self.session.execute(
            select(User.id, User.display_name, User.email).where(User.id.in_(user_ids))
        )
        out: dict[UUID, str | None] = {}
        for uid, display_name, email in result.all():
            if display_name:
                out[uid] = display_name
            elif email:
                local = str(email).split("@", 1)[0]
                out[uid] = local[:1] + "***" if local else "Shopper"
            else:
                out[uid] = "Shopper"
        return out

    async def product_labels(
        self, product_ids: list[UUID]
    ) -> dict[UUID, tuple[str, str]]:
        if not product_ids:
            return {}
        result = await self.session.execute(
            select(Product.id, Product.slug, Product.name).where(
                Product.id.in_(product_ids)
            )
        )
        return {row[0]: (row[1], row[2]) for row in result.all()}
