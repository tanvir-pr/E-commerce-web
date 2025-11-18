"""Orders, line items, and append-only status events."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db import Base


def _uuid7() -> UUID:
    return UUID(str(uuid7()))


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cart_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    merchandise_subtotal_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    total_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_zone_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    shipping_zone_slug: Mapped[str | None] = mapped_column(String(64))
    shipping_zone_name: Mapped[str | None] = mapped_column(String(128))
    total_weight_grams: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shipping_address: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_address_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(32))
    payment_status: Mapped[str | None] = mapped_column(String(32))
    reservation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    courier_name: Mapped[str | None] = mapped_column(String(64), index=True)
    tracking_number: Mapped[str | None] = mapped_column(String(128), index=True)
    packed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user = relationship("User", lazy="selectin")
    items = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OrderItem.created_at",
    )
    events = relationship(
        "OrderEvent",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OrderEvent.created_at",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    product_slug: Mapped[str] = mapped_column(String(160), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    size_label: Mapped[str | None] = mapped_column(String(64))
    shade_name: Mapped[str | None] = mapped_column(String(64))
    spf: Mapped[int | None] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order = relationship("Order", back_populates="items")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="system")
    note: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order = relationship("Order", back_populates="events")
