"""Support tickets and notification preferences."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid_utils import uuid7

from app.db import Base


def _uuid7() -> UUID:
    return UUID(str(uuid7()))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    order_updates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    marketing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stock_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    support_replies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    order_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages = relationship(
        "SupportTicketMessage",
        back_populates="ticket",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="SupportTicketMessage.created_at",
    )


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid7)
    ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket = relationship("SupportTicket", back_populates="messages")
