"""RAG assistant: intent, grounded answers, handoff."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.assistant.compose import compose_reply
from app.assistant.retrieval import RetrievedChunk, classify_intent
from app.assistant.schemas import AssistantAskIn, AssistantHandoffIn
from app.assistant.service import AssistantService
from app.problems import PROBLEM_UNAVAILABLE, ProblemError


def test_classify_policy_and_product() -> None:
    assert classify_intent("What is your return policy for unopened items?") == "policy"
    assert classify_intent("Suggest a niacinamide serum for acne") == "ingredient"
    assert classify_intent("Help me build an AM routine") == "routine"
    assert classify_intent("Where is my order tracking?") == "order"


def test_compose_policy_reply() -> None:
    chunks = [
        RetrievedChunk(
            source="returns",
            title="Returns",
            body="Unopened products may be returned.",
            score=3.0,
        )
    ]
    reply, conf, handoff, citations, products = compose_reply(
        intent="policy",
        message="return policy",
        chunks=chunks,
        products=[],
    )
    assert "Unopened" in reply
    assert conf >= 0.55
    assert handoff is False
    assert citations[0].source == "returns"
    assert products == []


class FakeFlagRepo:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    async def get_by_key(self, key: str) -> SimpleNamespace | None:
        if key != "assistant_enabled":
            return None
        return SimpleNamespace(key=key, enabled=self.enabled, value=None)


class FakeFlags:
    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled

    async def is_enabled(self, key: str, *, default: bool = True) -> bool:
        if key == "assistant_enabled":
            return self._enabled
        return default


class FakeChunkRepo:
    def __init__(self) -> None:
        self.conversations: dict = {}
        self.messages: list = []
        self.chunks = [
            SimpleNamespace(
                source="returns",
                title="Returns and refunds",
                body="Unopened products in original packaging may be returned.",
                tags=["return", "refund"],
                locale="en",
                is_active=True,
            ),
            SimpleNamespace(
                source="routine",
                title="Building a simple routine",
                body="Cleanser then serum then moisturizer then sunscreen.",
                tags=["routine", "am"],
                locale="en",
                is_active=True,
            ),
        ]

    async def add_conversation(self, row: SimpleNamespace) -> SimpleNamespace:
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        row.messages = []
        row.status = getattr(row, "status", "open")
        row.ticket_id = getattr(row, "ticket_id", None)
        row.created_at = datetime.now(UTC)
        row.updated_at = datetime.now(UTC)
        self.conversations[row.id] = row
        return row

    async def add_message(self, row: SimpleNamespace) -> SimpleNamespace:
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        row.created_at = datetime.now(UTC)
        self.messages.append(row)
        conv = self.conversations.get(row.conversation_id)
        if conv is not None:
            conv.messages.append(row)
        return row

    async def get_conversation(self, conversation_id: object) -> SimpleNamespace | None:
        return self.conversations.get(conversation_id)

    async def require_conversation(self, conversation_id: object) -> SimpleNamespace:
        row = await self.get_conversation(conversation_id)
        assert row is not None
        return row

    async def save_conversation(self, row: SimpleNamespace) -> SimpleNamespace:
        self.conversations[row.id] = row
        return row

    async def list_active_chunks(self, *, locale: str = "en") -> list:
        return self.chunks

    async def search_products_sql(self, q: str, *, limit: int = 5) -> list:
        return []

    async def get_published_products(self, ids: list) -> list:
        return []

    async def qty_on_hand_for_product(self, _product_id: object) -> int:
        return 0

    async def min_price_poisha(self, _product_id: object) -> int | None:
        return None


class FakeSearch:
    async def search(self, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(items=[])


class FakeSupport:
    def __init__(self) -> None:
        self.created = None

    async def create_ticket(self, body: object, *, user_id: object) -> SimpleNamespace:
        self.created = (body, user_id)
        return SimpleNamespace(id=uuid4())


@pytest.mark.asyncio
async def test_ask_policy_persists_messages() -> None:
    service = AssistantService(session=SimpleNamespace())  # type: ignore[arg-type]
    service.repo = FakeChunkRepo()  # type: ignore[assignment]
    service.flags = FakeFlags(True)  # type: ignore[assignment]
    service.search = FakeSearch()  # type: ignore[assignment]
    out = await service.ask(
        AssistantAskIn(message="What is your return policy?"),
        user_id=None,
    )
    assert out.intent == "policy"
    assert out.confidence >= 0.5
    assert "Unopened" in out.reply
    assert len(service.repo.messages) == 2  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_ask_disabled_flag() -> None:
    service = AssistantService(session=SimpleNamespace())  # type: ignore[arg-type]
    service.repo = FakeChunkRepo()  # type: ignore[assignment]
    service.flags = FakeFlags(False)  # type: ignore[assignment]
    with pytest.raises(ProblemError) as exc:
        await service.ask(AssistantAskIn(message="hello"), user_id=None)
    assert exc.value.type_ == PROBLEM_UNAVAILABLE


@pytest.mark.asyncio
async def test_handoff_creates_ticket() -> None:
    service = AssistantService(session=SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeChunkRepo()
    service.repo = repo  # type: ignore[assignment]
    service.flags = FakeFlags(True)  # type: ignore[assignment]
    support = FakeSupport()
    service.support = support  # type: ignore[assignment]
    service.search = FakeSearch()  # type: ignore[assignment]

    asked = await service.ask(
        AssistantAskIn(message="Where is my order?"),
        user_id=uuid4(),
    )
    user_id = uuid4()
    # attach user to conversation for handoff ownership
    conv = await repo.require_conversation(asked.conversation_id)
    conv.user_id = user_id

    out = await service.handoff(
        AssistantHandoffIn(conversation_id=asked.conversation_id, note="Please help"),
        user_id=user_id,
    )
    assert out.ticket_id is not None
    assert support.created is not None
    assert conv.status == "handed_off"
