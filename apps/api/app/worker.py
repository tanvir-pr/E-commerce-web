"""ARQ worker. Command: arq app.worker.WorkerSettings"""

import logging
from typing import Any

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.auth.jobs import send_password_reset_email, send_verification_email
from app.cart.jobs import mark_abandoned_carts
from app.config import get_settings
from app.logging_config import setup_logging
from app.orders.jobs import expire_stock_reservations, send_order_status_email
from app.payments.jobs import reconcile_late_payments
from app.search.jobs import reindex_catalog, sync_product

setup_logging()
logging.getLogger("arq").setLevel(logging.WARNING)
log = structlog.get_logger()


async def startup(_ctx: dict[str, Any]) -> None:
    structlog.contextvars.bind_contextvars(request_id="worker")
    log.info("worker_started")


async def shutdown(_ctx: dict[str, Any]) -> None:
    log.info("worker_stopped")


_RESERVATION_CRON_MINUTES = set(range(0, 60, 5))


class WorkerSettings:
    functions = [
        send_verification_email,
        send_password_reset_email,
        reindex_catalog,
        sync_product,
        mark_abandoned_carts,
        expire_stock_reservations,
        send_order_status_email,
        reconcile_late_payments,
    ]
    cron_jobs = [
        cron(mark_abandoned_carts, hour={0, 6, 12, 18}, minute=15),  # type: ignore[arg-type]
        cron(expire_stock_reservations, minute=_RESERVATION_CRON_MINUTES),
        cron(reconcile_late_payments, hour={2}, minute=20),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
