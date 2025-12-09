"""Checkout quote schemas. Money fields are integer poisha."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.cart.schemas import CartOut
from app.shipping.schemas import ShippingQuoteOut


class CheckoutQuoteIn(BaseModel):
    address_id: UUID | None = None
    # Inline fallback when the shopper has not saved an address yet.
    line1: str | None = Field(default=None, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str = Field(default="BD", min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)
    label: str | None = Field(default=None, max_length=64)
    coupon_code: str | None = Field(default=None, max_length=64)


class CheckoutStockLineOut(BaseModel):
    variant_id: UUID
    sku: str
    qty: int
    qty_available: int | None
    ok: bool
    message: str | None = None


class CheckoutContactOut(BaseModel):
    email_verified: bool
    phone_verified: bool
    ok: bool


class CheckoutAddressSnapshotOut(BaseModel):
    id: UUID | None = None
    label: str | None = None
    line1: str
    line2: str | None = None
    city: str
    district: str | None = None
    postal_code: str | None = None
    country: str = "BD"
    phone: str | None = None


class CheckoutQuoteOut(BaseModel):
    cart: CartOut
    address: CheckoutAddressSnapshotOut
    shipping: ShippingQuoteOut
    stock: list[CheckoutStockLineOut]
    contact: CheckoutContactOut
    merchandise_subtotal_poisha: int
    shipping_poisha: int
    discount_poisha: int = 0
    total_poisha: int
    currency: str = "BDT"
    coupon_code: str | None = None
    coupon_id: UUID | None = None
    coupon_message: str | None = None
    ready: bool
    blockers: list[str]
    quoted_at: datetime
    place_order_available: bool = False
