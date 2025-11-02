"""CartService merge and upsell with in-memory fakes."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.cart.schemas import CartItemIn
from app.cart.service import CartService
from app.problems import ProblemError


class FakeSession:
    async def flush(self) -> None:
        return None

    async def delete(self, _obj: object) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeRepo:
    def __init__(self) -> None:
        self.carts: dict[UUID, SimpleNamespace] = {}
        self.items: dict[UUID, SimpleNamespace] = {}
        self.variants: dict[UUID, SimpleNamespace] = {}
        self.stock: dict[UUID, int] = {}
        self.category_products: dict[str, list[SimpleNamespace]] = {}

    async def get_active_for_user(self, user_id: UUID) -> SimpleNamespace | None:
        for cart in self.carts.values():
            if cart.user_id == user_id and cart.status == "active":
                return await self.get_by_id(cart.id)
        return None

    async def get_by_guest_token(self, token: str) -> SimpleNamespace | None:
        for cart in self.carts.values():
            if cart.guest_token == token and cart.status == "active":
                return await self.get_by_id(cart.id)
        return None

    async def get_by_id(self, cart_id: UUID) -> SimpleNamespace | None:
        row = self.carts.get(cart_id)
        if row is None:
            return None
        row.items = [item for item in self.items.values() if item.cart_id == cart_id]
        return row

    async def require(self, cart_id: UUID) -> SimpleNamespace:
        row = await self.get_by_id(cart_id)
        if row is None:
            raise ProblemError(404, "Not found", "Cart not found.", "x")
        return row

    async def add_cart(self, cart: object) -> SimpleNamespace:
        cart_id = getattr(cart, "id", None) or uuid4()
        row = SimpleNamespace(
            id=cart_id,
            user_id=getattr(cart, "user_id", None),
            guest_token=getattr(cart, "guest_token", None),
            status=getattr(cart, "status", "active"),
            items=[],
            user=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
            abandoned_at=None,
            cleared_at=None,
        )
        self.carts[row.id] = row
        return row

    async def save(self, cart: SimpleNamespace) -> SimpleNamespace:
        return cart

    async def touch(self, cart: SimpleNamespace) -> None:
        cart.last_activity_at = datetime.now(UTC)

    async def get_item(self, cart_id: UUID, item_id: UUID) -> SimpleNamespace | None:
        item = self.items.get(item_id)
        if item is None or item.cart_id != cart_id:
            return None
        return item

    async def require_item(self, cart_id: UUID, item_id: UUID) -> SimpleNamespace:
        item = await self.get_item(cart_id, item_id)
        if item is None:
            raise ProblemError(404, "Not found", "Cart item not found.", "x")
        return item

    async def add_item(self, item: object) -> SimpleNamespace:
        item_id = getattr(item, "id", None) or uuid4()
        row = SimpleNamespace(
            id=item_id,
            cart_id=item.cart_id,
            variant_id=item.variant_id,
            qty=int(item.qty),
            unit_price_poisha=int(item.unit_price_poisha),
            variant=self.variants[item.variant_id],
        )
        self.items[row.id] = row
        self.carts[row.cart_id].items.append(row)
        return row

    async def delete_item(self, item: SimpleNamespace) -> None:
        self.items.pop(item.id, None)
        cart = self.carts[item.cart_id]
        cart.items = [row for row in cart.items if row.id != item.id]

    async def clear_items(self, cart_id: UUID) -> None:
        cart = self.carts[cart_id]
        for item in list(cart.items):
            self.items.pop(item.id, None)
        cart.items = []

    async def require_sellable_variant(self, variant_id: UUID) -> SimpleNamespace:
        row = self.variants.get(variant_id)
        if row is None:
            raise ProblemError(404, "Not found", "Variant not found.", "x")
        return row

    async def qty_on_hand(self, variant_id: UUID) -> int:
        return self.stock.get(variant_id, 0)

    async def products_for_category_slug(
        self, slug: str, *, limit: int = 3
    ) -> list[SimpleNamespace]:
        return self.category_products.get(slug, [])[:limit]


def _service() -> tuple[CartService, FakeRepo]:
    service = CartService(FakeSession())  # type: ignore[arg-type]
    repo = FakeRepo()
    service.repo = repo  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    return service, repo


def _variant(product_slug: str, category_slug: str, price: int = 1000) -> SimpleNamespace:
    product_id = uuid4()
    variant_id = uuid4()
    product = SimpleNamespace(
        id=product_id,
        slug=product_slug,
        name=product_slug,
        subtitle=None,
        routine_step="am",
        category=SimpleNamespace(slug=category_slug),
        variants=[],
    )
    variant = SimpleNamespace(
        id=variant_id,
        product_id=product_id,
        product=product,
        sku=f"SKU-{product_slug}",
        size_label="30 ml",
        shade_name=None,
        spf=None,
        price_poisha=price,
        is_active=True,
    )
    product.variants = [variant]
    return variant


@pytest.mark.asyncio
async def test_guest_add_and_merge_into_user() -> None:
    service, repo = _service()
    variant = _variant("serum-one", "serum", 145000)
    repo.variants[variant.id] = variant

    guest_out, token = await service.add_item(
        CartItemIn(variant_id=variant.id, qty=1),
        user_id=None,
        guest_token=None,
    )
    assert token is not None
    assert guest_out.item_count == 1
    assert guest_out.is_guest is True

    user_id = uuid4()
    merged, new_token = await service.get_cart(user_id=user_id, guest_token=token)
    assert new_token is None
    assert merged.is_guest is False
    assert merged.item_count == 1
    assert merged.subtotal_poisha == 145000


@pytest.mark.asyncio
async def test_upsell_missing_routine_steps() -> None:
    service, repo = _service()
    serum = _variant("daily-serum", "serum")
    repo.variants[serum.id] = serum
    moisturizer = SimpleNamespace(
        id=uuid4(),
        slug="day-cream",
        name="Day Cream",
        subtitle=None,
        category=SimpleNamespace(slug="moisturizer"),
        variants=[SimpleNamespace(is_active=True, price_poisha=99000)],
    )
    repo.category_products["moisturizer"] = [moisturizer]
    repo.category_products["cleanser"] = []
    repo.category_products["toner"] = []
    repo.category_products["sunscreen"] = []

    await service.add_item(
        CartItemIn(variant_id=serum.id, qty=1),
        user_id=uuid4(),
        guest_token=None,
    )
    upsell = await service.upsell(user_id=list(repo.carts.values())[0].user_id, guest_token=None)
    assert "moisturizer" in upsell.missing_steps
    assert any(item.slug == "day-cream" for item in upsell.items)
