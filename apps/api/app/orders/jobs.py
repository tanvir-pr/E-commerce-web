"""ARQ jobs for order maintenance."""

from typing import Any

import structlog

from app.orders.service import OrderService
from app.session import SessionFactory

log = structlog.get_logger()


async def expire_stock_reservations(_ctx: dict[str, Any]) -> dict[str, int]:
    async with SessionFactory() as session:
        count = await OrderService(session).expire_reservations()
        await session.commit()
    log.info("stock_reservations_expired", count=count)
    return {"count": count}
