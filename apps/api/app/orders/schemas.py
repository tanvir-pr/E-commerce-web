"""Order API schemas. Money fields are integer poisha."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrderItemOut(BaseModel):
    id: UUID
    variant_id: UUID
    product_id: UUID
    product_slug: str
    product_name: str
    sku: str
    size_label: str | None
    shade_name: str | None
    spf: int | None
    qty: int
    unit_price_poisha: int
    line_total_poisha: int


class OrderEventOut(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str
    actor_user_id: UUID | None
    source: str
    note: str | None
    created_at: datetime


class OrderAddressOut(BaseModel):
    id: UUID | None = None
    label: str | None = None
    line1: str
    line2: str | None = None
    city: str
    district: str | None = None
    postal_code: str | None = None
    country: str = "BD"
    phone: str | None = None


class OrderOut(BaseModel):
    id: UUID
    order_number: str
    status: str
    currency: str
    merchandise_subtotal_poisha: int
    shipping_poisha: int
    discount_poisha: int = 0
    total_poisha: int
    coupon_code: str | None = None
    shipping_zone_slug: str | None
    shipping_zone_name: str | None
    total_weight_grams: int
    shipping_address: OrderAddressOut
    payment_method: str | None
    payment_status: str | None
    fraud_score: int | None = None
    reservation_expires_at: datetime | None = None
    courier_name: str | None = None
    tracking_number: str | None = None
    packed_at: datetime | None = None
    placed_at: datetime
    confirmed_at: datetime | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    delivery_failed_at: datetime | None = None
    returned_at: datetime | None = None
    cancelled_at: datetime | None
    items: list[OrderItemOut]
    events: list[OrderEventOut] = Field(default_factory=list)
    allowed_transitions: list[str] = Field(default_factory=list)
    age_hours: float | None = None


class OrderSummaryOut(BaseModel):
    id: UUID
    order_number: str
    status: str
    total_poisha: int
    currency: str
    item_count: int
    placed_at: datetime
    user_email: str | None = None
    payment_method: str | None = None
    shipping_zone_slug: str | None = None
    courier_name: str | None = None
    tracking_number: str | None = None
    packed_at: datetime | None = None
    confirmed_at: datetime | None = None
    shipped_at: datetime | None = None
    age_hours: float | None = None


class OrderListOut(BaseModel):
    items: list[OrderSummaryOut]


class PlaceOrderIn(BaseModel):
    address_id: UUID | None = None
    line1: str | None = Field(default=None, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(default="BD", min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)
    label: str | None = Field(default=None, max_length=64)
    payment_method: str | None = Field(default="cod", max_length=32)
    coupon_code: str | None = Field(default=None, max_length=64)


class TransitionIn(BaseModel):
    to_status: str = Field(min_length=1, max_length=32)
    note: str | None = Field(default=None, max_length=500)
    courier_name: str | None = Field(default=None, max_length=64)
    tracking_number: str | None = Field(default=None, max_length=128)


class MessageOut(BaseModel):
    message: str


class FunnelCountsOut(BaseModel):
    pending_payment: int
    confirmed: int
    shipped: int
    delivered: int
    delivery_failed: int = 0
    returned: int = 0
    cancelled: int


class DashboardPeriodOut(BaseModel):
    revenue_poisha: int
    order_count: int
    aov_poisha: int
    cod_share: float
    cancel_rate: float


class DashboardAlertsOut(BaseModel):
    low_stock_count: int
    near_expiry_count: int
    overdue_shipments: int
    abandoned_cart_value_poisha: int


class TopProductOut(BaseModel):
    product_id: UUID
    product_slug: str
    product_name: str
    units: int
    revenue_poisha: int


class DashboardMetricsOut(BaseModel):
    currency: str = "BDT"
    today: DashboardPeriodOut
    last_7_days: DashboardPeriodOut
    last_30_days: DashboardPeriodOut
    custom: DashboardPeriodOut | None = None
    range_from: datetime | None = None
    range_to: datetime | None = None
    funnel: FunnelCountsOut
    alerts: DashboardAlertsOut
    top_products: list[TopProductOut]
    unshipped_confirmed: int

