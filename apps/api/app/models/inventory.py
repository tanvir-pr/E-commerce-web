"""Per-SKU stock batches and append-only movements."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db import Base


def _uuid7() -> UUID:
    return UUID(str(uuid7()))


class StockBatch(Base):
    __tablename__ = "stock_batches"
    __table_args__ = (
        UniqueConstraint("variant_id", "lot_code", name="uq_stock_batches_variant_lot"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lot_code: Mapped[str | None] = mapped_column(String(64))
    qty_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_on: Mapped[date | None] = mapped_column(Date)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    variant = relationship("ProductVariant", lazy="selectin")
    movements = relationship("StockMovement", back_populates="batch", lazy="noload")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("stock_batches.id", ondelete="SET NULL"),
        index=True,
    )
    qty_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    batch = relationship("StockBatch", back_populates="movements", lazy="noload")
