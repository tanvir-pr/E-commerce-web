"""ARQ jobs for cart maintenance."""

from typing import Any

import structlog

from app.cart.service import CartService
from app.session import SessionFactory

log = structlog.get_logger()


async def mark_abandoned_carts(_ctx: dict[str, Any]) -> dict[str, int]:
    async with SessionFactory() as session:
        count = await CartService(session).mark_abandoned()
        await session.commit()
    log.info("carts_marked_abandoned", count=count)
    return {"count": count}
