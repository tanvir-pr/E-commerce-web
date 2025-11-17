"""COD auto-confirm on place (Part 19)."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.cart.schemas import CartItemOut, CartOut
from app.checkout.schemas import (
    CheckoutAddressSnapshotOut,
    CheckoutContactOut,
    CheckoutQuoteOut,
    CheckoutStockLineOut,
)
from app.orders.schemas import PlaceOrderIn
from app.orders.service import OrderService
from app.problems import ProblemError
from app.shipping.schemas import ShippingQuoteOut


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


class FakeInventory:
    def __init__(self) -> None:
        self.reserved = 0
        self.released = 0

    async def reserve_for_order(self, *_args: object, **_kwargs: object) -> int:
        self.reserved = 2
        return 2

    async def release_for_order(self, *_args: object, **_kwargs: object) -> int:
        self.released += 1
        return 1

    async def consume_for_order(self, *_args: object, **_kwargs: object) -> int:
        return 0


class FakeCarts:
    def __init__(self) -> None:
        self.converted: list[object] = []

    async def mark_converted(self, cart_id: object) -> None:
        self.converted.append(cart_id)


class FakeCheckout:
    def __init__(self, quote: CheckoutQuoteOut) -> None:
        self.quote_out = quote

    async def quote(self, *_args: object, **_kwargs: object) -> CheckoutQuoteOut:
        return self.quote_out


class FakeRepo:
    def __init__(self) -> None:
        self.order: SimpleNamespace | None = None
        self.items: list[SimpleNamespace] = []
        self.events: list[object] = []

    async def add(self, order: object) -> SimpleNamespace:
        row = SimpleNamespace(
            id=uuid4(),
            order_number=order.order_number,
            user_id=order.user_id,
            cart_id=getattr(order, "cart_id", None),
            status=order.status,
            currency=getattr(order, "currency", "BDT"),
            merchandise_subtotal_poisha=order.merchandise_subtotal_poisha,
            shipping_poisha=order.shipping_poisha,
            total_poisha=order.total_poisha,
            shipping_zone_slug=getattr(order, "shipping_zone_slug", None),
            shipping_zone_name=getattr(order, "shipping_zone_name", None),
            total_weight_grams=getattr(order, "total_weight_grams", 0),
            shipping_address=order.shipping_address,
            payment_method=getattr(order, "payment_method", None),
            payment_status=getattr(order, "payment_status", None),
            reservation_expires_at=getattr(order, "reservation_expires_at", None),
            placed_at=order.placed_at,
            confirmed_at=None,
            shipped_at=None,
            delivered_at=None,
            cancelled_at=None,
            items=[],
            events=[],
            user=None,
        )
        self.order = row
        return row

    async def add_item(self, item: object) -> SimpleNamespace:
        row = SimpleNamespace(
            id=uuid4(),
            order_id=item.order_id,  # type: ignore[attr-defined]
            variant_id=item.variant_id,  # type: ignore[attr-defined]
            product_id=item.product_id,  # type: ignore[attr-defined]
            product_slug=item.product_slug,  # type: ignore[attr-defined]
            product_name=item.product_name,  # type: ignore[attr-defined]
            sku=item.sku,  # type: ignore[attr-defined]
            size_label=getattr(item, "size_label", None),
            shade_name=getattr(item, "shade_name", None),
            spf=getattr(item, "spf", None),
            qty=int(item.qty),  # type: ignore[attr-defined]
            unit_price_poisha=int(item.unit_price_poisha),  # type: ignore[attr-defined]
            line_total_poisha=int(item.line_total_poisha),  # type: ignore[attr-defined]
        )
        self.items.append(row)
        assert self.order is not None
        self.order.items.append(row)
        return row

    async def add_event(self, event: object) -> object:
        if getattr(event, "id", None) is None:
            event.id = uuid4()  # type: ignore[attr-defined]
        if getattr(event, "created_at", None) is None:
            event.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
        self.events.append(event)
        assert self.order is not None
        self.order.events.append(event)
        return event

    async def require(self, _order_id: object) -> SimpleNamespace:
        assert self.order is not None
        return self.order

    async def save(self, order: SimpleNamespace) -> SimpleNamespace:
        self.order = order
        return order


def _quote(*, ready: bool = True) -> CheckoutQuoteOut:
    cart_id = uuid4()
    variant_id = uuid4()
    product_id = uuid4()
    now = datetime.now(UTC)
    return CheckoutQuoteOut(
        cart=CartOut(
            id=cart_id,
            status="active",
            item_count=1,
            subtotal_poisha=10000,
            currency="BDT",
            is_guest=False,
            updated_at=now,
            last_activity_at=now,
            items=[
                CartItemOut(
                    id=uuid4(),
                    variant_id=variant_id,
                    product_id=product_id,
                    product_slug="serum",
                    product_name="Serum",
                    size_label="30ml",
                    shade_name=None,
                    spf=None,
                    sku="SER-1",
                    qty=1,
                    unit_price_poisha=10000,
                    line_total_poisha=10000,
                    routine_step=None,
                    category_slug="serum",
                    qty_available=5,
                )
            ],
        ),
        address=CheckoutAddressSnapshotOut(
            line1="12 Road",
            city="Dhaka",
            district="Dhaka",
            country="BD",
        ),
        shipping=ShippingQuoteOut(
            zone_id=uuid4(),
            zone_slug="dhaka-metro",
            zone_name="Dhaka metro",
            total_weight_grams=100,
            charge_poisha=6000,
            free_shipping_applied=False,
            free_shipping_threshold_poisha=300000,
            matched_by="district",
        ),
        stock=[
            CheckoutStockLineOut(
                variant_id=variant_id,
                sku="SER-1",
                qty=1,
                qty_available=5,
                ok=True,
            )
        ],
        contact=CheckoutContactOut(email_verified=True, phone_verified=False, ok=True),
        merchandise_subtotal_poisha=10000,
        shipping_poisha=6000,
        total_poisha=16000,
        currency="BDT",
        ready=ready,
        blockers=[] if ready else ["stock"],
        quoted_at=now,
        place_order_available=ready,
    )


def _service(
    *,
    quote: CheckoutQuoteOut | None = None,
    cod_auto_confirm: bool = True,
) -> tuple[OrderService, FakeRepo, FakeInventory, FakeCarts, FakeAudit]:
    settings = SimpleNamespace(
        stock_reservation_ttl_minutes=15,
        cod_auto_confirm=cod_auto_confirm,
    )
    service = OrderService(FakeSession(), settings=settings)  # type: ignore[arg-type]
    repo = FakeRepo()
    inventory = FakeInventory()
    carts = FakeCarts()
    audit = FakeAudit()
    service.repo = repo  # type: ignore[assignment]
    service.inventory = inventory  # type: ignore[assignment]
    service.carts = carts  # type: ignore[assignment]
    service.audit = audit  # type: ignore[assignment]
    service.checkout = FakeCheckout(quote or _quote())  # type: ignore[assignment]
    return service, repo, inventory, carts, audit


@pytest.mark.asyncio
async def test_cod_place_auto_confirms() -> None:
    service, repo, inventory, carts, audit = _service(cod_auto_confirm=True)
    user_id = uuid4()
    out = await service.place(
        PlaceOrderIn(line1="12 Road", city="Dhaka", payment_method="cod"),
        user_id=user_id,
        guest_token=None,
    )
    assert out.status == "confirmed"
    assert out.payment_method == "cod"
    assert out.payment_status == "cod_pending"
    assert out.reservation_expires_at is None
    assert inventory.reserved == 2
    assert len(carts.converted) == 1
    assert "order.placed" in audit.actions
    assert any(
        getattr(e, "to_status", None) == "confirmed"
        and getattr(e, "source", None) == "system"
        for e in repo.events
    )


@pytest.mark.asyncio
async def test_prepaid_place_stays_pending_payment() -> None:
    service, repo, inventory, _c, _a = _service(cod_auto_confirm=True)
    out = await service.place(
        PlaceOrderIn(line1="12 Road", city="Dhaka", payment_method="bkash"),
        user_id=uuid4(),
        guest_token=None,
    )
    assert out.status == "pending_payment"
    assert out.payment_status == "pending"
    assert out.reservation_expires_at is not None
    assert inventory.reserved == 2
    assert repo.order is not None
    assert repo.order.reservation_expires_at <= datetime.now(UTC) + timedelta(minutes=16)


@pytest.mark.asyncio
async def test_cod_auto_confirm_can_be_disabled() -> None:
    service, _repo, _i, _c, _a = _service(cod_auto_confirm=False)
    out = await service.place(
        PlaceOrderIn(line1="12 Road", city="Dhaka", payment_method="cod"),
        user_id=uuid4(),
        guest_token=None,
    )
    assert out.status == "pending_payment"
    assert out.payment_status == "pending"


@pytest.mark.asyncio
async def test_place_rejects_unready_quote() -> None:
    service, _r, _i, _c, _a = _service(quote=_quote(ready=False))
    with pytest.raises(ProblemError) as exc:
        await service.place(
            PlaceOrderIn(line1="12 Road", city="Dhaka"),
            user_id=uuid4(),
            guest_token=None,
        )
    assert exc.value.status == 422
