"""Staff product image upload routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import get_current_staff_user, get_current_user_id
from app.media.schemas import MessageOut, ProductImageOut, ProductImagePatchIn
from app.media.service import MediaService
from app.models.user import User
from app.session import get_session

router = APIRouter(prefix="/admin/catalog", tags=["admin-media"])


def get_media_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MediaService:
    return MediaService(session, settings=settings)


@router.post(
    "/products/{product_id}/images",
    response_model=ProductImageOut,
    status_code=201,
)
async def upload_product_image(
    product_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: MediaService = Depends(get_media_service),
    file: UploadFile = File(...),
    slot: str = Form(default="product"),
    alt_text: str | None = Form(default=None),
) -> ProductImageOut:
    data = await file.read()
    return await service.upload(
        product_id=product_id,
        slot=slot,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        alt_text=alt_text,
        actor_user_id=actor_id,
    )


@router.patch("/images/{image_id}", response_model=ProductImageOut)
async def patch_product_image(
    image_id: UUID,
    body: ProductImagePatchIn,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: MediaService = Depends(get_media_service),
) -> ProductImageOut:
    return await service.patch(image_id, body, actor_user_id=actor_id)


@router.delete("/images/{image_id}", response_model=MessageOut)
async def delete_product_image(
    image_id: UUID,
    actor_id: UUID = Depends(get_current_user_id),
    _staff: User = Depends(get_current_staff_user),
    service: MediaService = Depends(get_media_service),
) -> MessageOut:
    await service.delete(image_id, actor_user_id=actor_id)
    return MessageOut(message="Image deleted.")
