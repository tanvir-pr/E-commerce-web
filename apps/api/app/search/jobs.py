"""ARQ jobs for search index maintenance."""

from typing import Any
from uuid import UUID

import structlog

from app.search.indexer import SearchIndexer
from app.session import SessionFactory

log = structlog.get_logger()


async def reindex_catalog(_ctx: dict[str, Any]) -> dict[str, int | str]:
    async with SessionFactory() as session:
        indexer = SearchIndexer(session)
        result = await indexer.reindex_all()
        await session.commit()
    log.info("search_reindex_done", indexed=result.indexed)
    return {"indexed": result.indexed, "message": result.message}


async def sync_product(_ctx: dict[str, Any], product_id: str) -> None:
    async with SessionFactory() as session:
        indexer = SearchIndexer(session)
        await indexer.upsert_product(UUID(product_id))
        await session.commit()
