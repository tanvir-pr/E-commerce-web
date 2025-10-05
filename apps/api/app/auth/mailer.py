"""Enqueue auth emails via ARQ."""

from typing import Any, Protocol


class Mailer(Protocol):
    async def send_verification(self, *, email: str, token: str) -> None: ...

    async def send_password_reset(self, *, email: str, token: str) -> None: ...


class ArqMailer:
    def __init__(self, arq: Any) -> None:
        self.arq = arq

    async def send_verification(self, *, email: str, token: str) -> None:
        await self.arq.enqueue_job("send_verification_email", email, token)

    async def send_password_reset(self, *, email: str, token: str) -> None:
        await self.arq.enqueue_job("send_password_reset_email", email, token)


class NullMailer:
    async def send_verification(self, *, email: str, token: str) -> None:
        _ = (email, token)

    async def send_password_reset(self, *, email: str, token: str) -> None:
        _ = (email, token)
