"""Resolve payment gateway adapters from settings."""

from app.config import Settings
from app.payments.adapters.bkash import SandboxBkashGateway
from app.payments.adapters.sslcommerz import SandboxSslcommerzGateway
from app.payments.protocol import PaymentGateway
from app.problems import PROBLEM_VALIDATION, ProblemError

GATEWAY_METHODS = frozenset({"bkash", "sslcommerz"})


def get_gateway(method: str, settings: Settings) -> PaymentGateway:
    key = method.strip().lower()
    if key not in GATEWAY_METHODS:
        raise ProblemError(
            422,
            "Validation error",
            f"Payment method must be one of: {', '.join(sorted(GATEWAY_METHODS))}",
            PROBLEM_VALIDATION,
        )
    if key == "bkash":
        return SandboxBkashGateway(settings)
    return SandboxSslcommerzGateway(settings)
