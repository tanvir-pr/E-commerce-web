"""Place orders and enforce the status state machine."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.audit.service import AuditService
from app.cart.service import CartService
from app.checkout.schemas import CheckoutQuoteIn
from app.checkout.service import CheckoutService
from app.models.order import Order, OrderEvent, OrderItem
from app.orders.constants import (
    ADMIN_LIST_FILTERS,
    ALLOWED_TRANSITIONS,
    CUSTOMER_CANCEL_STATUSES,
    ORDER_STATUSES,
    PAYMENT_METHODS,
)
from app.orders.repository import OrderRepository
from app.orders.schemas import (
    OrderAddressOut,
    OrderEventOut,
    OrderItemOut,
    OrderListOut,
    OrderOut,
    OrderSummaryOut,
    PlaceOrderIn,
    TransitionIn,
)
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_VALIDATION, ProblemError


def _order_number() -> str:
    raw = str(uuid7()).replace("-", "").upper()
    return f"SOL-{raw[:4]}-{raw[4:10]}"


class OrderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OrderRepository(session)
        self.checkout = CheckoutService(session)
        self.carts = CartService(session)
        self.audit = AuditService(session)

    async def place(
        self,
        body: PlaceOrderIn,
        *,
        user_id: UUID,
        guest_token: str | None,
    ) -> OrderOut:
        method = (body.payment_method or "cod").strip().lower()
        if method not in PAYMENT_METHODS:
            raise ProblemError(
                422,
                "Validation error",
                f"payment_method must be one of: {', '.join(sorted(PAYMENT_METHODS))}",
                PROBLEM_VALIDATION,
            )

        quote_body = CheckoutQuoteIn(
            address_id=body.address_id,
            line1=body.line1,
            line2=body.line2,
            city=body.city,
            district=body.district,
            postal_code=body.postal_code,
            country=body.country,
            phone=body.phone,
            label=body.label,
        )
        quote = await self.checkout.quote(
            quote_body, user_id=user_id, guest_token=guest_token
        )
        if not quote.ready:
            raise ProblemError(
                422,
                "Validation error",
                "Checkout quote is not ready. Fix stock or address issues first.",
                PROBLEM_VALIDATION,
            )

        now = datetime.now(UTC)
        address = quote.address.model_dump(mode="json")
        order = Order(
            order_number=_order_number(),
            user_id=user_id,
            cart_id=quote.cart.id,
            status="pending_payment",
            currency=quote.currency,
            merchandise_subtotal_poisha=quote.merchandise_subtotal_poisha,
            shipping_poisha=quote.shipping_poisha,
            total_poisha=quote.total_poisha,
            shipping_zone_id=quote.shipping.zone_id,
            shipping_zone_slug=quote.shipping.zone_slug,
            shipping_zone_name=quote.shipping.zone_name,
            total_weight_grams=quote.shipping.total_weight_grams,
            shipping_address=address,
            source_address_id=quote.address.id,
            payment_method=method,
            payment_status="pending",
            placed_at=now,
        )
        order = await self.repo.add(order)
        for item in quote.cart.items:
            await self.repo.add_item(
                OrderItem(
                    order_id=order.id,
                    variant_id=item.variant_id,
                    product_id=item.product_id,
                    product_slug=item.product_slug,
                    product_name=item.product_name,
                    sku=item.sku,
                    size_label=item.size_label,
                    shade_name=item.shade_name,
                    spf=item.spf,
                    qty=item.qty,
                    unit_price_poisha=item.unit_price_poisha,
                    line_total_poisha=item.line_total_poisha,
                )
            )
        await self.repo.add_event(
            OrderEvent(
                order_id=order.id,
                from_status=None,
                to_status="pending_payment",
                actor_user_id=user_id,
                source="customer",
                note="Order placed",
                meta={"payment_method": method},
            )
        )
        # Part 18: reserve stock here. Part 19: COD may auto-confirm.
        await self.carts.mark_converted(quote.cart.id)
        await self.audit.record(
            action="order.placed",
            actor_user_id=user_id,
            subject_type="order",
            subject_id=str(order.id),
            meta={"order_number": order.order_number, "total_poisha": order.total_poisha},
        )
        order = await self.repo.require(order.id)
        return self._order_out(order, actor="customer")

    async def list_mine(self, user_id: UUID) -> OrderListOut:
        rows = await self.repo.list_for_user(user_id)
        return OrderListOut(items=[self._summary(row) for row in rows])

    async def get_mine(self, order_id: UUID, *, user_id: UUID) -> OrderOut:
        order = await self.repo.require_owned(order_id, user_id)
        return self._order_out(order, actor="customer")

    async def cancel_mine(
        self, order_id: UUID, *, user_id: UUID, note: str | None = None
    ) -> OrderOut:
        order = await self.repo.require_owned(order_id, user_id)
        if order.status not in CUSTOMER_CANCEL_STATUSES:
            raise ProblemError(
                422,
                "Validation error",
                "This order can no longer be cancelled.",
                PROBLEM_VALIDATION,
            )
        return await self._transition(
            order,
            to_status="cancelled",
            actor_user_id=user_id,
            source="customer",
            note=note or "Cancelled by customer",
        )

    async def admin_list(self, *, status: str = "all") -> OrderListOut:
        if status not in ADMIN_LIST_FILTERS:
            raise ProblemError(
                422,
                "Validation error",
                f"status must be one of: {', '.join(sorted(ADMIN_LIST_FILTERS))}",
                PROBLEM_VALIDATION,
            )
        rows = await self.repo.list_admin(status=status)
        return OrderListOut(items=[self._summary(row, include_email=True) for row in rows])

    async def admin_get(self, order_id: UUID) -> OrderOut:
        order = await self.repo.require(order_id)
        return self._order_out(order, actor="staff")

    async def admin_transition(
        self, order_id: UUID, body: TransitionIn, *, actor_user_id: UUID
    ) -> OrderOut:
        order = await self.repo.require(order_id)
        return await self._transition(
            order,
            to_status=body.to_status.strip().lower(),
            actor_user_id=actor_user_id,
            source="staff",
            note=body.note,
        )

    async def _transition(
        self,
        order: Order,
        *,
        to_status: str,
        actor_user_id: UUID,
        source: str,
        note: str | None,
    ) -> OrderOut:
        if to_status not in ORDER_STATUSES:
            raise ProblemError(
                422,
                "Validation error",
                f"Unknown status: {to_status}",
                PROBLEM_VALIDATION,
            )
        allowed = ALLOWED_TRANSITIONS.get(order.status, frozenset())
        if to_status not in allowed:
            raise ProblemError(
                422,
                "Validation error",
                f"Cannot transition from {order.status} to {to_status}.",
                PROBLEM_VALIDATION,
            )
        if source == "customer" and to_status == "cancelled":
            if order.status not in CUSTOMER_CANCEL_STATUSES:
                raise ProblemError(
                    403,
                    "Forbidden",
                    "Customers cannot cancel after shipping.",
                    PROBLEM_FORBIDDEN,
                )

        from_status = order.status
        now = datetime.now(UTC)
        order.status = to_status
        if to_status == "confirmed":
            order.confirmed_at = now
            if order.payment_method == "cod":
                order.payment_status = "cod_pending"
        elif to_status == "shipped":
            order.shipped_at = now
        elif to_status == "delivered":
            order.delivered_at = now
            if order.payment_method == "cod":
                order.payment_status = "collected"
        elif to_status == "cancelled":
            order.cancelled_at = now
            order.payment_status = "cancelled"
            # Part 18: release reservation here.

        await self.repo.add_event(
            OrderEvent(
                order_id=order.id,
                from_status=from_status,
                to_status=to_status,
                actor_user_id=actor_user_id,
                source=source,
                note=note,
            )
        )
        await self.audit.record(
            action="order.transitioned",
            actor_user_id=actor_user_id,
            subject_type="order",
            subject_id=str(order.id),
            meta={"from": from_status, "to": to_status, "source": source},
        )
        order = await self.repo.save(order)
        return self._order_out(order, actor="staff" if source == "staff" else "customer")

    def _summary(self, order: Order, *, include_email: bool = False) -> OrderSummaryOut:
        return OrderSummaryOut(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            total_poisha=order.total_poisha,
            currency=order.currency,
            item_count=sum(i.qty for i in order.items),
            placed_at=order.placed_at,
            user_email=order.user.email if include_email and order.user else None,
        )

    def _order_out(self, order: Order, *, actor: str) -> OrderOut:
        if actor == "staff":
            allowed = sorted(ALLOWED_TRANSITIONS.get(order.status, frozenset()))
        elif order.status in CUSTOMER_CANCEL_STATUSES:
            allowed = ["cancelled"]
        else:
            allowed = []
        address = order.shipping_address or {}
        return OrderOut(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            currency=order.currency,
            merchandise_subtotal_poisha=order.merchandise_subtotal_poisha,
            shipping_poisha=order.shipping_poisha,
            total_poisha=order.total_poisha,
            shipping_zone_slug=order.shipping_zone_slug,
            shipping_zone_name=order.shipping_zone_name,
            total_weight_grams=order.total_weight_grams,
            shipping_address=OrderAddressOut(
                id=address.get("id"),
                label=address.get("label"),
                line1=str(address.get("line1") or ""),
                line2=address.get("line2"),
                city=str(address.get("city") or ""),
                district=address.get("district"),
                postal_code=address.get("postal_code"),
                country=str(address.get("country") or "BD"),
                phone=address.get("phone"),
            ),
            payment_method=order.payment_method,
            payment_status=order.payment_status,
            placed_at=order.placed_at,
            confirmed_at=order.confirmed_at,
            shipped_at=order.shipped_at,
            delivered_at=order.delivered_at,
            cancelled_at=order.cancelled_at,
            items=[
                OrderItemOut(
                    id=item.id,
                    variant_id=item.variant_id,
                    product_id=item.product_id,
                    product_slug=item.product_slug,
                    product_name=item.product_name,
                    sku=item.sku,
                    size_label=item.size_label,
                    shade_name=item.shade_name,
                    spf=item.spf,
                    qty=item.qty,
                    unit_price_poisha=item.unit_price_poisha,
                    line_total_poisha=item.line_total_poisha,
                )
                for item in order.items
            ],
            events=[
                OrderEventOut(
                    id=event.id,
                    from_status=event.from_status,
                    to_status=event.to_status,
                    actor_user_id=event.actor_user_id,
                    source=event.source,
                    note=event.note,
                    created_at=event.created_at,
                )
                for event in sorted(order.events, key=lambda e: e.created_at)
            ],
            allowed_transitions=allowed,
        )
