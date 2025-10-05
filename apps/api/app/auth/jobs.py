"""ARQ jobs for auth emails."""

import asyncio
import smtplib
from email.message import EmailMessage
from typing import Any

import structlog

from app.config import get_settings

log = structlog.get_logger()


def _send_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        client.send_message(message)


async def send_verification_email(_ctx: dict[str, Any], email: str, token: str) -> None:
    settings = get_settings()
    base = settings.public_web_url.rstrip("/")
    verify_url = f"{base}/en/verify-email?token={token}"
    message = EmailMessage()
    message["Subject"] = "Verify your email"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "Confirm your email for the store.\n\n"
        f"Open this link: {verify_url}\n\n"
        "If you did not register, ignore this message.\n"
    )
    try:
        await asyncio.to_thread(_send_smtp, message)
        log.info("verification_email_sent")
    except Exception:
        log.error("verification_email_failed", error_type="smtp")
        raise


async def send_password_reset_email(_ctx: dict[str, Any], email: str, token: str) -> None:
    settings = get_settings()
    base = settings.public_web_url.rstrip("/")
    reset_url = f"{base}/en/reset-password?token={token}"
    message = EmailMessage()
    message["Subject"] = "Reset your password"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(
        "Reset your store password.\n\n"
        f"Open this link: {reset_url}\n\n"
        "If you did not request a reset, ignore this message.\n"
    )
    try:
        await asyncio.to_thread(_send_smtp, message)
        log.info("password_reset_email_sent")
    except Exception:
        log.error("password_reset_email_failed", error_type="smtp")
        raise
