"""Staff search index maintenance."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.search.indexer import SearchIndexer
from app.search.schemas import ReindexOut
from app.session import get_session

router = APIRouter(prefix="/admin/search", tags=["admin-search"])


def get_indexer(session: AsyncSession = Depends(get_session)) -> SearchIndexer:
    return SearchIndexer(session)


@router.post("/reindex", response_model=ReindexOut)
async def reindex_catalog(
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    indexer: SearchIndexer = Depends(get_indexer),
) -> ReindexOut:
    _ = actor_id
    return await indexer.reindex_all()
