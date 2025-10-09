"""ProductService with in-memory fakes."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.problems import ProblemError
from app.products.schemas import ProductIn, ProductPatchIn, VariantIn
from app.products.service import ProductService


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


class FakeCatalog:
    def __init__(self, category_id: UUID) -> None:
        self.category_id = category_id
        self.category = SimpleNamespace(id=category_id, slug="serum")

    async def require_category(self, category_id: UUID) -> SimpleNamespace:
        if category_id != self.category_id:
            raise ProblemError(404, "Not found", "Category not found.", "x")
        return self.category

    async def get_category_by_slug(self, slug: str) -> SimpleNamespace | None:
        if slug == "serum":
            return self.category
        return None

    async def get_attribute_by_kind_slug(
        self, kind: str, slug: str
    ) -> SimpleNamespace | None:
        _ = (kind, slug)
        return None


class FakeRepo:
    def __init__(self, category: SimpleNamespace) -> None:
        self.category = category
        self.products: dict[UUID, SimpleNamespace] = {}
        self.variants: dict[UUID, SimpleNamespace] = {}
        self.by_slug: dict[str, UUID] = {}

    async def list_products(
        self,
        *,
        category_id: UUID | None = None,
        status: str | None = None,
        attribute_id: UUID | None = None,
        include_deleted: bool = False,
        public_only: bool = False,
    ) -> list[SimpleNamespace]:
        _ = attribute_id
        rows = list(self.products.values())
        if not include_deleted:
            rows = [row for row in rows if row.deleted_at is None]
        if public_only:
            rows = [row for row in rows if row.status == "published"]
        elif status is not None:
            rows = [row for row in rows if row.status == status]
        if category_id is not None:
            rows = [row for row in rows if row.category_id == category_id]
        return rows

    async def get_by_slug(
        self, slug: str, *, public_only: bool = False
    ) -> SimpleNamespace | None:
        product_id = self.by_slug.get(slug)
        if product_id is None:
            return None
        row = self.products[product_id]
        if row.deleted_at is not None:
            return None
        if public_only and row.status != "published":
            return None
        return row

    async def get_by_id(self, product_id: UUID) -> SimpleNamespace | None:
        row = self.products.get(product_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def require(self, product_id: UUID) -> SimpleNamespace:
        row = await self.get_by_id(product_id)
        if row is None:
            raise ProblemError(404, "Not found", "Product not found.", "x")
        return row

    async def add(self, product: object) -> SimpleNamespace:
        product_id = getattr(product, "id", None) or uuid4()
        slug = str(product.slug)
        if slug in self.by_slug:
            raise ProblemError(409, "Conflict", "slug", "x")
        row = SimpleNamespace(
            id=product_id,
            category_id=product.category_id,
            category=self.category,
            slug=slug,
            name=str(product.name),
            subtitle=getattr(product, "subtitle", None),
            description=getattr(product, "description", None),
            how_to_use=getattr(product, "how_to_use", None),
            ingredients_text=getattr(product, "ingredients_text", None),
            warnings=getattr(product, "warnings", None),
            routine_step=getattr(product, "routine_step", None),
            pao_months=getattr(product, "pao_months", None),
            shelf_life_months=getattr(product, "shelf_life_months", None),
            status=str(getattr(product, "status", "draft")),
            published_at=getattr(product, "published_at", None),
            deleted_at=None,
            attributes=[],
            variants=[],
        )
        self.products[row.id] = row
        self.by_slug[row.slug] = row.id
        return row

    async def save(self, product: SimpleNamespace) -> SimpleNamespace:
        return product

    async def soft_delete(self, product: SimpleNamespace) -> None:
        product.deleted_at = object()
        if product.status == "published":
            product.status = "archived"

    async def replace_attributes(
        self, product: SimpleNamespace, attribute_ids: list[UUID]
    ) -> SimpleNamespace:
        product.attributes = [
            SimpleNamespace(id=aid, kind="skin_type", slug="oily", name="Oily", sort_order=1)
            for aid in attribute_ids
        ]
        return product

    async def add_variant(self, variant: object) -> SimpleNamespace:
        variant_id = getattr(variant, "id", None) or uuid4()
        row = SimpleNamespace(
            id=variant_id,
            product_id=variant.product_id,
            sku=str(variant.sku),
            size_label=getattr(variant, "size_label", None),
            shade_name=getattr(variant, "shade_name", None),
            shade_hex=getattr(variant, "shade_hex", None),
            spf=getattr(variant, "spf", None),
            price_poisha=int(variant.price_poisha),
            compare_at_poisha=getattr(variant, "compare_at_poisha", None),
            barcode=getattr(variant, "barcode", None),
            weight_grams=getattr(variant, "weight_grams", None),
            is_active=bool(getattr(variant, "is_active", True)),
            sort_order=int(getattr(variant, "sort_order", 0) or 0),
        )
        self.variants[row.id] = row
        product = self.products[row.product_id]
        product.variants.append(row)
        return row

    async def require_variant(self, variant_id: UUID) -> SimpleNamespace:
        row = self.variants.get(variant_id)
        if row is None:
            raise ProblemError(404, "Not found", "Variant not found.", "x")
        return row

    async def save_variant(self, variant: SimpleNamespace) -> SimpleNamespace:
        return variant

    async def delete_variant(self, variant: SimpleNamespace) -> None:
        self.variants.pop(variant.id, None)
        product = self.products[variant.product_id]
        product.variants = [row for row in product.variants if row.id != variant.id]


def _service() -> tuple[ProductService, FakeRepo, FakeAudit, UUID]:
    category_id = uuid4()
    category = SimpleNamespace(id=category_id, slug="serum")
    service = ProductService(FakeSession())  # type: ignore[arg-type]
    repo = FakeRepo(category)
    audit = FakeAudit()
    service.repo = repo  # type: ignore[assignment]
    service.catalog = FakeCatalog(category_id)  # type: ignore[assignment]
    service.audit = audit  # type: ignore[assignment]
    return service, repo, audit, category_id


@pytest.mark.asyncio
async def test_create_published_product_with_variant() -> None:
    service, _repo, audit, category_id = _service()
    out = await service.create(
        ProductIn(
            category_id=category_id,
            slug="barrier-serum",
            name="Barrier Serum",
            routine_step="am",
            status="published",
            pao_months=12,
            variants=[
                VariantIn(sku="ser-30", size_label="30 ml", price_poisha=150000),
            ],
        ),
        actor_user_id=uuid4(),
    )
    assert out.status == "published"
    assert out.published_at is not None
    assert out.variants[0].sku == "SER-30"
    assert out.variants[0].price_poisha == 150000
    assert "catalog.product_created" in audit.actions


@pytest.mark.asyncio
async def test_public_list_hides_drafts() -> None:
    service, repo, _a, category_id = _service()
    draft = await service.create(
        ProductIn(category_id=category_id, slug="draft-one", name="Draft", status="draft"),
        actor_user_id=uuid4(),
    )
    published = await service.create(
        ProductIn(
            category_id=category_id,
            slug="live-one",
            name="Live",
            status="published",
            variants=[VariantIn(sku="LIVE-1", price_poisha=1000)],
        ),
        actor_user_id=uuid4(),
    )
    _ = draft
    listed = await service.list_public(category_slug="serum")
    assert [item.slug for item in listed.items] == ["live-one"]
    assert listed.items[0].from_price_poisha == 1000
    detail = await service.get_public("live-one")
    assert detail.id == published.id


@pytest.mark.asyncio
async def test_soft_delete_archives_published() -> None:
    service, repo, audit, category_id = _service()
    created = await service.create(
        ProductIn(
            category_id=category_id,
            slug="gone",
            name="Gone",
            status="published",
        ),
        actor_user_id=uuid4(),
    )
    await service.soft_delete(created.id, actor_user_id=uuid4())
    assert repo.products[created.id].deleted_at is not None
    assert repo.products[created.id].status == "archived"
    assert "catalog.product_deleted" in audit.actions
    with pytest.raises(ProblemError):
        await service.get_public("gone")


@pytest.mark.asyncio
async def test_patch_sets_published_at() -> None:
    service, _r, _a, category_id = _service()
    created = await service.create(
        ProductIn(category_id=category_id, slug="soon", name="Soon", status="draft"),
        actor_user_id=uuid4(),
    )
    assert created.published_at is None
    updated = await service.patch(
        created.id,
        ProductPatchIn(status="published"),
        actor_user_id=uuid4(),
    )
    assert updated.status == "published"
    assert updated.published_at is not None
