"""Rebuild the Meilisearch products index from Postgres.

Usage (api container):
  python -m app.scripts.reindex_search
"""

import asyncio

from app.search.indexer import SearchIndexer
from app.session import SessionFactory


async def main() -> None:
    async with SessionFactory() as session:
        result = await SearchIndexer(session).reindex_all()
        await session.commit()
    print(result.message)


if __name__ == "__main__":
    asyncio.run(main())
