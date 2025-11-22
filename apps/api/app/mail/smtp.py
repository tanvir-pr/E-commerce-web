"""SMTP send used by ARQ email jobs."""

import smtplib
from email.message import EmailMessage

from app.config import get_settings


def send_smtp(message: EmailMessage) -> None:
    settings = get_settings()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        client.send_message(message)
