"""Support and notification preference schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

TICKET_TOPICS = ("order", "product", "account", "other")
TICKET_STATUSES = ("open", "pending", "closed")


class NotificationPrefsOut(BaseModel):
    order_updates: bool
    marketing: bool
    stock_back: bool
    support_replies: bool


class NotificationPrefsIn(BaseModel):
    order_updates: bool | None = None
    marketing: bool | None = None
    stock_back: bool | None = None
    support_replies: bool | None = None


class TicketMessageIn(BaseModel):
    body: str = Field(min_length=2, max_length=5000)


class TicketMessageOut(BaseModel):
    id: UUID
    body: str
    is_staff: bool
    author_user_id: UUID | None
    created_at: datetime


class TicketCreateIn(BaseModel):
    topic: str = Field(pattern="^(order|product|account|other)$")
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=2, max_length=5000)
    order_id: UUID | None = None
    product_id: UUID | None = None


class TicketStatusIn(BaseModel):
    status: str = Field(pattern="^(open|pending|closed)$")
    note: str | None = Field(default=None, max_length=500)


class TicketSummaryOut(BaseModel):
    id: UUID
    topic: str
    subject: str
    status: str
    order_id: UUID | None
    product_id: UUID | None
    created_at: datetime
    updated_at: datetime
    user_email: str | None = None
    message_count: int = 0


class TicketOut(TicketSummaryOut):
    messages: list[TicketMessageOut] = Field(default_factory=list)


class TicketListOut(BaseModel):
    items: list[TicketSummaryOut]
