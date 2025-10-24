"""Liveness of Postgres, Redis, and Meilisearch."""

from typing import Literal

import structlog
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_redis
from app.search.client import MeilisearchClient
from app.session import get_session

router = APIRouter(tags=["health"])
log = structlog.get_logger()


class HealthOut(BaseModel):
    status: Literal["ok", "down"]
    db: Literal["ok", "down"]
    redis: Literal["ok", "down"]
    search: Literal["ok", "down", "disabled"]


async def probe_health(session: AsyncSession, redis: Redis) -> HealthOut:
    db: Literal["ok", "down"] = "ok"
    cache: Literal["ok", "down"] = "ok"
    search: Literal["ok", "down", "disabled"] = "disabled"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        log.error("health_db_failed")
        db = "down"
    try:
        await redis.ping()
    except Exception:
        log.error("health_redis_failed")
        cache = "down"
    settings = get_settings()
    if settings.search_enabled:
        search = "ok" if await MeilisearchClient(settings).health() else "down"
        if search == "down":
            log.error("health_search_failed")
    # Core liveness is still db + redis; search is reported but non-blocking.
    status: Literal["ok", "down"] = "ok" if db == "ok" and cache == "ok" else "down"
    return HealthOut(status=status, db=db, redis=cache, search=search)


@router.get("/health", response_model=HealthOut)
async def health(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    result = await probe_health(session, redis)
    if result.db == "down":
        await session.rollback()
    return JSONResponse(
        status_code=200 if result.status == "ok" else 503,
        content=result.model_dump(),
    )
