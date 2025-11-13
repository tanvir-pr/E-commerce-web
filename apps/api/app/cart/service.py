"""Cart use cases: guest/user carts, merge, routine upsell, admin clear."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.cart.constants import ADMIN_LIST_FILTERS, ROUTINE_CATEGORY_SLUGS
from app.cart.repository import CartRepository
from app.cart.schemas import (
    AdminCartDetailOut,
    AdminCartListOut,
    AdminCartSummaryOut,
    CartItemIn,
    CartItemOut,
    CartItemPatchIn,
    CartOut,
    UpsellOut,
    UpsellProductOut,
)
from app.config import Settings, get_settings
from app.models.cart import Cart, CartItem
from app.problems import PROBLEM_VALIDATION, ProblemError


class CartService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = CartRepository(session)
        self.audit = AuditService(session)

    def abandon_cutoff(self) -> datetime:
        return datetime.now(UTC) - timedelta(hours=self.settings.cart_abandon_after_hours)

    async def resolve_cart(
        self,
        *,
        user_id: UUID | None,
        guest_token: str | None,
    ) -> tuple[Cart, str | None]:
        """Return cart and optional new guest token to set on the response."""
        guest_cart = None
        if guest_token:
            guest_cart = await self.repo.get_by_guest_token(guest_token)

        if user_id is not None:
            user_cart = await self.repo.get_active_for_user(user_id)
            if user_cart is None:
                user_cart = await self.repo.add_cart(
                    Cart(user_id=user_id, status="active")
                )
            if guest_cart is not None and guest_cart.id != user_cart.id:
                await self._merge_into(user_cart, guest_cart)
                user_cart = await self.repo.require(user_cart.id)
            return user_cart, None

        if guest_cart is not None:
            return guest_cart, None

        token = secrets.token_urlsafe(24)
        cart = await self.repo.add_cart(Cart(guest_token=token, status="active"))
        return cart, token

    async def get_cart(
        self, *, user_id: UUID | None, guest_token: str | None
    ) -> tuple[CartOut, str | None]:
        cart, new_token = await self.resolve_cart(user_id=user_id, guest_token=guest_token)
        await self._reprice(cart)
        cart = await self.repo.require(cart.id)
        return await self._cart_out(cart), new_token

    async def add_item(
        self,
        body: CartItemIn,
        *,
        user_id: UUID | None,
        guest_token: str | None,
    ) -> tuple[CartOut, str | None]:
        cart, new_token = await self.resolve_cart(user_id=user_id, guest_token=guest_token)
        variant = await self.repo.require_sellable_variant(body.variant_id)
        self._validate_qty(body.qty)
        available = await self.repo.qty_on_hand(variant.id)
        existing = next((i for i in cart.items if i.variant_id == variant.id), None)
        new_qty = body.qty + (existing.qty if existing else 0)
        if available > 0 and new_qty > available:
            raise ProblemError(
                422,
                "Validation error",
                f"Only {available} in stock for this variant.",
                PROBLEM_VALIDATION,
            )
        if existing:
            existing.qty = new_qty
            existing.unit_price_poisha = variant.price_poisha
        else:
            await self.repo.add_item(
                CartItem(
                    cart_id=cart.id,
                    variant_id=variant.id,
                    qty=body.qty,
                    unit_price_poisha=variant.price_poisha,
                )
            )
        await self.repo.touch(cart)
        cart = await self.repo.require(cart.id)
        return await self._cart_out(cart), new_token

    async def patch_item(
        self,
        item_id: UUID,
        body: CartItemPatchIn,
        *,
        user_id: UUID | None,
        guest_token: str | None,
    ) -> tuple[CartOut, str | None]:
        cart, new_token = await self.resolve_cart(user_id=user_id, guest_token=guest_token)
        item = await self.repo.require_item(cart.id, item_id)
        if body.qty == 0:
            await self.repo.delete_item(item)
        else:
            self._validate_qty(body.qty)
            available = await self.repo.qty_on_hand(item.variant_id)
            if available > 0 and body.qty > available:
                raise ProblemError(
                    422,
                    "Validation error",
                    f"Only {available} in stock for this variant.",
                    PROBLEM_VALIDATION,
                )
            item.qty = body.qty
        await self.repo.touch(cart)
        cart = await self.repo.require(cart.id)
        await self._reprice(cart)
        cart = await self.repo.require(cart.id)
        return await self._cart_out(cart), new_token

    async def remove_item(
        self,
        item_id: UUID,
        *,
        user_id: UUID | None,
        guest_token: str | None,
    ) -> tuple[CartOut, str | None]:
        cart, new_token = await self.resolve_cart(user_id=user_id, guest_token=guest_token)
        item = await self.repo.require_item(cart.id, item_id)
        await self.repo.delete_item(item)
        await self.repo.touch(cart)
        cart = await self.repo.require(cart.id)
        return await self._cart_out(cart), new_token

    async def clear_own(
        self, *, user_id: UUID | None, guest_token: str | None
    ) -> tuple[CartOut, str | None]:
        cart, new_token = await self.resolve_cart(user_id=user_id, guest_token=guest_token)
        await self.repo.clear_items(cart.id)
        await self.repo.touch(cart)
        cart = await self.repo.require(cart.id)
        return await self._cart_out(cart), new_token

    async def mark_converted(self, cart_id: UUID) -> None:
        """Clear lines and mark the cart converted after a successful place-order."""
        cart = await self.repo.require(cart_id)
        await self.repo.clear_items(cart.id)
        cart.status = "converted"
        cart.cleared_at = datetime.now(UTC)
        await self.repo.touch(cart)

    async def upsell(
        self, *, user_id: UUID | None, guest_token: str | None
    ) -> UpsellOut:
        cart, _ = await self.resolve_cart(user_id=user_id, guest_token=guest_token)
        present: set[str] = set()
        for item in cart.items:
            variant = item.variant
            product = variant.product if variant else None
            slug = product.category.slug if product and product.category else None
            if slug:
                present.add(slug)
        missing = [step for step in ROUTINE_CATEGORY_SLUGS if step not in present]
        suggestions: list[UpsellProductOut] = []
        cart_product_ids = {
            item.variant.product_id
            for item in cart.items
            if item.variant is not None
        }
        for step in missing:
            for product in await self.repo.products_for_category_slug(step, limit=2):
                if product.id in cart_product_ids:
                    continue
                prices = [
                    v.price_poisha for v in product.variants if v.is_active
                ] or [v.price_poisha for v in product.variants]
                suggestions.append(
                    UpsellProductOut(
                        product_id=product.id,
                        slug=product.slug,
                        name=product.name,
                        subtitle=product.subtitle,
                        category_slug=step,
                        from_price_poisha=min(prices) if prices else None,
                        reason=f"Complete your routine — add a {step}",
                    )
                )
                break
        return UpsellOut(items=suggestions, missing_steps=missing)

    async def admin_list(self, *, status: str = "all") -> AdminCartListOut:
        if status not in ADMIN_LIST_FILTERS:
            raise ProblemError(
                422,
                "Validation error",
                f"status must be one of: {', '.join(sorted(ADMIN_LIST_FILTERS))}",
                PROBLEM_VALIDATION,
            )
        cutoff = self.abandon_cutoff()
        rows = await self.repo.list_admin(status=status, abandon_cutoff=cutoff)
        items = [await self._admin_summary(row, cutoff) for row in rows]
        # Hide empty active carts from abandoned view noise optionally — keep all for staff
        if status == "abandoned":
            items = [row for row in items if row.item_count > 0]
        return AdminCartListOut(
            items=items,
            abandon_after_hours=self.settings.cart_abandon_after_hours,
        )

    async def admin_get(self, cart_id: UUID) -> AdminCartDetailOut:
        cart = await self.repo.require(cart_id)
        cutoff = self.abandon_cutoff()
        summary = await self._admin_summary(cart, cutoff)
        return AdminCartDetailOut(
            **summary.model_dump(),
            items=await self._item_outs(cart),
        )

    async def admin_clear(self, cart_id: UUID, *, actor_user_id: UUID) -> None:
        cart = await self.repo.require(cart_id)
        await self.repo.clear_items(cart.id)
        cart.status = "cleared"
        cart.cleared_at = datetime.now(UTC)
        await self.repo.touch(cart)
        await self.audit.record(
            action="cart.cleared",
            actor_user_id=actor_user_id,
            subject_type="cart",
            subject_id=str(cart_id),
        )

    async def mark_abandoned(self) -> int:
        cutoff = self.abandon_cutoff()
        rows = await self.repo.list_stale_active(cutoff)
        count = 0
        now = datetime.now(UTC)
        for cart in rows:
            if not cart.items:
                continue
            cart.status = "abandoned"
            cart.abandoned_at = now
            count += 1
        await self.session.flush()
        return count

    async def _merge_into(self, target: Cart, source: Cart) -> None:
        by_variant = {item.variant_id: item for item in target.items}
        for item in list(source.items):
            existing = by_variant.get(item.variant_id)
            if existing:
                existing.qty = min(
                    existing.qty + item.qty, self.settings.cart_max_line_qty
                )
                await self.repo.delete_item(item)
            else:
                item.cart_id = target.id
        source.status = "cleared"
        source.cleared_at = datetime.now(UTC)
        source.guest_token = None
        await self.repo.touch(target)
        await self.session.flush()

    async def _reprice(self, cart: Cart) -> None:
        for item in cart.items:
            if item.variant and item.variant.is_active:
                item.unit_price_poisha = item.variant.price_poisha
        await self.session.flush()

    def _validate_qty(self, qty: int) -> None:
        if qty < 1 or qty > self.settings.cart_max_line_qty:
            raise ProblemError(
                422,
                "Validation error",
                f"qty must be between 1 and {self.settings.cart_max_line_qty}.",
                PROBLEM_VALIDATION,
            )

    async def _cart_out(self, cart: Cart) -> CartOut:
        items = await self._item_outs(cart)
        return CartOut(
            id=cart.id,
            status=cart.status,
            item_count=sum(i.qty for i in items),
            subtotal_poisha=sum(i.line_total_poisha for i in items),
            is_guest=cart.user_id is None,
            updated_at=cart.updated_at,
            last_activity_at=cart.last_activity_at,
            items=items,
        )

    async def _item_outs(self, cart: Cart) -> list[CartItemOut]:
        outs: list[CartItemOut] = []
        for item in cart.items:
            variant = item.variant
            product = variant.product if variant else None
            if variant is None or product is None:
                continue
            available = await self.repo.qty_on_hand(variant.id)
            outs.append(
                CartItemOut(
                    id=item.id,
                    variant_id=variant.id,
                    product_id=product.id,
                    product_slug=product.slug,
                    product_name=product.name,
                    size_label=variant.size_label,
                    shade_name=variant.shade_name,
                    spf=variant.spf,
                    sku=variant.sku,
                    qty=item.qty,
                    unit_price_poisha=item.unit_price_poisha,
                    line_total_poisha=item.unit_price_poisha * item.qty,
                    routine_step=product.routine_step,
                    category_slug=product.category.slug if product.category else None,
                    qty_available=available,
                )
            )
        return outs

    async def _admin_summary(self, cart: Cart, cutoff: datetime) -> AdminCartSummaryOut:
        items = await self._item_outs(cart)
        effective = cart.status
        if (
            cart.status == "active"
            and cart.last_activity_at < cutoff
            and items
        ):
            effective = "abandoned"
        email = cart.user.email if cart.user else None
        return AdminCartSummaryOut(
            id=cart.id,
            status=effective,
            user_id=cart.user_id,
            user_email=email,
            is_guest=cart.user_id is None,
            item_count=sum(i.qty for i in items),
            subtotal_poisha=sum(i.line_total_poisha for i in items),
            last_activity_at=cart.last_activity_at,
            created_at=cart.created_at,
            abandoned_at=cart.abandoned_at,
            cleared_at=cart.cleared_at,
        )
