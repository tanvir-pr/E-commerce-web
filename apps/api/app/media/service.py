"""Upload, process, and attach product images."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from uuid_utils import uuid7

from app.audit.service import AuditService
from app.config import Settings
from app.media.constants import ALLOWED_UPLOAD_TYPES, IMAGE_SLOTS
from app.media.processing import process_upload
from app.media.schemas import ImageDerivativeOut, ProductImageOut, ProductImagePatchIn
from app.media.storage import MediaStorage
from app.models.product import ProductImage
from app.problems import PROBLEM_NOT_FOUND, PROBLEM_VALIDATION, ProblemError
from app.products.repository import ProductRepository


class MediaService:
    def __init__(self, session: AsyncSession, *, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.storage = MediaStorage(settings)
        self.products = ProductRepository(session)
        self.audit = AuditService(session)

    async def upload(
        self,
        *,
        product_id: UUID,
        slot: str,
        filename: str | None,
        content_type: str | None,
        data: bytes,
        alt_text: str | None,
        actor_user_id: UUID,
    ) -> ProductImageOut:
        if slot not in IMAGE_SLOTS:
            raise ProblemError(
                422,
                "Validation error",
                f"slot must be one of: {', '.join(sorted(IMAGE_SLOTS))}",
                PROBLEM_VALIDATION,
            )
        if content_type not in ALLOWED_UPLOAD_TYPES:
            raise ProblemError(
                422,
                "Validation error",
                "Only JPEG, PNG, or WebP uploads are accepted.",
                PROBLEM_VALIDATION,
            )
        if len(data) > self.settings.media_max_upload_bytes:
            raise ProblemError(
                422,
                "Validation error",
                "Image exceeds the maximum upload size.",
                PROBLEM_VALIDATION,
            )
        await self.products.require(product_id)
        processed = process_upload(
            data,
            thumb_max=self.settings.media_thumb_max,
            card_max=self.settings.media_card_max,
            full_max=self.settings.media_full_max,
        )
        image_id = UUID(str(uuid7()))
        relative_dir = f"products/{product_id}/{image_id}"
        derivatives_map: dict[str, dict[str, object]] = {"webp": {}, "avif": {}}
        for item in processed.derivatives:
            webp_rel = f"{relative_dir}/{item.size_key}.webp"
            self.storage.write_bytes(webp_rel, item.webp)
            derivatives_map["webp"][item.size_key] = {
                "path": webp_rel,
                "width": item.width,
                "height": item.height,
            }
            if item.avif:
                avif_rel = f"{relative_dir}/{item.size_key}.avif"
                self.storage.write_bytes(avif_rel, item.avif)
                derivatives_map["avif"][item.size_key] = {
                    "path": avif_rel,
                    "width": item.width,
                    "height": item.height,
                }

        row = ProductImage(
            id=image_id,
            product_id=product_id,
            slot=slot,
            alt_text=alt_text,
            sort_order=0,
            original_filename=filename,
            content_type=content_type,
            width=processed.width,
            height=processed.height,
            derivatives=derivatives_map,
            created_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        await self.audit.record(
            action="catalog.image_uploaded",
            actor_user_id=actor_user_id,
            subject_type="product_image",
            subject_id=str(image_id),
            meta={"product_id": str(product_id), "slot": slot},
        )
        return self._out(row)

    async def patch(
        self,
        image_id: UUID,
        body: ProductImagePatchIn,
        *,
        actor_user_id: UUID,
    ) -> ProductImageOut:
        row = await self._require(image_id)
        data = body.model_dump(exclude_unset=True)
        if "slot" in data and data["slot"] not in IMAGE_SLOTS:
            raise ProblemError(
                422,
                "Validation error",
                f"slot must be one of: {', '.join(sorted(IMAGE_SLOTS))}",
                PROBLEM_VALIDATION,
            )
        for key, value in data.items():
            setattr(row, key, value)
        await self.session.flush()
        await self.audit.record(
            action="catalog.image_updated",
            actor_user_id=actor_user_id,
            subject_type="product_image",
            subject_id=str(image_id),
        )
        return self._out(row)

    async def delete(self, image_id: UUID, *, actor_user_id: UUID) -> None:
        row = await self._require(image_id)
        product_id = row.product_id
        self.storage.delete_tree(product_id, image_id)
        await self.session.delete(row)
        await self.session.flush()
        await self.audit.record(
            action="catalog.image_deleted",
            actor_user_id=actor_user_id,
            subject_type="product_image",
            subject_id=str(image_id),
            meta={"product_id": str(product_id)},
        )

    async def _require(self, image_id: UUID) -> ProductImage:
        row = await self.session.get(ProductImage, image_id)
        if row is None:
            raise ProblemError(404, "Not found", "Image not found.", PROBLEM_NOT_FOUND)
        return row

    def _out(self, row: ProductImage) -> ProductImageOut:
        derivatives: list[ImageDerivativeOut] = []
        webp_map = (row.derivatives or {}).get("webp", {})
        avif_map = (row.derivatives or {}).get("avif", {})
        for size_key in ("thumb", "card", "full"):
            webp = webp_map.get(size_key)
            if not isinstance(webp, dict):
                continue
            path = str(webp.get("path", ""))
            avif = avif_map.get(size_key) if isinstance(avif_map, dict) else None
            avif_url = None
            if isinstance(avif, dict) and avif.get("path"):
                avif_url = self.storage.relative_url(str(avif["path"]))
            derivatives.append(
                ImageDerivativeOut(
                    size_key=size_key,
                    width=int(webp.get("width", row.width)),
                    height=int(webp.get("height", row.height)),
                    webp_url=self.storage.relative_url(path),
                    avif_url=avif_url,
                )
            )
        return ProductImageOut(
            id=row.id,
            product_id=row.product_id,
            slot=row.slot,
            alt_text=row.alt_text,
            sort_order=row.sort_order,
            width=row.width,
            height=row.height,
            derivatives=derivatives,
            created_at=row.created_at,
        )
