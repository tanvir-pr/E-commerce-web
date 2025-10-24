"""Keep the Meilisearch products index in sync with Postgres."""

from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.products.repository import ProductRepository
from app.search.client import MeilisearchClient, MeilisearchError
from app.search.documents import product_document
from app.search.schemas import ReindexOut

log = structlog.get_logger()


class SearchIndexer:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        client: MeilisearchClient | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.client = client or MeilisearchClient(self.settings)
        self.repo = ProductRepository(session)

    @property
    def enabled(self) -> bool:
        return self.settings.search_enabled

    async def ensure_ready(self) -> None:
        if not self.enabled:
            return
        await self.client.ensure_index()
        await self.client.configure_index()

    async def upsert_product(self, product_id: UUID) -> None:
        if not self.enabled:
            return
        try:
            row = await self.repo.get_by_id(product_id)
            if row is None:
                await self.client.delete_document(str(product_id))
                return
            document = product_document(row)
            if document is None:
                await self.client.delete_document(str(product_id))
                return
            await self.client.upsert_documents([document])
        except MeilisearchError as exc:
            log.error(
                "search_upsert_failed",
                product_id=str(product_id),
                error=str(exc),
                status=exc.status,
            )
        except Exception as exc:  # noqa: BLE001 — never break catalog writes
            log.error(
                "search_upsert_failed",
                product_id=str(product_id),
                error_type=type(exc).__name__,
            )

    async def remove_product(self, product_id: UUID) -> None:
        if not self.enabled:
            return
        try:
            await self.client.delete_document(str(product_id))
        except MeilisearchError as exc:
            log.error(
                "search_delete_failed",
                product_id=str(product_id),
                error=str(exc),
                status=exc.status,
            )
        except Exception as exc:  # noqa: BLE001
            log.error(
                "search_delete_failed",
                product_id=str(product_id),
                error_type=type(exc).__name__,
            )

    async def reindex_all(self) -> ReindexOut:
        if not self.enabled:
            return ReindexOut(
                indexed=0,
                removed=0,
                message="Search is disabled.",
            )
        await self.ensure_ready()
        await self.client.delete_all_documents()
        rows = await self.repo.list_products(public_only=True)
        documents = []
        for row in rows:
            document = product_document(row)
            if document is not None:
                documents.append(document)
        # Chunk to keep payloads modest.
        chunk_size = 200
        for start in range(0, len(documents), chunk_size):
            await self.client.upsert_documents(documents[start : start + chunk_size])
        return ReindexOut(
            indexed=len(documents),
            removed=0,
            message=f"Indexed {len(documents)} published products.",
        )
