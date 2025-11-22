"""ARQ jobs for order maintenance and transactional emails."""

import asyncio
from email.message import EmailMessage
from typing import Any

import structlog

from app.config import get_settings
from app.mail.smtp import send_smtp
from app.orders.mailer import ArqOrderMailer
from app.orders.service import OrderService
from app.session import SessionFactory

log = structlog.get_logger()

_STATUS_LABELS: dict[str, str] = {
    "pending_payment": "Pending payment",
    "confirmed": "Confirmed",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "delivery_failed": "Delivery failed",
    "returned": "Returned",
    "cancelled": "Cancelled",
}


async def expire_stock_reservations(ctx: dict[str, Any]) -> dict[str, int]:
    mailer = ArqOrderMailer(ctx["redis"])
    async with SessionFactory() as session:
        count = await OrderService(session, mailer=mailer).expire_reservations()
        await session.commit()
    log.info("stock_reservations_expired", count=count)
    return {"count": count}


async def send_order_status_email(
    _ctx: dict[str, Any],
    email: str,
    order_id: str,
    order_number: str,
    status: str,
    courier_name: str | None = None,
    tracking_number: str | None = None,
) -> None:
    settings = get_settings()
    base = settings.public_web_url.rstrip("/")
    track_url = f"{base}/en/orders/{order_id}"
    label = _STATUS_LABELS.get(status, status.replace("_", " ").title())
    lines = [
        f"Solum order {order_number} is now: {label}.",
        "",
        f"Track your order: {track_url}",
        "",
    ]
    if courier_name or tracking_number:
        lines.append(f"Courier: {courier_name or '—'}")
        lines.append(f"Tracking: {tracking_number or '—'}")
        lines.append("")
    lines.append("Thank you for shopping with Solum.")
    message = EmailMessage()
    message["Subject"] = f"Solum order {order_number}: {label}"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content("\n".join(lines) + "\n")
    try:
        await asyncio.to_thread(send_smtp, message)
        log.info("order_status_email_sent", status=status, order_number=order_number)
    except Exception:
        log.error("order_status_email_failed", error_type="smtp", status=status)
        raise
