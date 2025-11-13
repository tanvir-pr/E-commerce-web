"""CheckoutService verified contact, empty cart, and stock soft-check."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.cart.schemas import CartItemOut, CartOut
from app.checkout.schemas import CheckoutQuoteIn
from app.checkout.service import CheckoutService
from app.problems import PROBLEM_CONTACT_UNVERIFIED, PROBLEM_VALIDATION, ProblemError
from app.shipping.schemas import ShippingQuoteOut


class FakeUsers:
    def __init__(self, user: SimpleNamespace | None) -> None:
        self.user = user

    async def get_by_id(self, _user_id: object) -> SimpleNamespace | None:
        return self.user


class FakeAddresses:
    def __init__(self, address: SimpleNamespace) -> None:
        self.address = address

    async def get_owned(self, _user_id: object, _address_id: object) -> SimpleNamespace:
        return self.address


class FakeCarts:
    def __init__(self, cart: CartOut) -> None:
        self.cart = cart

    async def get_cart(self, **_kwargs: object) -> tuple[CartOut, None]:
        return self.cart, None


class FakeShipping:
    async def quote(self, _body: object) -> ShippingQuoteOut:
        return ShippingQuoteOut(
            zone_id=uuid4(),
            zone_slug="dhaka-metro",
            zone_name="Dhaka metro",
            total_weight_grams=100,
            charge_poisha=6000,
            free_shipping_applied=False,
            free_shipping_threshold_poisha=250000,
            matched_by="district",
        )


def _cart(*, qty: int = 1, available: int | None = 5) -> CartOut:
    variant_id = uuid4()
    product_id = uuid4()
    return CartOut(
        id=uuid4(),
        status="active",
        item_count=qty,
        subtotal_poisha=145000 * qty,
        is_guest=False,
        updated_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
        items=[
            CartItemOut(
                id=uuid4(),
                variant_id=variant_id,
                product_id=product_id,
                product_slug="daily-barrier-serum",
                product_name="Daily Barrier Serum",
                size_label="30 ml",
                shade_name=None,
                spf=None,
                sku="SER-BAR-30",
                qty=qty,
                unit_price_poisha=145000,
                line_total_poisha=145000 * qty,
                routine_step="am",
                category_slug="serum",
                qty_available=available,
            )
        ],
    )


def _service(
    *,
    user: SimpleNamespace | None,
    cart: CartOut,
    address: SimpleNamespace | None = None,
) -> CheckoutService:
    service = CheckoutService(session=SimpleNamespace())  # type: ignore[arg-type]
    service.users = FakeUsers(user)  # type: ignore[assignment]
    service.carts = FakeCarts(cart)  # type: ignore[assignment]
    service.shipping = FakeShipping()  # type: ignore[assignment]
    service.addresses = FakeAddresses(
        address
        or SimpleNamespace(
            id=uuid4(),
            label="Home",
            line1="12 Road",
            line2=None,
            city="Dhaka",
            district="Dhaka",
            postal_code="1200",
            country="BD",
            phone=None,
            is_default=True,
        )
    )  # type: ignore[assignment]
    return service


@pytest.mark.asyncio
async def test_quote_requires_verified_contact() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        deleted_at=None,
        email_verified_at=None,
        phone_verified_at=None,
    )
    service = _service(user=user, cart=_cart())
    with pytest.raises(ProblemError) as exc:
        await service.quote(
            CheckoutQuoteIn(address_id=uuid4()),
            user_id=user.id,
            guest_token=None,
        )
    assert exc.value.type_ == PROBLEM_CONTACT_UNVERIFIED


@pytest.mark.asyncio
async def test_quote_rejects_empty_cart() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        deleted_at=None,
        email_verified_at=datetime.now(UTC),
        phone_verified_at=None,
    )
    empty = CartOut(
        id=uuid4(),
        status="active",
        item_count=0,
        subtotal_poisha=0,
        is_guest=False,
        updated_at=datetime.now(UTC),
        last_activity_at=datetime.now(UTC),
        items=[],
    )
    service = _service(user=user, cart=empty)
    with pytest.raises(ProblemError) as exc:
        await service.quote(
            CheckoutQuoteIn(line1="12 Road", city="Dhaka", district="Dhaka"),
            user_id=user.id,
            guest_token=None,
        )
    assert exc.value.type_ == PROBLEM_VALIDATION


@pytest.mark.asyncio
async def test_quote_ready_when_stock_ok() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        deleted_at=None,
        email_verified_at=datetime.now(UTC),
        phone_verified_at=None,
    )
    service = _service(user=user, cart=_cart(qty=1, available=10))
    quote = await service.quote(
        CheckoutQuoteIn(line1="12 Road", city="Dhaka", district="Dhaka"),
        user_id=user.id,
        guest_token=None,
    )
    assert quote.ready is True
    assert quote.total_poisha == 145000 + 6000
    assert quote.place_order_available is True
    assert quote.contact.ok is True


@pytest.mark.asyncio
async def test_quote_not_ready_when_stock_short() -> None:
    user = SimpleNamespace(
        id=uuid4(),
        deleted_at=None,
        email_verified_at=None,
        phone_verified_at=datetime.now(UTC),
    )
    service = _service(user=user, cart=_cart(qty=5, available=2))
    quote = await service.quote(
        CheckoutQuoteIn(line1="12 Road", city="Dhaka", district="Dhaka"),
        user_id=user.id,
        guest_token=None,
    )
    assert quote.ready is False
    assert "stock" in quote.blockers
    assert quote.stock[0].ok is False
