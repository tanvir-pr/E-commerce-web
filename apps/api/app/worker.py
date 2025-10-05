"""ARQ worker. Command: arq app.worker.WorkerSettings"""

import logging
from typing import Any

import structlog
from arq.connections import RedisSettings

from app.auth.jobs import send_password_reset_email, send_verification_email
from app.config import get_settings
from app.logging_config import setup_logging

setup_logging()
logging.getLogger("arq").setLevel(logging.WARNING)
log = structlog.get_logger()


async def startup(_ctx: dict[str, Any]) -> None:
    structlog.contextvars.bind_contextvars(request_id="worker")
    log.info("worker_started")


async def shutdown(_ctx: dict[str, Any]) -> None:
    log.info("worker_stopped")


class WorkerSettings:
    functions = [send_verification_email, send_password_reset_email]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
