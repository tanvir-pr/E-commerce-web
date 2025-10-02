"""Staff admin routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import (
    AuditEventOut,
    AuditListOut,
    CreateStaffIn,
    CreateStaffOut,
    ReplacePermissionsIn,
)
from app.deps import get_current_staff_user, get_current_super_admin_id
from app.models.audit import AuditLog
from app.models.user import User
from app.session import get_session
from app.staff.service import StaffService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit", response_model=AuditListOut)
async def list_audit(
    _staff: User = Depends(get_current_staff_user),
    session: AsyncSession = Depends(get_session),
) -> AuditListOut:
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)
    )
    rows = result.scalars().all()
    return AuditListOut(
        items=[
            AuditEventOut(
                id=row.id,
                action=row.action,
                actor_user_id=row.actor_user_id,
                subject_type=row.subject_type,
                subject_id=row.subject_id,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


@router.post("/staff", response_model=CreateStaffOut)
async def create_staff(
    body: CreateStaffIn,
    actor_id: UUID = Depends(get_current_super_admin_id),
    session: AsyncSession = Depends(get_session),
) -> CreateStaffOut:
    staff_id = await StaffService(session).create_staff(
        actor_id=actor_id,
        email=str(body.email),
        password=body.password,
        permissions=body.permissions,
    )
    return CreateStaffOut(id=staff_id)


@router.put("/staff/{staff_user_id}/permissions")
async def replace_permissions(
    staff_user_id: UUID,
    body: ReplacePermissionsIn,
    actor_id: UUID = Depends(get_current_super_admin_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await StaffService(session).replace_permissions(
        actor_id=actor_id,
        staff_user_id=staff_user_id,
        permissions=body.permissions,
    )
    return {"message": "Permissions updated."}
