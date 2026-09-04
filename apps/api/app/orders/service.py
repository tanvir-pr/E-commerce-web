"""Place orders and enforce the status state machine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.audit.service import AuditService
from app.cart.service import CartService
from app.checkout.schemas import CheckoutQuoteIn
from app.checkout.service import CheckoutService
from app.config import Settings, get_settings
from app.coupons.service import CouponService
from app.flags.service import FeatureFlagService
from app.inventory.service import InventoryService
from app.models.order import Order, OrderEvent, OrderItem
from app.orders.constants import (
    ADMIN_LIST_FILTERS,
    ALLOWED_TRANSITIONS,
    CUSTOMER_CANCEL_STATUSES,
    ORDER_STATUSES,
    PAYMENT_METHODS,
    STAFF_CANCEL_STATUSES,
)
from app.orders.mailer import NullOrderMailer, OrderMailer
from app.orders.repository import OrderRepository
from app.orders.schemas import (
    DashboardAlertsOut,
    DashboardMetricsOut,
    DashboardPeriodOut,
    FunnelCountsOut,
    OrderAddressOut,
    OrderEventOut,
    OrderItemOut,
    OrderListOut,
    OrderOut,
    OrderSummaryOut,
    PlaceOrderIn,
    TopProductOut,
    TransitionIn,
)
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_VALIDATION, ProblemError


def _order_number() -> str:
    raw = str(uuid7()).replace("-", "").upper()
    return f"SOL-{raw[:4]}-{raw[4:10]}"


_EMAIL_STATUSES = frozenset(
    {
        "pending_payment",
        "confirmed",
        "shipped",
        "delivered",
        "delivery_failed",
        "returned",
        "cancelled",
    }
)


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        mailer: OrderMailer | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.mailer: OrderMailer = mailer or NullOrderMailer()
        self.repo = OrderRepository(session)
        self.checkout = CheckoutService(session)
        self.carts = CartService(session)
        self.inventory = InventoryService(session)
        self.coupons = CouponService(session)
        self.flags = FeatureFlagService(session)
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
        await self.flags.assert_can_place(method)

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
            coupon_code=body.coupon_code,
        )
        quote = await self.checkout.quote(
            quote_body,
            user_id=user_id,
            guest_token=guest_token,
            strict_coupon=True,
        )
        if not quote.ready:
            raise ProblemError(
                422,
                "Validation error",
                "Checkout quote is not ready. Fix stock or address issues first.",
                PROBLEM_VALIDATION,
            )

        fraud_score: int | None = None
        fraud_reasons: list[str] = []
        if method == "cod":
            fraud_score, fraud_reasons = await self.flags.evaluate_cod(
                user_id=user_id, quote=quote
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
            discount_poisha=quote.discount_poisha,
            total_poisha=quote.total_poisha,
            coupon_id=quote.coupon_id,
            coupon_code=quote.coupon_code if quote.discount_poisha > 0 else None,
            shipping_zone_id=quote.shipping.zone_id,
            shipping_zone_slug=quote.shipping.zone_slug,
            shipping_zone_name=quote.shipping.zone_name,
            total_weight_grams=quote.shipping.total_weight_grams,
            shipping_address=address,
            source_address_id=quote.address.id,
            payment_method=method,
            payment_status="pending",
            fraud_score=fraud_score,
            placed_at=now,
        )
        order = await self.repo.add(order)
        if quote.coupon_id is not None and quote.discount_poisha > 0:
            await self.coupons.record_redemption(
                coupon_id=quote.coupon_id,
                order_id=order.id,
                user_id=user_id,
                discount_poisha=quote.discount_poisha,
            )
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
                meta={
                    "payment_method": method,
                    "fraud_score": fraud_score,
                    "fraud_reasons": fraud_reasons,
                },
            )
        )
        order = await self.repo.require(order.id)
        reserved = await self.inventory.reserve_for_order(
            order, list(order.items), actor_user_id=user_id
        )
        if reserved:
            order.reservation_expires_at = now + timedelta(
                minutes=self.settings.stock_reservation_ttl_minutes
            )
            order = await self.repo.save(order)
        if method == "cod" and self.settings.cod_auto_confirm:
            await self._transition(
                order,
                to_status="confirmed",
                actor_user_id=user_id,
                source="system",
                note="COD accepted",
            )
        await self.carts.mark_converted(quote.cart.id)
        await self.audit.record(
            action="order.placed",
            actor_user_id=user_id,
            subject_type="order",
            subject_id=str(order.id),
            meta={
                "order_number": order.order_number,
                "total_poisha": order.total_poisha,
                "discount_poisha": order.discount_poisha,
                "coupon_code": order.coupon_code,
                "reserved_units": reserved,
                "payment_method": method,
                "fraud_score": fraud_score,
                "cod_auto_confirmed": method == "cod" and self.settings.cod_auto_confirm,
            },
        )
        order = await self.repo.require(order.id)
        # COD auto-confirm already emailed via _transition; prepaid stays pending.
        if order.status == "pending_payment":
            await self._notify_status(order, "pending_payment")
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

    async def admin_list(
        self,
        *,
        status: str = "all",
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> OrderListOut:
        if status not in ADMIN_LIST_FILTERS:
            raise ProblemError(
                422,
                "Validation error",
                f"status must be one of: {', '.join(sorted(ADMIN_LIST_FILTERS))}",
                PROBLEM_VALIDATION,
            )
        rows = await self.repo.list_admin(
            status=status, since=since, until=until
        )
        return OrderListOut(items=[self._summary(row, include_email=True) for row in rows])

    async def orders_csv(
        self,
        *,
        status: str = "all",
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> str:
        listing = await self.admin_list(status=status, since=since, until=until)
        lines = [
            "order_number,status,total_poisha,currency,payment_method,item_count,placed_at,user_email"
        ]
        for row in listing.items:
            email = (row.user_email or "").replace(",", " ")
            lines.append(
                ",".join(
                    [
                        row.order_number,
                        row.status,
                        str(row.total_poisha),
                        row.currency,
                        row.payment_method or "",
                        str(row.item_count),
                        row.placed_at.isoformat(),
                        email,
                    ]
                )
            )
        return "\n".join(lines) + "\n"

    async def metrics_csv(
        self,
        *,
        range_from: datetime | None = None,
        range_to: datetime | None = None,
    ) -> str:
        metrics = await self.dashboard_metrics(
            range_from=range_from, range_to=range_to
        )
        period = metrics.custom or metrics.last_30_days
        label = "custom" if metrics.custom else "last_30_days"
        lines = [
            "period,revenue_poisha,order_count,aov_poisha,cod_share,cancel_rate",
            ",".join(
                [
                    label,
                    str(period.revenue_poisha),
                    str(period.order_count),
                    str(period.aov_poisha),
                    f"{period.cod_share:.4f}",
                    f"{period.cancel_rate:.4f}",
                ]
            ),
            "",
            "product_slug,product_name,units,revenue_poisha",
        ]
        for product in metrics.top_products:
            name = product.product_name.replace(",", " ")
            lines.append(
                f"{product.product_slug},{name},{product.units},{product.revenue_poisha}"
            )
        return "\n".join(lines) + "\n"

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
            courier_name=body.courier_name,
            tracking_number=body.tracking_number,
        )

    async def admin_pack(
        self, order_id: UUID, *, actor_user_id: UUID, note: str | None = None
    ) -> OrderOut:
        order = await self.repo.require(order_id)
        if order.status != "confirmed":
            raise ProblemError(
                422,
                "Validation error",
                "Only confirmed orders can be marked packed.",
                PROBLEM_VALIDATION,
            )
        if order.packed_at is not None:
            return self._order_out(order, actor="staff")
        now = datetime.now(UTC)
        order.packed_at = now
        await self.repo.add_event(
            OrderEvent(
                order_id=order.id,
                from_status="confirmed",
                to_status="confirmed",
                actor_user_id=actor_user_id,
                source="staff",
                note=note or "Packed",
                meta={"packed": True},
            )
        )
        await self.audit.record(
            action="order.packed",
            actor_user_id=actor_user_id,
            subject_type="order",
            subject_id=str(order.id),
            meta={"order_number": order.order_number},
        )
        order = await self.repo.save(order)
        return self._order_out(order, actor="staff")

    async def dashboard_metrics(
        self,
        *,
        range_from: datetime | None = None,
        range_to: datetime | None = None,
    ) -> DashboardMetricsOut:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day7 = now - timedelta(days=7)
        day30 = now - timedelta(days=30)
        if range_from is not None and range_to is not None and range_from >= range_to:
            raise ProblemError(
                422,
                "Validation error",
                "range_from must be before range_to.",
                PROBLEM_VALIDATION,
            )
        funnel_raw = await self.repo.count_by_status()
        funnel = FunnelCountsOut(
            pending_payment=funnel_raw.get("pending_payment", 0),
            confirmed=funnel_raw.get("confirmed", 0),
            shipped=funnel_raw.get("shipped", 0),
            delivered=funnel_raw.get("delivered", 0),
            delivery_failed=funnel_raw.get("delivery_failed", 0),
            returned=funnel_raw.get("returned", 0),
            cancelled=funnel_raw.get("cancelled", 0),
        )
        low = await self.inventory.low_stock(
            threshold=self.settings.inventory_low_stock_threshold
        )
        near_expiry = 0
        for item in low.items:
            if item.nearest_expiry is None:
                continue
            days = (item.nearest_expiry - now.date()).days
            if 0 <= days <= self.settings.inventory_near_expiry_days:
                near_expiry += 1
        abandoned = await self.carts.admin_list(status="abandoned")
        abandoned_value = sum(row.subtotal_poisha for row in abandoned.items)
        overdue = await self.repo.count_overdue_confirmed(
            cutoff=now - timedelta(hours=self.settings.fulfilment_sla_hours)
        )
        top_since = range_from or day30
        top_until = range_to
        top_rows = await self.repo.top_products(
            since=top_since, until=top_until, limit=5
        )
        custom = None
        if range_from is not None:
            custom = self._period(
                await self.repo.period_stats(since=range_from, until=range_to)
            )
        return DashboardMetricsOut(
            today=self._period(await self.repo.period_stats(since=today_start)),
            last_7_days=self._period(await self.repo.period_stats(since=day7)),
            last_30_days=self._period(await self.repo.period_stats(since=day30)),
            custom=custom,
            range_from=range_from,
            range_to=range_to,
            funnel=funnel,
            alerts=DashboardAlertsOut(
                low_stock_count=len(low.items),
                near_expiry_count=near_expiry,
                overdue_shipments=overdue,
                abandoned_cart_value_poisha=abandoned_value,
            ),
            top_products=[
                TopProductOut(
                    product_id=row[0],
                    product_slug=row[1],
                    product_name=row[2],
                    units=int(row[3] or 0),
                    revenue_poisha=int(row[4] or 0),
                )
                for row in top_rows
            ],
            unshipped_confirmed=funnel.confirmed,
        )

    def _period(self, raw: dict[str, float | int]) -> DashboardPeriodOut:
        order_count = int(raw["order_count"])
        revenue = int(raw["revenue_poisha"])
        placed = int(raw["placed_count"])
        cancelled = int(raw["cancelled_count"])
        cod_sold = int(raw["cod_sold_count"])
        return DashboardPeriodOut(
            revenue_poisha=revenue,
            order_count=order_count,
            aov_poisha=(revenue // order_count) if order_count else 0,
            cod_share=(cod_sold / order_count) if order_count else 0.0,
            cancel_rate=(cancelled / placed) if placed else 0.0,
        )

    async def confirm_prepaid(
        self,
        order: Order,
        *,
        actor_user_id: UUID,
        provider_ref: str,
        gateway: str,
    ) -> OrderOut:
        """Confirm a prepaid order after gateway validation; sets payment_status=paid."""
        return await self._transition(
            order,
            to_status="confirmed",
            actor_user_id=actor_user_id,
            source="system",
            note=f"{gateway} payment validated",
            mark_paid=True,
            event_meta={"provider_ref": provider_ref, "gateway": gateway},
        )

    async def confirm_late_prepaid(
        self,
        order: Order,
        *,
        actor_user_id: UUID,
        provider_ref: str,
        gateway: str,
    ) -> OrderOut:
        """Revive a cancelled order after late gateway payment + successful re-reserve."""
        return await self._transition(
            order,
            to_status="confirmed",
            actor_user_id=actor_user_id,
            source="system",
            note=f"{gateway} late payment re-reserved",
            mark_paid=True,
            event_meta={
                "provider_ref": provider_ref,
                "gateway": gateway,
                "late_payment": True,
            },
        )

    async def _transition(
        self,
        order: Order,
        *,
        to_status: str,
        actor_user_id: UUID,
        source: str,
        note: str | None,
        courier_name: str | None = None,
        tracking_number: str | None = None,
        mark_paid: bool = False,
        event_meta: dict[str, object] | None = None,
    ) -> OrderOut:
        if to_status not in ORDER_STATUSES:
            raise ProblemError(
                422,
                "Validation error",
                f"Unknown status: {to_status}",
                PROBLEM_VALIDATION,
            )
        allowed = ALLOWED_TRANSITIONS.get(order.status, frozenset())
        late_revive = (
            source == "system"
            and order.status == "cancelled"
            and to_status == "confirmed"
            and mark_paid
        )
        if to_status not in allowed and not late_revive:
            raise ProblemError(
                422,
                "Validation error",
                f"Cannot transition from {order.status} to {to_status}.",
                PROBLEM_VALIDATION,
            )
        if to_status == "cancelled":
            if source == "customer" and order.status not in CUSTOMER_CANCEL_STATUSES:
                raise ProblemError(
                    403,
                    "Forbidden",
                    "Customers cannot cancel after shipping.",
                    PROBLEM_FORBIDDEN,
                )
            if source == "staff" and order.status not in STAFF_CANCEL_STATUSES:
                raise ProblemError(
                    422,
                    "Validation error",
                    "Staff cannot cancel after shipping. Mark delivery_failed or returned instead.",
                    PROBLEM_VALIDATION,
                )

        from_status = order.status
        now = datetime.now(UTC)
        order.status = to_status
        if to_status == "confirmed":
            order.confirmed_at = now
            order.reservation_expires_at = None
            if mark_paid:
                order.payment_status = "paid"
            elif order.payment_method == "cod":
                order.payment_status = "cod_pending"
            elif order.payment_status in (None, "pending"):
                order.payment_status = "pending"
        elif to_status == "shipped":
            courier = (courier_name or order.courier_name or "").strip()
            tracking = (tracking_number or order.tracking_number or "").strip()
            if source == "staff" and (not courier or not tracking):
                raise ProblemError(
                    422,
                    "Validation error",
                    "courier_name and tracking_number are required to ship.",
                    PROBLEM_VALIDATION,
                )
            order.courier_name = courier or order.courier_name
            order.tracking_number = tracking or order.tracking_number
            if order.packed_at is None:
                order.packed_at = now
            order.shipped_at = now
            order.reservation_expires_at = None
            # First ship consumes; retry after delivery_failed is a no-op.
            await self.inventory.consume_for_order(order, actor_user_id=actor_user_id)
        elif to_status == "delivered":
            order.delivered_at = now
            if order.payment_method == "cod":
                order.payment_status = "collected"
        elif to_status == "delivery_failed":
            order.delivery_failed_at = now
        elif to_status == "returned":
            order.returned_at = now
            if order.payment_method == "cod" and order.payment_status == "cod_pending":
                order.payment_status = "cancelled"
            await self.inventory.restock_for_order(
                order,
                actor_user_id=actor_user_id,
                note=note or "Returned parcel restocked",
            )
        elif to_status == "cancelled":
            order.cancelled_at = now
            order.payment_status = "cancelled"
            order.reservation_expires_at = None
            await self.inventory.release_for_order(
                order,
                actor_user_id=actor_user_id,
                note=note or "Order cancelled",
            )

        await self.repo.add_event(
            OrderEvent(
                order_id=order.id,
                from_status=from_status,
                to_status=to_status,
                actor_user_id=actor_user_id,
                source=source,
                note=note,
                meta=event_meta,
            )
        )
        await self.audit.record(
            action="order.transitioned",
            actor_user_id=actor_user_id,
            subject_type="order",
            subject_id=str(order.id),
            meta={
                "from": from_status,
                "to": to_status,
                "source": source,
                "courier_name": order.courier_name,
                "tracking_number": order.tracking_number,
                **(event_meta or {}),
            },
        )
        order = await self.repo.save(order)
        order = await self.repo.require(order.id)
        await self._notify_status(order, to_status)
        return self._order_out(order, actor="staff" if source == "staff" else "customer")

    async def wants_order_emails(self, user_id: UUID) -> bool:
        from app.support.service import SupportService

        return await SupportService(self.session).wants_order_updates(user_id)

    async def _notify_status(self, order: Order, status: str) -> None:
        if status not in _EMAIL_STATUSES:
            return
        user = order.user
        email = user.email if user is not None else None
        if not email:
            return
        if not await self.wants_order_emails(order.user_id):
            return
        await self.mailer.send_order_status(
            email=email,
            order_id=str(order.id),
            order_number=order.order_number,
            status=status,
            courier_name=order.courier_name,
            tracking_number=order.tracking_number,
        )

    async def expire_reservations(self) -> int:
        """Cancel pending_payment orders whose stock hold has expired."""
        now = datetime.now(UTC)
        rows = await self.repo.list_expired_pending(now=now)
        count = 0
        for order in rows:
            await self._transition(
                order,
                to_status="cancelled",
                actor_user_id=order.user_id,
                source="system",
                note="Stock reservation expired",
            )
            count += 1
        return count

    def _age_hours(self, order: Order) -> float:
        anchor = order.confirmed_at or order.placed_at
        return round((datetime.now(UTC) - anchor).total_seconds() / 3600, 1)

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
            payment_method=order.payment_method,
            shipping_zone_slug=order.shipping_zone_slug,
            courier_name=order.courier_name,
            tracking_number=order.tracking_number,
            packed_at=order.packed_at,
            confirmed_at=order.confirmed_at,
            shipped_at=order.shipped_at,
            age_hours=self._age_hours(order),
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
            discount_poisha=int(getattr(order, "discount_poisha", 0) or 0),
            total_poisha=order.total_poisha,
            coupon_code=getattr(order, "coupon_code", None),
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
            fraud_score=getattr(order, "fraud_score", None),
            reservation_expires_at=order.reservation_expires_at,
            courier_name=order.courier_name,
            tracking_number=order.tracking_number,
            packed_at=order.packed_at,
            placed_at=order.placed_at,
            confirmed_at=order.confirmed_at,
            shipped_at=order.shipped_at,
            delivered_at=order.delivered_at,
            delivery_failed_at=order.delivery_failed_at,
            returned_at=order.returned_at,
            cancelled_at=order.cancelled_at,
            age_hours=self._age_hours(order),
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
                for event in sorted(
                    order.events,
                    key=lambda e: e.created_at or datetime.min.replace(tzinfo=UTC),
                )
            ],
            allowed_transitions=allowed,
        )
