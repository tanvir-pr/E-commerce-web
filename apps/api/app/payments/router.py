"""Customer payment routes — pay start, validate, session-less return, webhooks."""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user_id
from app.orders.mailer import ArqOrderMailer
from app.payments.schemas import PayStartOut, PayValidateIn, PayValidateOut
from app.payments.service import PaymentService
from app.session import get_session

router = APIRouter(tags=["payments"])


def get_payment_service(
    request: Request, session: AsyncSession = Depends(get_session)
) -> PaymentService:
    return PaymentService(session, mailer=ArqOrderMailer(request.app.state.arq))


@router.post("/orders/{order_id}/pay", response_model=PayStartOut)
async def start_order_payment(
    order_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> PayStartOut:
    return await service.start_pay(order_id, user_id=user_id)


@router.post("/payments/{method}/validate", response_model=PayValidateOut)
async def validate_payment(
    method: str,
    body: PayValidateIn,
    user_id: UUID = Depends(get_current_user_id),
    service: PaymentService = Depends(get_payment_service),
) -> PayValidateOut:
    payload: dict[str, Any] = body.model_dump(exclude_none=True)
    return await service.validate_owned_or_forbidden(
        method, payload, user_id=user_id
    )


@router.get("/payments/{method}/return")
async def payment_return_get(
    method: str,
    request: Request,
    service: PaymentService = Depends(get_payment_service),
    locale: str = Query(default="en"),
) -> RedirectResponse:
    """Session-less browser return — no auth cookie required; then 303 to order."""
    payload = {k: v for k, v in request.query_params.items() if k != "locale"}
    out = await service.process_return(method, payload)
    base = service.settings.public_web_url.rstrip("/")
    loc = (locale or "en").strip() or "en"
    return RedirectResponse(
        url=f"{base}/{loc}/orders/{out.order_id}",
        status_code=303,
    )


@router.post("/payments/{method}/return")
async def payment_return_post(
    method: str,
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> RedirectResponse:
    """Session-less form POST return from hosted gateway; 303 to order."""
    content_type = request.headers.get("content-type", "")
    payload: dict[str, Any]
    if "application/json" in content_type:
        body = await request.json()
        payload = body if isinstance(body, dict) else {}
    else:
        form = await request.form()
        payload = {str(k): str(v) for k, v in form.items()}
    locale = str(payload.pop("locale", "en") or "en")
    out = await service.process_return(method, payload)
    base = service.settings.public_web_url.rstrip("/")
    return RedirectResponse(
        url=f"{base}/{locale}/orders/{out.order_id}",
        status_code=303,
    )


@router.post("/payments/{method}/webhook", response_model=PayValidateOut)
async def payment_webhook(
    method: str,
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> PayValidateOut:
    """Signed gateway webhook — CSRF exempt, processed once per gateway_event_id."""
    body = await request.body()
    signature = request.headers.get("x-store-signature")
    try:
        parsed: Any = json.loads(body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        parsed = {}
    payload = parsed if isinstance(parsed, dict) else {}
    return await service.process_webhook(
        method,
        body=body,
        signature_header=signature,
        payload=payload,
    )
