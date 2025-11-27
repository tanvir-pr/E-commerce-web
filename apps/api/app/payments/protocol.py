"""Payment gateway Protocol and shared result types."""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True)
class InitiateResult:
    redirect_url: str
    provider_ref: str


@dataclass(frozen=True)
class ValidateResult:
    ok: bool
    order_id: UUID
    provider_ref: str
    amount_poisha: int
    reason: str | None = None


class PaymentGateway(Protocol):
    method: str

    def initiate(
        self,
        *,
        order_id: UUID,
        order_number: str,
        amount_poisha: int,
        currency: str,
        return_url: str,
        cancel_url: str,
    ) -> InitiateResult: ...

    def validate(self, payload: dict[str, Any]) -> ValidateResult: ...
