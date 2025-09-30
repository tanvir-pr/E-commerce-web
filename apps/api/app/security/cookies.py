"""Session cookie helpers (__Host- prefix)."""

from fastapi import Response

ACCESS_COOKIE = "__Host-access"
REFRESH_COOKIE = "__Host-refresh"
CSRF_COOKIE = "__Host-csrf"

_COMMON = {
    "secure": True,
    "samesite": "lax",
    "path": "/",
}


def set_access_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        **_COMMON,  # type: ignore[arg-type]
    )


def set_refresh_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        **_COMMON,  # type: ignore[arg-type]
    )


def set_csrf_cookie(response: Response, token: str, max_age: int = 60 * 60 * 12) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        max_age=max_age,
        httponly=False,
        **_COMMON,  # type: ignore[arg-type]
    )


def clear_session_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", secure=True, httponly=True, samesite="lax")
