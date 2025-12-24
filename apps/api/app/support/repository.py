"""Support ticket and notification preference persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.models.review import WishlistItem
from app.models.support import NotificationPreference, SupportTicket, SupportTicketMessage
from app.models.user import User
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class SupportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_prefs(self, user_id: UUID) -> NotificationPreference | None:
        result = await self.session.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_prefs(self, row: NotificationPreference) -> NotificationPreference:
        self.session.add(row)
        await self.session.flush()
        return row

    async def save_prefs(self, row: NotificationPreference) -> NotificationPreference:
        await self.session.flush()
        return row

    async def add_ticket(self, row: SupportTicket) -> SupportTicket:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_message(self, row: SupportTicketMessage) -> SupportTicketMessage:
        self.session.add(row)
        await self.session.flush()
        return row

    async def save_ticket(self, row: SupportTicket) -> SupportTicket:
        await self.session.flush()
        return row

    async def get_ticket(self, ticket_id: UUID) -> SupportTicket | None:
        result = await self.session.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .where(SupportTicket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def require_ticket(self, ticket_id: UUID) -> SupportTicket:
        row = await self.get_ticket(ticket_id)
        if row is None:
            raise ProblemError(404, "Not found", "Ticket not found.", PROBLEM_NOT_FOUND)
        return row

    async def list_for_user(self, user_id: UUID) -> list[SupportTicket]:
        result = await self.session.execute(
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .where(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.updated_at.desc())
            .limit(100)
        )
        return list(result.scalars().all())

    async def list_admin(self, *, status: str | None = None) -> list[SupportTicket]:
        stmt = (
            select(SupportTicket)
            .options(selectinload(SupportTicket.messages))
            .order_by(SupportTicket.updated_at.desc())
            .limit(200)
        )
        if status and status != "all":
            stmt = stmt.where(SupportTicket.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def user_emails(self, user_ids: list[UUID]) -> dict[UUID, str]:
        if not user_ids:
            return {}
        result = await self.session.execute(
            select(User.id, User.email).where(User.id.in_(user_ids))
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_user(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_product(self, product_id: UUID) -> Product | None:
        result = await self.session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()

    async def wishlisters_for_stock_back(
        self, product_id: UUID
    ) -> list[tuple[UUID, str, str]]:
        """Return (user_id, email, product_slug) for users wanting stock-back mail."""
        result = await self.session.execute(
            select(User.id, User.email, Product.slug)
            .join(WishlistItem, WishlistItem.user_id == User.id)
            .join(Product, Product.id == WishlistItem.product_id)
            .outerjoin(
                NotificationPreference,
                NotificationPreference.user_id == User.id,
            )
            .where(
                WishlistItem.product_id == product_id,
                User.deleted_at.is_(None),
                (NotificationPreference.stock_back.is_(True))
                | (NotificationPreference.user_id.is_(None)),
            )
        )
        return [(row[0], row[1], row[2]) for row in result.all()]
