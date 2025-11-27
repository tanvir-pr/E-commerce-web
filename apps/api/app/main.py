"""FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from arq.connections import RedisSettings, create_pool
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis.asyncio import Redis

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.cart.admin_router import router as carts_admin_router
from app.cart.router import router as cart_router
from app.catalog.admin_router import router as catalog_admin_router
from app.catalog.router import router as catalog_router
from app.checkout.router import router as checkout_router
from app.config import get_settings
from app.health import router as health_router
from app.inventory.router import router as inventory_admin_router
from app.logging_config import current_request_id, setup_logging
from app.media.router import router as media_admin_router
from app.middleware import CSRFMiddleware, RequestContextMiddleware
from app.orders.admin_router import router as orders_admin_router
from app.orders.router import router as orders_router
from app.payments.router import router as payments_router
from app.problems import PROBLEM_INTERNAL, PROBLEM_VALIDATION, ProblemError, problem_payload
from app.products.admin_router import router as products_admin_router
from app.products.router import router as products_router
from app.search.admin_router import router as search_admin_router
from app.search.client import MeilisearchClient
from app.search.router import router as search_router
from app.session import engine
from app.shipping.admin_router import router as shipping_admin_router
from app.shipping.router import router as shipping_router
from app.users.router import router as users_router

setup_logging()
log = structlog.get_logger()


def _validation_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for item in exc.errors():
        loc = item.get("loc", [])
        parts = [str(part) for part in loc if part not in {"body", "query", "path"}]
        field = ".".join(parts) if parts else "request"
        errors.append({"field": field, "message": str(item.get("msg", "Invalid value"))})
    return errors


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        if settings.search_enabled:
            try:
                client = MeilisearchClient(settings)
                await client.ensure_index()
                await client.configure_index()
                log.info("search_index_ready", index=settings.meilisearch_index)
            except Exception as exc:  # noqa: BLE001 — boot without blocking catalog
                log.error("search_index_setup_failed", error_type=type(exc).__name__)
        log.info("app_started", app_env=settings.app_env)
        yield
        await app.state.arq.close()
        await app.state.redis.aclose()
        await engine.dispose()

    app = FastAPI(title="Store API", version="0.23.0", lifespan=lifespan)

    @app.exception_handler(ProblemError)
    async def handle_problem(_request: Request, exc: ProblemError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=problem_payload(exc, current_request_id()),
            media_type="application/problem+json",
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        problem = ProblemError(
            422,
            "Validation error",
            "One or more fields are invalid.",
            PROBLEM_VALIDATION,
            errors=_validation_errors(exc),
        )
        return JSONResponse(
            status_code=422,
            content=problem_payload(problem, current_request_id()),
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_error", error_type=type(exc).__name__)
        problem = ProblemError(
            500,
            "Internal Server Error",
            "Something went wrong.",
            PROBLEM_INTERNAL,
        )
        return JSONResponse(
            status_code=500,
            content=problem_payload(problem, current_request_id()),
            media_type="application/problem+json",
        )

    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
    )

    media_root = Path(settings.media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.media_url_path.rstrip("/") or "/api/v1/media",
        StaticFiles(directory=str(media_root)),
        name="media",
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(catalog_router, prefix="/api/v1")
    app.include_router(products_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(cart_router, prefix="/api/v1")
    app.include_router(shipping_router, prefix="/api/v1")
    app.include_router(checkout_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(payments_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(catalog_admin_router, prefix="/api/v1")
    app.include_router(products_admin_router, prefix="/api/v1")
    app.include_router(media_admin_router, prefix="/api/v1")
    app.include_router(inventory_admin_router, prefix="/api/v1")
    app.include_router(search_admin_router, prefix="/api/v1")
    app.include_router(carts_admin_router, prefix="/api/v1")
    app.include_router(shipping_admin_router, prefix="/api/v1")
    app.include_router(orders_admin_router, prefix="/api/v1")
    return app


app = create_app()
