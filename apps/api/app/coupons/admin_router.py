"""Staff coupon CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.coupons.schemas import CouponIn, CouponListOut, CouponOut
from app.coupons.service import CouponService
from app.deps import get_current_staff_user, get_current_user_id
from app.models.user import User
from app.session import get_session

router = APIRouter(tags=["admin-coupons"])


def get_coupon_service(session: AsyncSession = Depends(get_session)) -> CouponService:
    return CouponService(session)


@router.get("/admin/coupons", response_model=CouponListOut)
async def list_coupons(
    _staff: User = Depends(get_current_staff_user),
    service: CouponService = Depends(get_coupon_service),
) -> CouponListOut:
    return await service.list_admin()


@router.post("/admin/coupons", response_model=CouponOut, status_code=201)
async def create_coupon(
    body: CouponIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CouponService = Depends(get_coupon_service),
) -> CouponOut:
    return await service.create(body, actor_user_id=actor_id)


@router.patch("/admin/coupons/{coupon_id}", response_model=CouponOut)
async def update_coupon(
    coupon_id: UUID,
    body: CouponIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CouponService = Depends(get_coupon_service),
) -> CouponOut:
    return await service.update(coupon_id, body, actor_user_id=actor_id)


@router.delete("/admin/coupons/{coupon_id}", status_code=204)
async def delete_coupon(
    coupon_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: CouponService = Depends(get_coupon_service),
) -> None:
    await service.delete(coupon_id, actor_user_id=actor_id)
