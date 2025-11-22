"""Enqueue order status emails via ARQ."""

from typing import Any, Protocol


class OrderMailer(Protocol):
    async def send_order_status(
        self,
        *,
        email: str,
        order_id: str,
        order_number: str,
        status: str,
        courier_name: str | None = None,
        tracking_number: str | None = None,
    ) -> None: ...


class ArqOrderMailer:
    def __init__(self, arq: Any) -> None:
        self.arq = arq

    async def send_order_status(
        self,
        *,
        email: str,
        order_id: str,
        order_number: str,
        status: str,
        courier_name: str | None = None,
        tracking_number: str | None = None,
    ) -> None:
        await self.arq.enqueue_job(
            "send_order_status_email",
            email,
            order_id,
            order_number,
            status,
            courier_name,
            tracking_number,
        )


class NullOrderMailer:
    async def send_order_status(
        self,
        *,
        email: str,
        order_id: str,
        order_number: str,
        status: str,
        courier_name: str | None = None,
        tracking_number: str | None = None,
    ) -> None:
        _ = (email, order_id, order_number, status, courier_name, tracking_number)
