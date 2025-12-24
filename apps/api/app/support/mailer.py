"""Enqueue support and stock-back emails via ARQ."""

from typing import Any, Protocol


class SupportMailer(Protocol):
    async def send_support_reply(
        self,
        *,
        email: str,
        ticket_id: str,
        subject: str,
        preview: str,
    ) -> None: ...

    async def send_stock_back(
        self,
        *,
        email: str,
        product_slug: str,
        product_name: str,
    ) -> None: ...


class ArqSupportMailer:
    def __init__(self, arq: Any) -> None:
        self.arq = arq

    async def send_support_reply(
        self,
        *,
        email: str,
        ticket_id: str,
        subject: str,
        preview: str,
    ) -> None:
        await self.arq.enqueue_job(
            "send_support_reply_email",
            email,
            ticket_id,
            subject,
            preview,
        )

    async def send_stock_back(
        self,
        *,
        email: str,
        product_slug: str,
        product_name: str,
    ) -> None:
        await self.arq.enqueue_job(
            "send_stock_back_email",
            email,
            product_slug,
            product_name,
        )


class NullSupportMailer:
    async def send_support_reply(
        self,
        *,
        email: str,
        ticket_id: str,
        subject: str,
        preview: str,
    ) -> None:
        _ = (email, ticket_id, subject, preview)

    async def send_stock_back(
        self,
        *,
        email: str,
        product_slug: str,
        product_name: str,
    ) -> None:
        _ = (email, product_slug, product_name)
