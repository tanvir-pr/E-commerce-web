"""Order status emails enqueue on place and transitions (Part 22)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.orders.schemas import PlaceOrderIn, TransitionIn
from app.orders.service import OrderService
from app.problems import ProblemError


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeInventory:
    async def reserve_for_order(self, *_args: object, **_kwargs: object) -> int:
        return 0

    async def release_for_order(self, *_args: object, **_kwargs: object) -> int:
        return 0

    async def consume_for_order(self, *_args: object, **_kwargs: object) -> int:
        return 0

    async def restock_for_order(self, *_args: object, **_kwargs: object) -> int:
        return 0


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []

    async def send_order_status(self, **kwargs: object) -> None:
        self.sent.append(kwargs)


class FakeRepo:
    def __init__(self, order: SimpleNamespace) -> None:
        self.order = order

    async def require(self, _order_id: object) -> SimpleNamespace:
        return self.order

    async def require_owned(self, order_id: object, user_id: object) -> SimpleNamespace:
        if self.order.id != order_id or self.order.user_id != user_id:
            raise ProblemError(404, "Not found", "Order not found.", "x")
        return self.order

    async def add_event(self, event: object) -> object:
        if getattr(event, "id", None) is None:
            event.id = uuid4()  # type: ignore[attr-defined]
        if getattr(event, "created_at", None) is None:
            event.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
        self.order.events.append(event)
        return event

    async def save(self, order: SimpleNamespace) -> SimpleNamespace:
        return order


def _order(status: str) -> SimpleNamespace:
    user_id = uuid4()
    return SimpleNamespace(
        id=uuid4(),
        order_number="SOL-MAIL-000001",
        user_id=user_id,
        status=status,
        currency="BDT",
        merchandise_subtotal_poisha=10000,
        shipping_poisha=6000,
        total_poisha=16000,
        shipping_zone_slug="dhaka-metro",
        shipping_zone_name="Dhaka metro",
        total_weight_grams=100,
        shipping_address={"line1": "12 Road", "city": "Dhaka", "country": "BD"},
        payment_method="cod",
        payment_status="cod_pending",
        reservation_expires_at=None,
        courier_name=None,
        tracking_number=None,
        packed_at=None,
        placed_at=datetime.now(UTC),
        confirmed_at=datetime.now(UTC) if status != "pending_payment" else None,
        shipped_at=None,
        delivered_at=None,
        delivery_failed_at=None,
        returned_at=None,
        cancelled_at=None,
        items=[],
        events=[],
        user=SimpleNamespace(id=user_id, email="buyer@example.com"),
    )


def _service(order: SimpleNamespace) -> tuple[OrderService, FakeMailer]:
    mailer = FakeMailer()
    service = OrderService(FakeSession(), mailer=mailer)  # type: ignore[arg-type]
    service.repo = FakeRepo(order)  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    service.inventory = FakeInventory()  # type: ignore[assignment]

    async def _always_email(_user_id: object) -> bool:
        return True

    service.wants_order_emails = _always_email  # type: ignore[method-assign]
    return service, mailer


@pytest.mark.asyncio
async def test_ship_emails_buyer_with_tracking() -> None:
    order = _order("confirmed")
    service, mailer = _service(order)
    out = await service.admin_transition(
        order.id,
        TransitionIn(
            to_status="shipped",
            courier_name="Pathao",
            tracking_number="PX-99",
            note="Out for delivery",
        ),
        actor_user_id=uuid4(),
    )
    assert out.status == "shipped"
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["email"] == "buyer@example.com"
    assert mailer.sent[0]["status"] == "shipped"
    assert mailer.sent[0]["courier_name"] == "Pathao"
    assert mailer.sent[0]["tracking_number"] == "PX-99"
    assert mailer.sent[0]["order_number"] == "SOL-MAIL-000001"


@pytest.mark.asyncio
async def test_delivery_failed_and_returned_emails() -> None:
    order = _order("shipped")
    order.courier_name = "Pathao"
    order.tracking_number = "PX-1"
    order.shipped_at = datetime.now(UTC)
    service, mailer = _service(order)
    await service.admin_transition(
        order.id,
        TransitionIn(to_status="delivery_failed"),
        actor_user_id=uuid4(),
    )
    assert mailer.sent[-1]["status"] == "delivery_failed"
    await service.admin_transition(
        order.id,
        TransitionIn(to_status="returned"),
        actor_user_id=uuid4(),
    )
    assert mailer.sent[-1]["status"] == "returned"
    assert len(mailer.sent) == 2


@pytest.mark.asyncio
async def test_skips_email_without_user_address() -> None:
    order = _order("confirmed")
    order.user = None
    service, mailer = _service(order)
    await service.admin_transition(
        order.id,
        TransitionIn(
            to_status="shipped",
            courier_name="Pathao",
            tracking_number="PX-2",
        ),
        actor_user_id=uuid4(),
    )
    assert mailer.sent == []


@pytest.mark.asyncio
async def test_customer_cancel_emails() -> None:
    order = _order("confirmed")
    service, mailer = _service(order)
    await service.cancel_mine(order.id, user_id=order.user_id)
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_prepaid_place_emails_pending_payment() -> None:
    from app.cart.schemas import CartItemOut, CartOut
    from app.checkout.schemas import (
        CheckoutAddressSnapshotOut,
        CheckoutContactOut,
        CheckoutQuoteOut,
        CheckoutStockLineOut,
    )
    from app.shipping.schemas import ShippingQuoteOut

    class FakeCarts:
        async def mark_converted(self, _cart_id: object) -> None:
            return None

    class FakeCheckout:
        async def quote(self, *_a: object, **_k: object) -> CheckoutQuoteOut:
            now = datetime.now(UTC)
            vid = uuid4()
            pid = uuid4()
            return CheckoutQuoteOut(
                cart=CartOut(
                    id=uuid4(),
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
                            variant_id=vid,
                            product_id=pid,
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
                    line1="12 Road", city="Dhaka", district="Dhaka", country="BD"
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
                        variant_id=vid,
                        sku="SER-1",
                        qty=1,
                        qty_available=5,
                        ok=True,
                    )
                ],
                contact=CheckoutContactOut(
                    email_verified=True, phone_verified=False, ok=True
                ),
                merchandise_subtotal_poisha=10000,
                shipping_poisha=6000,
                total_poisha=16000,
                currency="BDT",
                ready=True,
                blockers=[],
                quoted_at=now,
                place_order_available=True,
            )

    class PlaceRepo:
        def __init__(self) -> None:
            self.order: SimpleNamespace | None = None

        async def add(self, order: object) -> SimpleNamespace:
            user_id = order.user_id  # type: ignore[attr-defined]
            row = SimpleNamespace(
                id=uuid4(),
                order_number=order.order_number,  # type: ignore[attr-defined]
                user_id=user_id,
                cart_id=getattr(order, "cart_id", None),
                status=order.status,  # type: ignore[attr-defined]
                currency=getattr(order, "currency", "BDT"),
                merchandise_subtotal_poisha=order.merchandise_subtotal_poisha,  # type: ignore[attr-defined]
                shipping_poisha=order.shipping_poisha,  # type: ignore[attr-defined]
                discount_poisha=getattr(order, "discount_poisha", 0),
                total_poisha=order.total_poisha,  # type: ignore[attr-defined]
                coupon_id=getattr(order, "coupon_id", None),
                coupon_code=getattr(order, "coupon_code", None),
                shipping_zone_slug=getattr(order, "shipping_zone_slug", None),
                shipping_zone_name=getattr(order, "shipping_zone_name", None),
                total_weight_grams=getattr(order, "total_weight_grams", 0),
                shipping_address=order.shipping_address,  # type: ignore[attr-defined]
                payment_method=getattr(order, "payment_method", None),
                payment_status=getattr(order, "payment_status", None),
                fraud_score=getattr(order, "fraud_score", None),
                reservation_expires_at=getattr(order, "reservation_expires_at", None),
                courier_name=None,
                tracking_number=None,
                packed_at=None,
                placed_at=order.placed_at,  # type: ignore[attr-defined]
                confirmed_at=None,
                shipped_at=None,
                delivered_at=None,
                delivery_failed_at=None,
                returned_at=None,
                cancelled_at=None,
                items=[],
                events=[],
                user=SimpleNamespace(id=user_id, email="buyer@example.com"),
            )
            self.order = row
            return row

        async def add_item(self, item: object) -> SimpleNamespace:
            assert self.order is not None
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
            self.order.items.append(row)
            return row

        async def add_event(self, event: object) -> object:
            assert self.order is not None
            if getattr(event, "id", None) is None:
                event.id = uuid4()  # type: ignore[attr-defined]
            if getattr(event, "created_at", None) is None:
                event.created_at = datetime.now(UTC)  # type: ignore[attr-defined]
            self.order.events.append(event)
            return event

        async def require(self, _order_id: object) -> SimpleNamespace:
            assert self.order is not None
            return self.order

        async def save(self, order: SimpleNamespace) -> SimpleNamespace:
            self.order = order
            return order

    settings = SimpleNamespace(
        stock_reservation_ttl_minutes=15,
        cod_auto_confirm=True,
    )
    mailer = FakeMailer()
    service = OrderService(FakeSession(), settings=settings, mailer=mailer)  # type: ignore[arg-type]
    service.repo = PlaceRepo()  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    service.inventory = FakeInventory()  # type: ignore[assignment]
    service.carts = FakeCarts()  # type: ignore[assignment]
    service.checkout = FakeCheckout()  # type: ignore[assignment]

    async def _always_email(_user_id: object) -> bool:
        return True

    service.wants_order_emails = _always_email  # type: ignore[method-assign]

    class FakeFlags:
        async def assert_can_place(self, _method: str) -> None:
            return None

        async def evaluate_cod(self, **_kwargs: object) -> tuple[int, list[str]]:
            return 0, []

    service.flags = FakeFlags()  # type: ignore[assignment]

    out = await service.place(
        PlaceOrderIn(line1="12 Road", city="Dhaka", payment_method="bkash"),
        user_id=uuid4(),
        guest_token=None,
    )
    assert out.status == "pending_payment"
    assert len(mailer.sent) == 1
    assert mailer.sent[0]["status"] == "pending_payment"
