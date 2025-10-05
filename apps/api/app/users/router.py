"""Customer account routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_current_user_id
from app.security.cookies import REFRESH_COOKIE
from app.session import get_session
from app.users.schemas import (
    AddressIn,
    AddressOut,
    MeOut,
    MePatchIn,
    MessageOut,
    SessionListOut,
)
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)


@router.get("/me", response_model=MeOut)
async def me(current: MeOut = Depends(get_current_user)) -> MeOut:
    return current


@router.patch("/me", response_model=MeOut)
async def patch_me(
    body: MePatchIn,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> MeOut:
    return await service.patch_me(user_id, body)


@router.get("/me/export")
async def export_me(
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    return await service.export(user_id)


@router.delete("/me", response_model=MessageOut)
async def delete_me(
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> MessageOut:
    await service.soft_delete(user_id)
    return MessageOut(
        message=(
            "Account marked deleted and sessions revoked. "
            "Full erasure is incomplete (row and audit history remain)."
        )
    )


@router.get("/me/addresses", response_model=list[AddressOut])
async def list_addresses(
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> list[AddressOut]:
    return await service.list_addresses(user_id)


@router.post("/me/addresses", response_model=AddressOut, status_code=201)
async def create_address(
    body: AddressIn,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> AddressOut:
    return await service.create_address(user_id, body)


@router.put("/me/addresses/{address_id}", response_model=AddressOut)
async def update_address(
    address_id: UUID,
    body: AddressIn,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> AddressOut:
    return await service.update_address(user_id, address_id, body)


@router.delete("/me/addresses/{address_id}", response_model=MessageOut)
async def delete_address(
    address_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> MessageOut:
    await service.delete_address(user_id, address_id)
    return MessageOut(message="Address deleted.")


@router.get("/me/sessions", response_model=SessionListOut)
async def list_sessions(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> SessionListOut:
    return await service.list_sessions(
        user_id, current_refresh=request.cookies.get(REFRESH_COOKIE)
    )


@router.delete("/me/sessions/{session_id}", response_model=MessageOut)
async def revoke_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> MessageOut:
    await service.revoke_session(user_id, session_id)
    return MessageOut(message="Session revoked.")
