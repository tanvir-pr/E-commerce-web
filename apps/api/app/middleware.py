"""Request id on every request and CSRF for mutating methods."""

import json
import re
from http.cookies import SimpleCookie
from typing import Any
from uuid import uuid4

import structlog

from app.logging_config import current_request_id
from app.problems import PROBLEM_CSRF, ProblemError, problem_payload
from app.security.cookies import CSRF_COOKIE

_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}")
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_EXEMPT_PATHS = {"/api/v1/health"}


def _headers(scope: dict[str, Any]) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, value in scope.get("headers", []):
        found[key.decode("latin-1").lower()] = value.decode("latin-1")
    return found


def request_id_value(raw: str | None) -> str:
    if raw and _REQUEST_ID_RE.fullmatch(raw):
        return raw
    return str(uuid4())


def _csrf_from_cookie(cookie_header: str | None) -> str:
    if not cookie_header:
        return ""
    jar = SimpleCookie()
    jar.load(cookie_header)
    morsel = jar.get(CSRF_COOKIE)
    return morsel.value if morsel else ""


class RequestContextMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = _headers(scope)
        request_id = request_id_value(headers.get("x-request-id"))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        log = structlog.get_logger()
        status_code = 500

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = list(message.get("headers") or [])
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            log.info(
                "request_completed",
                method=scope.get("method"),
                path=scope.get("path"),
                status=status_code,
            )
        except Exception:
            log.error(
                "request_failed",
                method=scope.get("method"),
                path=scope.get("path"),
                error_type="unhandled",
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()


class CSRFMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET")).upper()
        path = scope.get("path", "")
        if method in _SAFE_METHODS or path in _CSRF_EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        headers = _headers(scope)
        cookie_token = _csrf_from_cookie(headers.get("cookie"))
        header_token = headers.get("x-csrf-token", "")
        if not cookie_token or not header_token or cookie_token != header_token:
            payload = problem_payload(
                ProblemError(
                    403,
                    "CSRF validation failed",
                    "Missing or invalid CSRF token.",
                    PROBLEM_CSRF,
                ),
                current_request_id(),
            )
            body = json.dumps(payload).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [
                        (b"content-type", b"application/problem+json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
