"""ARQ jobs for payment reconciliation."""

from typing import Any

import structlog

from app.orders.mailer import ArqOrderMailer
from app.payments.service import PaymentService
from app.session import SessionFactory

log = structlog.get_logger()


async def reconcile_late_payments(ctx: dict[str, Any]) -> dict[str, int]:
    mailer = ArqOrderMailer(ctx["redis"])
    async with SessionFactory() as session:
        result = await PaymentService(session, mailer=mailer).reconcile_late_payments()
        await session.commit()
    log.info(
        "late_payments_reconciled",
        refunded=result["refunded"],
        revived=result["revived"],
        scanned=result["scanned"],
    )
    return result
