"""Verified reviews and wishlist use cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.models.product import Product
from app.models.review import ProductReview, WishlistItem
from app.problems import (
    PROBLEM_FORBIDDEN,
    PROBLEM_NOT_FOUND,
    PROBLEM_VALIDATION,
    ProblemError,
)
from app.reviews.repository import ReviewRepository
from app.reviews.schemas import (
    ReviewIn,
    ReviewListOut,
    ReviewModerationIn,
    ReviewOut,
    WishlistAddIn,
    WishlistItemOut,
    WishlistOut,
)
from app.users.repository import UserRepository
from app.users.schemas import SKIN_TYPES


class ReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReviewRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)

    async def list_for_product(
        self, slug: str, *, user_id: UUID | None
    ) -> ReviewListOut:
        product = await self.repo.get_product_by_slug(slug)
        if product is None or product.status != "published":
            raise ProblemError(404, "Not found", "Product not found.", PROBLEM_NOT_FOUND)
        rows = await self.repo.list_published_for_product(product.id)
        avg, count = await self.repo.rating_stats(product.id)
        names = await self.repo.user_display_names([r.user_id for r in rows])
        can_review = False
        if user_id is not None:
            existing = await self.repo.get_user_review(
                user_id=user_id, product_id=product.id
            )
            if existing is None:
                order = await self.repo.delivered_order_for_product(
                    user_id=user_id, product_id=product.id
                )
                can_review = order is not None
        return ReviewListOut(
            items=[
                ReviewOut(
                    id=row.id,
                    product_id=row.product_id,
                    product_slug=product.slug,
                    product_name=product.name,
                    rating=row.rating,
                    title=row.title,
                    body=row.body,
                    skin_type=row.skin_type,
                    is_verified=row.is_verified,
                    is_published=row.is_published,
                    created_at=row.created_at,
                    author_display=names.get(row.user_id),
                )
                for row in rows
            ],
            rating_avg=round(avg, 2) if avg is not None else None,
            rating_count=count,
            can_review=can_review,
        )

    async def create_for_product(
        self, slug: str, body: ReviewIn, *, user_id: UUID
    ) -> ReviewOut:
        product = await self.repo.get_product_by_slug(slug)
        if product is None or product.status != "published":
            raise ProblemError(404, "Not found", "Product not found.", PROBLEM_NOT_FOUND)
        existing = await self.repo.get_user_review(
            user_id=user_id, product_id=product.id
        )
        if existing is not None:
            raise ProblemError(
                422,
                "Validation error",
                "You already reviewed this product.",
                PROBLEM_VALIDATION,
            )
        order = await self.repo.delivered_order_for_product(
            user_id=user_id, product_id=product.id
        )
        if order is None:
            raise ProblemError(
                403,
                "Forbidden",
                "Only verified purchasers can leave a review after delivery.",
                PROBLEM_FORBIDDEN,
            )
        skin = body.skin_type
        if skin is not None and skin != "" and skin not in SKIN_TYPES:
            raise ProblemError(
                422,
                "Validation error",
                f"skin_type must be one of: {', '.join(SKIN_TYPES)}",
                PROBLEM_VALIDATION,
            )
        user = await self.users.get_by_id(user_id)
        if not skin and user is not None:
            skin = user.skin_type
        row = ProductReview(
            product_id=product.id,
            user_id=user_id,
            order_id=order.id,
            rating=body.rating,
            title=(body.title.strip() if body.title else None) or None,
            body=body.body.strip(),
            skin_type=skin or None,
            is_verified=True,
            is_published=True,
        )
        await self.repo.add_review(row)
        await self.audit.record(
            action="review.created",
            actor_user_id=user_id,
            subject_type="product_review",
            subject_id=str(row.id),
            meta={"product_id": str(product.id), "rating": body.rating},
        )
        display = None
        if user is not None:
            display = user.display_name or (
                user.email.split("@", 1)[0][:1] + "***" if user.email else "Shopper"
            )
        return ReviewOut(
            id=row.id,
            product_id=row.product_id,
            product_slug=product.slug,
            product_name=product.name,
            rating=row.rating,
            title=row.title,
            body=row.body,
            skin_type=row.skin_type,
            is_verified=row.is_verified,
            is_published=row.is_published,
            created_at=row.created_at,
            author_display=display,
        )

    async def admin_list(self, *, published: bool | None = None) -> ReviewListOut:
        rows = await self.repo.list_admin(published=published)
        labels = await self.repo.product_labels([r.product_id for r in rows])
        names = await self.repo.user_display_names([r.user_id for r in rows])
        return ReviewListOut(
            items=[
                ReviewOut(
                    id=row.id,
                    product_id=row.product_id,
                    product_slug=labels.get(row.product_id, (None, None))[0],
                    product_name=labels.get(row.product_id, (None, None))[1],
                    rating=row.rating,
                    title=row.title,
                    body=row.body,
                    skin_type=row.skin_type,
                    is_verified=row.is_verified,
                    is_published=row.is_published,
                    created_at=row.created_at,
                    author_display=names.get(row.user_id),
                )
                for row in rows
            ],
            rating_count=len(rows),
        )

    async def moderate(
        self, review_id: UUID, body: ReviewModerationIn, *, actor_user_id: UUID
    ) -> ReviewOut:
        row = await self.repo.require_review(review_id)
        row.is_published = body.is_published
        await self.repo.save_review(row)
        await self.audit.record(
            action="review.moderated",
            actor_user_id=actor_user_id,
            subject_type="product_review",
            subject_id=str(row.id),
            meta={"is_published": body.is_published, "note": body.note},
        )
        labels = await self.repo.product_labels([row.product_id])
        names = await self.repo.user_display_names([row.user_id])
        slug, name = labels.get(row.product_id, (None, None))
        return ReviewOut(
            id=row.id,
            product_id=row.product_id,
            product_slug=slug,
            product_name=name,
            rating=row.rating,
            title=row.title,
            body=row.body,
            skin_type=row.skin_type,
            is_verified=row.is_verified,
            is_published=row.is_published,
            created_at=row.created_at,
            author_display=names.get(row.user_id),
        )

    async def rating_stats(self, product_id: UUID) -> tuple[float | None, int]:
        return await self.repo.rating_stats(product_id)

    async def list_wishlist(self, user_id: UUID) -> WishlistOut:
        rows = await self.repo.list_wishlist(user_id)
        items: list[WishlistItemOut] = []
        for item, product in rows:
            items.append(self._wishlist_item(item, product))
        return WishlistOut(items=items)

    async def add_wishlist(self, body: WishlistAddIn, *, user_id: UUID) -> WishlistItemOut:
        product = await self.repo.require_published_product(body.product_id)
        existing = await self.repo.get_wishlist_item(
            user_id=user_id, product_id=product.id
        )
        if existing is not None:
            return self._wishlist_item(existing, product)
        row = WishlistItem(user_id=user_id, product_id=product.id)
        await self.repo.add_wishlist(row)
        await self.audit.record(
            action="wishlist.added",
            actor_user_id=user_id,
            subject_type="wishlist_item",
            subject_id=str(row.id),
            meta={"product_id": str(product.id)},
        )
        return self._wishlist_item(row, product)

    async def remove_wishlist(self, product_id: UUID, *, user_id: UUID) -> None:
        row = await self.repo.get_wishlist_item(user_id=user_id, product_id=product_id)
        if row is None:
            return
        await self.repo.delete_wishlist(row)
        await self.audit.record(
            action="wishlist.removed",
            actor_user_id=user_id,
            subject_type="wishlist_item",
            subject_id=str(row.id),
            meta={"product_id": str(product_id)},
        )

    async def is_wishlisted(self, *, user_id: UUID, product_id: UUID) -> bool:
        row = await self.repo.get_wishlist_item(user_id=user_id, product_id=product_id)
        return row is not None

    def _wishlist_item(self, item: WishlistItem, product: Product) -> WishlistItemOut:
        active = [v for v in (product.variants or []) if v.is_active]
        prices = [v.price_poisha for v in active] or [
            v.price_poisha for v in (product.variants or [])
        ]
        return WishlistItemOut(
            id=item.id,
            product_id=product.id,
            product_slug=product.slug,
            product_name=product.name,
            subtitle=product.subtitle,
            from_price_poisha=min(prices) if prices else None,
            created_at=item.created_at,
        )
