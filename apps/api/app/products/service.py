"""Product catalog use cases."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.catalog.repository import CatalogRepository
from app.config import get_settings
from app.models.product import Product, ProductImage, ProductVariant
from app.problems import PROBLEM_NOT_FOUND, PROBLEM_VALIDATION, ProblemError
from app.products.constants import PRODUCT_STATUSES, ROUTINE_STEPS
from app.products.repository import ProductRepository
from app.products.schemas import (
    BulkStatusIn,
    BulkStatusOut,
    ProductAttributeRef,
    ProductImageSummaryOut,
    ProductIn,
    ProductListOut,
    ProductOut,
    ProductPatchIn,
    ProductSummaryOut,
    VariantIn,
    VariantOut,
    VariantPatchIn,
)
from app.search.indexer import SearchIndexer


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProductRepository(session)
        self.catalog = CatalogRepository(session)
        self.audit = AuditService(session)
        self.search = SearchIndexer(session)

    async def list_public(
        self,
        *,
        category_slug: str | None = None,
        attribute_slug: str | None = None,
        attribute_kind: str | None = None,
    ) -> ProductListOut:
        category_id = None
        if category_slug:
            category = await self.catalog.get_category_by_slug(category_slug)
            if category is None:
                return ProductListOut(items=[])
            category_id = category.id
        attribute_id = None
        if attribute_slug:
            if not attribute_kind:
                raise ProblemError(
                    422,
                    "Validation error",
                    "attribute_kind is required with attribute_slug.",
                    PROBLEM_VALIDATION,
                )
            attr = await self.catalog.get_attribute_by_kind_slug(
                attribute_kind, attribute_slug
            )
            if attr is None:
                return ProductListOut(items=[])
            attribute_id = attr.id
        rows = await self.repo.list_products(
            category_id=category_id,
            attribute_id=attribute_id,
            public_only=True,
        )
        return ProductListOut(items=[_summary(row) for row in rows])

    async def list_admin(
        self, *, status: str | None = None, category_id: UUID | None = None
    ) -> ProductListOut:
        if status is not None and status not in PRODUCT_STATUSES:
            raise ProblemError(
                422,
                "Validation error",
                f"status must be one of: {', '.join(sorted(PRODUCT_STATUSES))}",
                PROBLEM_VALIDATION,
            )
        rows = await self.repo.list_products(status=status, category_id=category_id)
        return ProductListOut(items=[_summary(row) for row in rows])

    async def get_public(self, slug: str) -> ProductOut:
        row = await self.repo.get_by_slug(slug, public_only=True)
        if row is None:
            raise ProblemError(404, "Not found", "Product not found.", PROBLEM_NOT_FOUND)
        return _detail(row, active_variants_only=True)

    async def get_admin(self, product_id: UUID) -> ProductOut:
        row = await self.repo.require(product_id)
        return _detail(row, active_variants_only=False)

    async def create(self, body: ProductIn, *, actor_user_id: UUID) -> ProductOut:
        await self.catalog.require_category(body.category_id)
        _validate_routine(body.routine_step)
        if body.status not in PRODUCT_STATUSES:
            raise ProblemError(422, "Validation error", "Invalid status.", PROBLEM_VALIDATION)
        product = Product(
            category_id=body.category_id,
            slug=body.slug,
            name=body.name,
            subtitle=body.subtitle,
            description=body.description,
            how_to_use=body.how_to_use,
            ingredients_text=body.ingredients_text,
            warnings=body.warnings,
            routine_step=body.routine_step,
            pao_months=body.pao_months,
            shelf_life_months=body.shelf_life_months,
            status=body.status,
            published_at=datetime.now(UTC) if body.status == "published" else None,
        )
        saved = await self.repo.add(product)
        if body.attribute_ids:
            saved = await self.repo.replace_attributes(saved, body.attribute_ids)
        for variant_body in body.variants:
            await self._add_variant(saved.id, variant_body)
        saved = await self.repo.require(saved.id)
        await self.audit.record(
            action="catalog.product_created",
            actor_user_id=actor_user_id,
            subject_type="product",
            subject_id=str(saved.id),
        )
        await self.search.upsert_product(saved.id)
        return _detail(saved, active_variants_only=False)

    async def patch(
        self, product_id: UUID, body: ProductPatchIn, *, actor_user_id: UUID
    ) -> ProductOut:
        row = await self.repo.require(product_id)
        data = body.model_dump(exclude_unset=True)
        attribute_ids = data.pop("attribute_ids", None)
        if "category_id" in data and data["category_id"] is not None:
            await self.catalog.require_category(data["category_id"])
        if "routine_step" in data:
            _validate_routine(data["routine_step"])
        if "status" in data:
            new_status = data["status"]
            if new_status not in PRODUCT_STATUSES:
                raise ProblemError(
                    422, "Validation error", "Invalid status.", PROBLEM_VALIDATION
                )
            if new_status == "published" and row.published_at is None:
                row.published_at = datetime.now(UTC)
        for key, value in data.items():
            setattr(row, key, value)
        saved = await self.repo.save(row)
        if attribute_ids is not None:
            saved = await self.repo.replace_attributes(saved, attribute_ids)
        await self.audit.record(
            action="catalog.product_updated",
            actor_user_id=actor_user_id,
            subject_type="product",
            subject_id=str(saved.id),
        )
        await self.search.upsert_product(saved.id)
        return _detail(saved, active_variants_only=False)

    async def soft_delete(self, product_id: UUID, *, actor_user_id: UUID) -> None:
        row = await self.repo.require(product_id)
        await self.repo.soft_delete(row)
        await self.audit.record(
            action="catalog.product_deleted",
            actor_user_id=actor_user_id,
            subject_type="product",
            subject_id=str(product_id),
        )
        await self.search.remove_product(product_id)

    async def bulk_status(
        self, body: BulkStatusIn, *, actor_user_id: UUID
    ) -> BulkStatusOut:
        if body.status not in PRODUCT_STATUSES:
            raise ProblemError(
                422, "Validation error", "Invalid status.", PROBLEM_VALIDATION
            )
        updated = 0
        touched: list[UUID] = []
        for product_id in body.product_ids:
            row = await self.repo.get_by_id(product_id)
            if row is None:
                continue
            row.status = body.status
            if body.status == "published" and row.published_at is None:
                row.published_at = datetime.now(UTC)
            await self.repo.save(row)
            updated += 1
            touched.append(product_id)
        await self.audit.record(
            action="catalog.products_bulk_status",
            actor_user_id=actor_user_id,
            subject_type="product_bulk",
            subject_id=body.status,
            meta={"updated": updated, "requested": len(body.product_ids)},
        )
        for product_id in touched:
            await self.search.upsert_product(product_id)
        return BulkStatusOut(updated=updated, status=body.status)

    async def add_variant(
        self, product_id: UUID, body: VariantIn, *, actor_user_id: UUID
    ) -> VariantOut:
        await self.repo.require(product_id)
        variant = await self._add_variant(product_id, body)
        await self.audit.record(
            action="catalog.variant_created",
            actor_user_id=actor_user_id,
            subject_type="product_variant",
            subject_id=str(variant.id),
        )
        await self.search.upsert_product(product_id)
        return _variant_out(variant)

    async def patch_variant(
        self, variant_id: UUID, body: VariantPatchIn, *, actor_user_id: UUID
    ) -> VariantOut:
        variant = await self.repo.require_variant(variant_id)
        for key, value in body.model_dump(exclude_unset=True).items():
            if key == "shade_hex" and value:
                value = value.upper()
            setattr(variant, key, value)
        saved = await self.repo.save_variant(variant)
        await self.audit.record(
            action="catalog.variant_updated",
            actor_user_id=actor_user_id,
            subject_type="product_variant",
            subject_id=str(saved.id),
        )
        await self.search.upsert_product(saved.product_id)
        return _variant_out(saved)

    async def delete_variant(self, variant_id: UUID, *, actor_user_id: UUID) -> None:
        variant = await self.repo.require_variant(variant_id)
        product_id = variant.product_id
        await self.repo.delete_variant(variant)
        await self.audit.record(
            action="catalog.variant_deleted",
            actor_user_id=actor_user_id,
            subject_type="product_variant",
            subject_id=str(variant_id),
            meta={"product_id": str(product_id)},
        )
        await self.search.upsert_product(product_id)

    async def _add_variant(self, product_id: UUID, body: VariantIn) -> ProductVariant:
        variant = ProductVariant(
            product_id=product_id,
            sku=body.sku.strip().upper(),
            size_label=body.size_label,
            shade_name=body.shade_name,
            shade_hex=body.shade_hex,
            spf=body.spf,
            price_poisha=body.price_poisha,
            compare_at_poisha=body.compare_at_poisha,
            barcode=body.barcode,
            weight_grams=body.weight_grams,
            is_active=body.is_active,
            sort_order=body.sort_order,
        )
        return await self.repo.add_variant(variant)


def _validate_routine(value: str | None) -> None:
    if value is None:
        return
    if value not in ROUTINE_STEPS:
        raise ProblemError(
            422,
            "Validation error",
            f"routine_step must be one of: {', '.join(sorted(ROUTINE_STEPS))}",
            PROBLEM_VALIDATION,
        )


def _summary(row: Product) -> ProductSummaryOut:
    active = [v for v in row.variants if v.is_active]
    prices = [v.price_poisha for v in active] or [v.price_poisha for v in row.variants]
    return ProductSummaryOut(
        id=row.id,
        category_id=row.category_id,
        category_slug=row.category.slug if row.category else None,
        slug=row.slug,
        name=row.name,
        subtitle=row.subtitle,
        routine_step=row.routine_step,
        status=row.status,
        from_price_poisha=min(prices) if prices else None,
        published_at=row.published_at,
    )


def _detail(row: Product, *, active_variants_only: bool) -> ProductOut:
    variants = list(row.variants or [])
    if active_variants_only:
        variants = [v for v in variants if v.is_active]
    variants = sorted(variants, key=lambda v: (v.sort_order, v.sku))
    attrs = sorted(row.attributes or [], key=lambda a: (a.kind, a.sort_order, a.name))
    return ProductOut(
        id=row.id,
        category_id=row.category_id,
        category_slug=row.category.slug if row.category else None,
        slug=row.slug,
        name=row.name,
        subtitle=row.subtitle,
        description=row.description,
        how_to_use=row.how_to_use,
        ingredients_text=row.ingredients_text,
        warnings=row.warnings,
        routine_step=row.routine_step,
        pao_months=row.pao_months,
        shelf_life_months=row.shelf_life_months,
        status=row.status,
        published_at=row.published_at,
        attributes=[
            ProductAttributeRef(id=a.id, kind=a.kind, slug=a.slug, name=a.name)
            for a in attrs
        ],
        variants=[_variant_out(v) for v in variants],
        images=[
            _image_out(img)
            for img in sorted(
                getattr(row, "images", None) or [],
                key=lambda i: (i.sort_order, str(i.id)),
            )
        ],
    )


def _image_out(row: ProductImage) -> ProductImageSummaryOut:
    base = get_settings().media_url_path.rstrip("/")

    def url_for(fmt: str, size_key: str) -> str | None:
        block = (row.derivatives or {}).get(fmt, {})
        if not isinstance(block, dict):
            return None
        entry = block.get(size_key)
        if not isinstance(entry, dict) or not entry.get("path"):
            return None
        return f"{base}/{str(entry['path']).replace(chr(92), '/')}"

    return ProductImageSummaryOut(
        id=row.id,
        slot=row.slot,
        alt_text=row.alt_text,
        sort_order=row.sort_order,
        width=row.width,
        height=row.height,
        thumb_webp_url=url_for("webp", "thumb"),
        thumb_avif_url=url_for("avif", "thumb"),
        card_webp_url=url_for("webp", "card"),
        card_avif_url=url_for("avif", "card"),
        full_webp_url=url_for("webp", "full"),
        full_avif_url=url_for("avif", "full"),
    )


def _variant_out(row: ProductVariant) -> VariantOut:
    return VariantOut(
        id=row.id,
        sku=row.sku,
        size_label=row.size_label,
        shade_name=row.shade_name,
        shade_hex=row.shade_hex,
        spf=row.spf,
        price_poisha=row.price_poisha,
        compare_at_poisha=row.compare_at_poisha,
        barcode=row.barcode,
        weight_grams=row.weight_grams,
        is_active=row.is_active,
        sort_order=row.sort_order,
    )
