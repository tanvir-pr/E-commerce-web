"""Assistant orchestration: retrieve → ground → persist → handoff."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.compose import compose_reply
from app.assistant.repository import AssistantRepository
from app.assistant.retrieval import classify_intent, retrieve_policy, retrieve_products
from app.assistant.schemas import (
    AssistantAskIn,
    AssistantAskOut,
    AssistantConversationOut,
    AssistantHandoffIn,
    AssistantHandoffOut,
    AssistantMessageOut,
    AssistantStatusOut,
)
from app.flags.service import FeatureFlagService
from app.models.assistant import AssistantConversation, AssistantMessage
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_UNAVAILABLE, PROBLEM_VALIDATION, ProblemError
from app.search.service import SearchService
from app.support.schemas import TicketCreateIn
from app.support.service import SupportService


class AssistantService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        search: SearchService | None = None,
        flags: FeatureFlagService | None = None,
        support: SupportService | None = None,
    ) -> None:
        self.session = session
        self.repo = AssistantRepository(session)
        self.search = search or SearchService()
        self.flags = flags or FeatureFlagService(session)
        self.support = support or SupportService(session)

    async def status(self) -> AssistantStatusOut:
        enabled = await self.flags.is_enabled("assistant_enabled", default=True)
        return AssistantStatusOut(enabled=enabled)

    async def ask(
        self, body: AssistantAskIn, *, user_id: UUID | None
    ) -> AssistantAskOut:
        await self._require_enabled()
        text = body.message.strip()
        if not text:
            raise ProblemError(
                422, "Validation error", "message is required.", PROBLEM_VALIDATION
            )

        conversation = await self._get_or_create(
            body.conversation_id, user_id=user_id, locale=body.locale
        )
        await self.repo.add_message(
            AssistantMessage(
                conversation_id=conversation.id,
                role="user",
                content=text,
            )
        )

        intent = classify_intent(text)
        chunks = await retrieve_policy(self.repo, text, locale=body.locale)
        product_hits = []
        if intent in {"product", "routine", "ingredient", "unknown"}:
            product_hits = await retrieve_products(self.repo, self.search, text)

        enriched = []
        for hit in product_hits:
            price = await self.repo.min_price_poisha(hit.product.id)
            qty = await self.repo.qty_on_hand_for_product(hit.product.id)
            enriched.append((hit, price, qty))

        # Always pull a matching policy chunk for routine/ingredient framing.
        if intent in {"routine", "ingredient"} and not any(
            c.source in {"routine", "ingredients"} for c in chunks
        ):
            extra = await retrieve_policy(
                self.repo,
                "routine ingredients" if intent == "routine" else "ingredients",
                locale=body.locale,
                limit=2,
            )
            chunks = (chunks + extra)[:3]

        reply, confidence, handoff, citations, cards = compose_reply(
            intent=intent,
            message=text,
            chunks=chunks,
            products=enriched,
        )

        assistant_msg = await self.repo.add_message(
            AssistantMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=reply,
                intent=intent,
                confidence=confidence,
                citations=[c.model_dump() for c in citations],
                product_ids=[str(c.id) for c in cards],
            )
        )
        conversation.updated_at = datetime.now(UTC)
        if user_id and conversation.user_id is None:
            conversation.user_id = user_id
        await self.repo.save_conversation(conversation)

        return AssistantAskOut(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            reply=reply,
            intent=intent,
            confidence=confidence,
            handoff_suggested=handoff or confidence < 0.45,
            citations=citations,
            products=cards,
        )

    async def handoff(
        self, body: AssistantHandoffIn, *, user_id: UUID
    ) -> AssistantHandoffOut:
        await self._require_enabled()
        conversation = await self.repo.require_conversation(body.conversation_id)
        if conversation.user_id and conversation.user_id != user_id:
            raise ProblemError(
                403, "Forbidden", "This conversation belongs to another user.", PROBLEM_FORBIDDEN
            )
        if conversation.ticket_id is not None:
            return AssistantHandoffOut(
                conversation_id=conversation.id,
                ticket_id=conversation.ticket_id,
                message="Already handed off to support.",
            )

        transcript = self._transcript(conversation)
        note = (body.note or "").strip()
        subject = "Assistant handoff"
        last_user = next(
            (m.content for m in reversed(conversation.messages) if m.role == "user"),
            "Chat handoff",
        )
        if last_user:
            subject = f"Assistant: {last_user[:80]}"
        body_text = transcript
        if note:
            body_text = f"{note}\n\n---\n{transcript}"

        ticket = await self.support.create_ticket(
            TicketCreateIn(
                topic="other",
                subject=subject,
                body=body_text[:8000],
            ),
            user_id=user_id,
        )
        conversation.ticket_id = ticket.id
        conversation.status = "handed_off"
        conversation.user_id = user_id
        conversation.updated_at = datetime.now(UTC)
        await self.repo.save_conversation(conversation)
        await self.repo.add_message(
            AssistantMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=(
                    "I’ve opened a support ticket for you. Our team will reply in your "
                    "Account → Support messages."
                ),
                intent="handoff",
                confidence=1.0,
            )
        )
        return AssistantHandoffOut(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            message="Support ticket created.",
        )

    async def get_conversation(
        self, conversation_id: UUID, *, user_id: UUID | None
    ) -> AssistantConversationOut:
        await self._require_enabled()
        conversation = await self.repo.require_conversation(conversation_id)
        if (
            conversation.user_id is not None
            and user_id is not None
            and conversation.user_id != user_id
        ):
            raise ProblemError(
                403, "Forbidden", "This conversation belongs to another user.", PROBLEM_FORBIDDEN
            )
        return AssistantConversationOut(
            id=conversation.id,
            status=conversation.status,
            ticket_id=conversation.ticket_id,
            created_at=conversation.created_at,
            messages=[
                AssistantMessageOut(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    intent=m.intent,
                    confidence=m.confidence,
                    created_at=m.created_at,
                )
                for m in conversation.messages
            ],
        )

    async def _require_enabled(self) -> None:
        if not await self.flags.is_enabled("assistant_enabled", default=True):
            raise ProblemError(
                503,
                "Unavailable",
                "The shopping assistant is temporarily disabled.",
                PROBLEM_UNAVAILABLE,
            )

    async def _get_or_create(
        self,
        conversation_id: UUID | None,
        *,
        user_id: UUID | None,
        locale: str,
    ) -> AssistantConversation:
        if conversation_id is not None:
            conversation = await self.repo.require_conversation(conversation_id)
            if conversation.status == "handed_off":
                raise ProblemError(
                    422,
                    "Validation error",
                    "This conversation was handed off to support. Start a new chat.",
                    PROBLEM_VALIDATION,
                )
            if conversation.user_id and user_id and conversation.user_id != user_id:
                raise ProblemError(
                    403,
                    "Forbidden",
                    "This conversation belongs to another user.",
                    PROBLEM_FORBIDDEN,
                )
            return conversation
        conversation = AssistantConversation(user_id=user_id, locale=locale or "en")
        return await self.repo.add_conversation(conversation)

    def _transcript(self, conversation: AssistantConversation) -> str:
        lines: list[str] = []
        for m in conversation.messages:
            label = "Customer" if m.role == "user" else "Assistant"
            lines.append(f"{label}: {m.content}")
        return "\n\n".join(lines) if lines else "(empty conversation)"
