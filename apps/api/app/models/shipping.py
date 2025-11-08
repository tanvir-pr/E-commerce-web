"""Delivery zones and weight-based shipping tiers."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db import Base


def _uuid7() -> UUID:
    return UUID(str(uuid7()))


class DeliveryZone(Base):
    __tablename__ = "delivery_zones"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # District names matched case-insensitively (trimmed). Empty + is_default covers fallback.
    match_districts: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Null = use global free_shipping_threshold_poisha setting.
    free_shipping_threshold_poisha: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tiers = relationship(
        "DeliveryWeightTier",
        back_populates="zone",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="DeliveryWeightTier.max_weight_grams",
    )


class DeliveryWeightTier(Base):
    __tablename__ = "delivery_weight_tiers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    zone_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("delivery_zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Applies when total cart weight (g) is <= this value. Highest tier should be large.
    max_weight_grams: Mapped[int] = mapped_column(Integer, nullable=False)
    charge_poisha: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    zone = relationship("DeliveryZone", back_populates="tiers")
