"""Support tickets, prefs, and stock-back notify."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.problems import PROBLEM_VALIDATION, ProblemError
from app.support.schemas import (
    NotificationPrefsIn,
    TicketCreateIn,
    TicketMessageIn,
    TicketStatusIn,
)
from app.support.service import SupportService


class FakeRepo:
    def __init__(self) -> None:
        self.prefs: dict[object, SimpleNamespace] = {}
        self.tickets: list[SimpleNamespace] = []
        self.product = SimpleNamespace(id=uuid4(), name="Serum", slug="serum")
        self.users: dict[object, SimpleNamespace] = {}

    async def get_prefs(self, user_id: object) -> SimpleNamespace | None:
        return self.prefs.get(user_id)

    async def add_prefs(self, row: SimpleNamespace) -> SimpleNamespace:
        self.prefs[row.user_id] = row
        return row

    async def save_prefs(self, row: SimpleNamespace) -> SimpleNamespace:
        self.prefs[row.user_id] = row
        return row

    async def add_ticket(self, row: SimpleNamespace) -> SimpleNamespace:
        if not getattr(row, "id", None):
            row.id = uuid4()
        now = datetime.now(UTC)
        row.created_at = now
        row.updated_at = now
        row.closed_at = None
        row.messages = []
        self.tickets.append(row)
        return row

    async def add_message(self, row: SimpleNamespace) -> SimpleNamespace:
        if not getattr(row, "id", None):
            row.id = uuid4()
        row.created_at = datetime.now(UTC)
        for ticket in self.tickets:
            if ticket.id == row.ticket_id:
                ticket.messages.append(row)
                break
        return row

    async def save_ticket(self, row: SimpleNamespace) -> SimpleNamespace:
        return row

    async def get_ticket(self, ticket_id: object) -> SimpleNamespace | None:
        for ticket in self.tickets:
            if ticket.id == ticket_id:
                return ticket
        return None

    async def require_ticket(self, ticket_id: object) -> SimpleNamespace:
        row = await self.get_ticket(ticket_id)
        assert row is not None
        return row

    async def list_for_user(self, user_id: object) -> list[SimpleNamespace]:
        return [t for t in self.tickets if t.user_id == user_id]

    async def list_admin(self, *, status: str | None = None) -> list[SimpleNamespace]:
        rows = self.tickets
        if status:
            rows = [t for t in rows if t.status == status]
        return rows

    async def user_emails(self, user_ids: list[object]) -> dict[object, str]:
        return {
            uid: self.users.get(uid, SimpleNamespace(email="x@example.com")).email
            for uid in user_ids
        }

    async def get_user(self, user_id: object) -> SimpleNamespace | None:
        return self.users.get(user_id)

    async def get_product(self, product_id: object) -> SimpleNamespace | None:
        return self.product if product_id == self.product.id else None

    async def wishlisters_for_stock_back(
        self, product_id: object
    ) -> list[tuple[object, str, str]]:
        _ = product_id
        return [(uuid4(), "wish@example.com", "serum")]


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


class FakeMailer:
    def __init__(self) -> None:
        self.replies: list[dict[str, str]] = []
        self.stock: list[dict[str, str]] = []

    async def send_support_reply(self, **kwargs: str) -> None:
        self.replies.append(dict(kwargs))

    async def send_stock_back(self, **kwargs: str) -> None:
        self.stock.append(dict(kwargs))


def _service() -> tuple[SupportService, FakeRepo, FakeMailer]:
    service = SupportService(session=SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeRepo()
    mailer = FakeMailer()
    service.repo = repo  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    service.mailer = mailer  # type: ignore[assignment]
    return service, repo, mailer


@pytest.mark.asyncio
async def test_prefs_default_then_update() -> None:
    service, _repo, _mailer = _service()
    user_id = uuid4()
    prefs = await service.get_prefs(user_id)
    assert prefs.order_updates is True
    assert prefs.marketing is False
    updated = await service.update_prefs(
        user_id, NotificationPrefsIn(marketing=True, stock_back=False)
    )
    assert updated.marketing is True
    assert updated.stock_back is False


@pytest.mark.asyncio
async def test_create_order_ticket_requires_order_id() -> None:
    service, _repo, _mailer = _service()
    with pytest.raises(ProblemError) as exc:
        await service.create_ticket(
            TicketCreateIn(
                topic="order",
                subject="Where is my parcel?",
                body="Still waiting after two days.",
            ),
            user_id=uuid4(),
        )
    assert exc.value.type_ == PROBLEM_VALIDATION


@pytest.mark.asyncio
async def test_create_and_staff_reply_emails() -> None:
    service, repo, mailer = _service()
    user_id = uuid4()
    repo.users[user_id] = SimpleNamespace(email="buyer@example.com")
    ticket = await service.create_ticket(
        TicketCreateIn(
            topic="account",
            subject="Change email",
            body="Please help update my email.",
        ),
        user_id=user_id,
    )
    assert ticket.status == "open"
    assert len(ticket.messages) == 1
    replied = await service.admin_reply(
        ticket.id,
        TicketMessageIn(body="We can update that for you."),
        actor_user_id=uuid4(),
    )
    assert replied.status == "pending"
    assert len(mailer.replies) == 1
    closed = await service.admin_set_status(
        ticket.id,
        TicketStatusIn(status="closed"),
        actor_user_id=uuid4(),
    )
    assert closed.status == "closed"


@pytest.mark.asyncio
async def test_stock_back_notify() -> None:
    service, repo, mailer = _service()
    count = await service.notify_stock_back(repo.product.id)
    assert count == 1
    assert mailer.stock[0]["product_slug"] == "serum"
