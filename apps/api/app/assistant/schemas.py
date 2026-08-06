"""Assistant API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AssistantAskIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    locale: str = Field(default="en", max_length=8)


class AssistantCitationOut(BaseModel):
    source: str
    title: str
    excerpt: str


class AssistantProductCardOut(BaseModel):
    id: UUID
    slug: str
    name: str
    subtitle: str | None = None
    from_price_poisha: int | None = None
    qty_available: int | None = None
    in_stock: bool = False
    routine_step: str | None = None
    concerns: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)


class AssistantAskOut(BaseModel):
    conversation_id: UUID
    message_id: UUID
    reply: str
    intent: str
    confidence: float
    handoff_suggested: bool
    citations: list[AssistantCitationOut] = Field(default_factory=list)
    products: list[AssistantProductCardOut] = Field(default_factory=list)


class AssistantHandoffIn(BaseModel):
    conversation_id: UUID
    note: str | None = Field(default=None, max_length=1000)


class AssistantHandoffOut(BaseModel):
    conversation_id: UUID
    ticket_id: UUID
    message: str


class AssistantMessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    intent: str | None = None
    confidence: float | None = None
    created_at: datetime


class AssistantConversationOut(BaseModel):
    id: UUID
    status: str
    ticket_id: UUID | None
    messages: list[AssistantMessageOut]
    created_at: datetime


class AssistantStatusOut(BaseModel):
    enabled: bool
