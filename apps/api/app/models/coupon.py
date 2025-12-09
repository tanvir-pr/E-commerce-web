"""Discount coupons and redemptions."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid_utils import uuid7

from app.db import Base


def _uuid7() -> UUID:
    return UUID(str(uuid7()))


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)  # percent|fixed
    # percent: 1–100; fixed: poisha
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    min_spend_poisha: Mapped[int | None] = mapped_column(Integer)
    category_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_redemptions: Mapped[int | None] = mapped_column(Integer)
    max_per_user: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    __table_args__ = (UniqueConstraint("order_id", name="uq_coupon_redemptions_order"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    coupon_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    discount_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
