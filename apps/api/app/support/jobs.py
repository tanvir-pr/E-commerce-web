"""ARQ jobs for support replies and stock-back alerts."""

import asyncio
from email.message import EmailMessage
from typing import Any

import structlog

from app.config import get_settings
from app.mail.smtp import send_smtp

log = structlog.get_logger()


async def send_support_reply_email(
    _ctx: dict[str, Any],
    email: str,
    ticket_id: str,
    subject: str,
    preview: str,
) -> None:
    settings = get_settings()
    base = settings.public_web_url.rstrip("/")
    url = f"{base}/en/account"
    message = EmailMessage()
    message["Subject"] = f"Solum support: {subject}"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                "You have a new reply on your Solum support ticket.",
                "",
                f"Subject: {subject}",
                f"Reply: {preview[:280]}",
                "",
                f"Open your account: {url}",
                f"Ticket id: {ticket_id}",
                "",
                "Thank you,",
                "Solum support",
            ]
        )
        + "\n"
    )
    try:
        await asyncio.to_thread(send_smtp, message)
        log.info("support_reply_email_sent", ticket_id=ticket_id)
    except Exception:
        log.error("support_reply_email_failed", error_type="smtp", ticket_id=ticket_id)
        raise


async def send_stock_back_email(
    _ctx: dict[str, Any],
    email: str,
    product_slug: str,
    product_name: str,
) -> None:
    settings = get_settings()
    base = settings.public_web_url.rstrip("/")
    url = f"{base}/en/p/{product_slug}"
    message = EmailMessage()
    message["Subject"] = f"Solum: {product_name} is back in stock"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"{product_name} from your wishlist is available again.",
                "",
                f"View product: {url}",
                "",
                "You can turn off these alerts in Account → Notifications.",
                "",
                "Solum",
            ]
        )
        + "\n"
    )
    try:
        await asyncio.to_thread(send_smtp, message)
        log.info("stock_back_email_sent", product_slug=product_slug)
    except Exception:
        log.error("stock_back_email_failed", error_type="smtp", product_slug=product_slug)
        raise
