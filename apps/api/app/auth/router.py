"""Auth HTTP routes."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.mailer import ArqMailer
from app.auth.schemas import (
    CsrfOut,
    LoginIn,
    LoginOut,
    MessageOut,
    RegisterIn,
    RegisterOut,
    TotpChallengeIn,
    TotpConfirmIn,
    TotpConfirmOut,
    TotpSetupOut,
    VerifyEmailIn,
    VerifyEmailOut,
)
from app.auth.service import AuthService, client_meta, request_header_map
from app.config import Settings, get_settings
from app.deps import get_redis
from app.security.cookies import (
    CHALLENGE_COOKIE,
    ENROLL_COOKIE,
    REFRESH_COOKIE,
    clear_pending_cookies,
    clear_session_cookies,
    set_access_cookie,
    set_challenge_cookie,
    set_csrf_cookie,
    set_enroll_cookie,
    set_refresh_cookie,
)
from app.security.rate_limit import RedisRateLimiter
from app.security.tokens import generate_opaque_token
from app.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        session,
        settings=settings,
        mailer=ArqMailer(request.app.state.arq),
    )


def _set_session_cookies(
    response: Response,
    *,
    access: str,
    refresh: str,
    settings: Settings,
) -> None:
    set_access_cookie(response, access, settings.access_token_ttl_seconds)
    set_refresh_cookie(
        response,
        refresh,
        settings.refresh_token_ttl_days * 24 * 60 * 60,
    )
    clear_pending_cookies(response)


@router.get("/csrf", response_model=CsrfOut)
async def issue_csrf(response: Response) -> CsrfOut:
    token = generate_opaque_token(24)
    set_csrf_cookie(response, token)
    return CsrfOut(csrf_token=token)


@router.post("/register", response_model=RegisterOut)
async def register(
    body: RegisterIn,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> RegisterOut:
    ip, user_agent = client_meta(request_header_map(request.headers))
    message = await service.register(
        email=str(body.email),
        password=body.password,
        ip=ip,
        user_agent=user_agent,
    )
    return RegisterOut(message=message)


@router.post("/verify-email", response_model=VerifyEmailOut)
async def verify_email(
    body: VerifyEmailIn,
    service: AuthService = Depends(get_auth_service),
) -> VerifyEmailOut:
    await service.verify_email(token=body.token)
    return VerifyEmailOut(message="Email verified. You can sign in.")


@router.post("/login", response_model=LoginOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
) -> LoginOut:
    ip, user_agent = client_meta(request_header_map(request.headers))
    limiter_ip = RedisRateLimiter(
        redis,
        limit=settings.login_rate_limit_per_ip,
        window_seconds=settings.login_rate_limit_window_seconds,
        prefix="login:ip",
    )
    limiter_email = RedisRateLimiter(
        redis,
        limit=settings.login_rate_limit_per_email,
        window_seconds=settings.login_rate_limit_window_seconds,
        prefix="login:email",
    )
    await limiter_ip.check(ip or "unknown")
    await limiter_email.check(str(body.email).strip().lower())

    result = await service.login(
        email=str(body.email),
        password=body.password,
        ip=ip,
        user_agent=user_agent,
    )
    clear_session_cookies(response)
    if result.next == "session" and result.access and result.refresh:
        _set_session_cookies(
            response, access=result.access, refresh=result.refresh, settings=settings
        )
        return LoginOut(next="session")
    if result.next == "enroll" and result.pending_token:
        set_enroll_cookie(response, result.pending_token, settings.pending_auth_ttl_seconds)
        return LoginOut(next="enroll")
    if result.next == "challenge" and result.pending_token:
        set_challenge_cookie(response, result.pending_token, settings.pending_auth_ttl_seconds)
        return LoginOut(next="challenge")
    return LoginOut(next="session")


@router.post("/totp/setup", response_model=TotpSetupOut)
async def totp_setup(
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TotpSetupOut:
    result = await service.totp_setup(enroll_token=request.cookies.get(ENROLL_COOKIE))
    return TotpSetupOut(
        secret=result.secret,
        otpauth_url=result.otpauth_url,
        qr_svg=result.qr_svg,
    )


@router.post("/totp/confirm", response_model=TotpConfirmOut)
async def totp_confirm(
    body: TotpConfirmIn,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
) -> TotpConfirmOut:
    _user, access, refresh, codes = await service.totp_confirm(
        enroll_token=request.cookies.get(ENROLL_COOKIE),
        code=body.code,
    )
    _set_session_cookies(response, access=access, refresh=refresh, settings=settings)
    return TotpConfirmOut(recovery_codes=codes)


@router.post("/totp/challenge", response_model=LoginOut)
async def totp_challenge(
    body: TotpChallengeIn,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
) -> LoginOut:
    _user, access, refresh = await service.totp_challenge(
        challenge_token=request.cookies.get(CHALLENGE_COOKIE),
        code=body.code,
        recovery_code=body.recovery_code,
    )
    _set_session_cookies(response, access=access, refresh=refresh, settings=settings)
    return LoginOut(next="session")


@router.post("/refresh", response_model=MessageOut)
async def refresh(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    service: AuthService = Depends(get_auth_service),
) -> MessageOut:
    raw = request.cookies.get(REFRESH_COOKIE)
    _user, access, new_refresh = await service.refresh(raw_refresh=raw)
    _set_session_cookies(response, access=access, refresh=new_refresh, settings=settings)
    return MessageOut(message="Session refreshed.")


@router.post("/logout", response_model=MessageOut)
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> Any:
    raw = request.cookies.get(REFRESH_COOKIE)
    await service.logout(raw_refresh=raw)
    clear_session_cookies(response)
    return MessageOut(message="Signed out.")
