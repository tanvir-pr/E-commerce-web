"""Assistant persistence."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assistant import AssistantConversation, AssistantMessage, KnowledgeChunk
from app.models.inventory import StockBatch
from app.models.product import Product, ProductVariant
from app.problems import PROBLEM_NOT_FOUND, ProblemError


class AssistantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_conversation(self, row: AssistantConversation) -> AssistantConversation:
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_message(self, row: AssistantMessage) -> AssistantMessage:
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_conversation(self, conversation_id: UUID) -> AssistantConversation | None:
        result = await self.session.execute(
            select(AssistantConversation)
            .where(AssistantConversation.id == conversation_id)
            .options(selectinload(AssistantConversation.messages))
        )
        return result.scalar_one_or_none()

    async def require_conversation(self, conversation_id: UUID) -> AssistantConversation:
        row = await self.get_conversation(conversation_id)
        if row is None:
            raise ProblemError(
                404, "Not found", "Conversation not found.", PROBLEM_NOT_FOUND
            )
        return row

    async def save_conversation(self, row: AssistantConversation) -> AssistantConversation:
        await self.session.flush()
        return row

    async def list_active_chunks(self, *, locale: str = "en") -> list[KnowledgeChunk]:
        result = await self.session.execute(
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.is_active.is_(True),
                or_(KnowledgeChunk.locale == locale, KnowledgeChunk.locale == "en"),
            )
            .order_by(KnowledgeChunk.source.asc())
        )
        return list(result.scalars().all())

    async def search_products_sql(self, q: str, *, limit: int = 5) -> list[Product]:
        term = f"%{q.strip()}%"
        if len(q.strip()) < 2:
            return []
        result = await self.session.execute(
            select(Product)
            .where(
                Product.status == "published",
                Product.deleted_at.is_(None),
                or_(
                    Product.name.ilike(term),
                    Product.subtitle.ilike(term),
                    Product.description.ilike(term),
                    Product.ingredients_text.ilike(term),
                    Product.how_to_use.ilike(term),
                ),
            )
            .order_by(Product.name.asc())
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def get_published_products(self, ids: list[UUID]) -> list[Product]:
        if not ids:
            return []
        result = await self.session.execute(
            select(Product).where(
                Product.id.in_(ids),
                Product.status == "published",
                Product.deleted_at.is_(None),
            )
        )
        by_id = {p.id: p for p in result.scalars().unique().all()}
        return [by_id[i] for i in ids if i in by_id]

    async def qty_on_hand_for_product(self, product_id: UUID) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(StockBatch.qty_on_hand), 0))
            .select_from(StockBatch)
            .join(ProductVariant, ProductVariant.id == StockBatch.variant_id)
            .where(ProductVariant.product_id == product_id)
        )
        return int(result.scalar_one() or 0)

    async def min_price_poisha(self, product_id: UUID) -> int | None:
        result = await self.session.execute(
            select(func.min(ProductVariant.price_poisha)).where(
                ProductVariant.product_id == product_id,
                ProductVariant.is_active.is_(True),
            )
        )
        value = result.scalar_one_or_none()
        return int(value) if value is not None else None
