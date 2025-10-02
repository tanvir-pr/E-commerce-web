"""Shared request dependencies."""

from typing import cast
from uuid import UUID

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.problems import PROBLEM_UNAUTHORIZED, InvalidAccessToken, ProblemError
from app.rbac import ensure_staff, ensure_super_admin
from app.security.cookies import ACCESS_COOKIE
from app.security.tokens import decode_access_token
from app.session import get_session
from app.users.repository import UserRepository
from app.users.schemas import MeOut
from app.users.service import UserService


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_current_user_id(request: Request) -> UUID:
    raw = request.cookies.get(ACCESS_COOKIE)
    if not raw:
        raise ProblemError(
            401,
            "Unauthorized",
            "Sign in again.",
            PROBLEM_UNAUTHORIZED,
        )
    try:
        payload = decode_access_token(raw)
        return UUID(str(payload["sub"]))
    except (InvalidAccessToken, ValueError, KeyError) as exc:
        raise ProblemError(
            401,
            "Unauthorized",
            "Sign in again.",
            PROBLEM_UNAUTHORIZED,
        ) from exc


async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> MeOut:
    return await UserService(session).get_me(user_id)


async def get_current_user_row(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise ProblemError(
            401,
            "Unauthorized",
            "Sign in again.",
            PROBLEM_UNAUTHORIZED,
        )
    return user


async def get_current_staff_user(user: User = Depends(get_current_user_row)) -> User:
    ensure_staff(user)
    return user


async def get_current_super_admin_id(user: User = Depends(get_current_user_row)) -> UUID:
    ensure_super_admin(user)
    return user.id
