"""CatalogService tree and attribute helpers with fakes."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from app.catalog.schemas import AttributeIn, CategoryIn, CategoryPatchIn
from app.catalog.service import CatalogService
from app.problems import ProblemError


class FakeSession:
    async def flush(self) -> None:
        return None


class FakeAudit:
    def __init__(self) -> None:
        self.actions: list[str] = []

    async def record(self, **kwargs: object) -> None:
        self.actions.append(str(kwargs.get("action")))


class FakeRepo:
    def __init__(self) -> None:
        self.categories: dict[UUID, SimpleNamespace] = {}
        self.attributes: dict[UUID, SimpleNamespace] = {}
        self.by_slug: dict[str, UUID] = {}

    async def list_categories(self, *, include_inactive: bool = False) -> list[SimpleNamespace]:
        rows = list(self.categories.values())
        if not include_inactive:
            rows = [row for row in rows if row.is_active and row.deleted_at is None]
        else:
            rows = [row for row in rows if row.deleted_at is None]
        return sorted(rows, key=lambda r: (r.sort_order, r.name))

    async def get_category_by_slug(
        self, slug: str, *, include_inactive: bool = False
    ) -> SimpleNamespace | None:
        category_id = self.by_slug.get(slug)
        if category_id is None:
            return None
        row = self.categories[category_id]
        if row.deleted_at is not None:
            return None
        if not include_inactive and not row.is_active:
            return None
        return row

    async def get_category_by_id(self, category_id: UUID) -> SimpleNamespace | None:
        row = self.categories.get(category_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def require_category(self, category_id: UUID) -> SimpleNamespace:
        row = await self.get_category_by_id(category_id)
        if row is None:
            raise ProblemError(404, "Not found", "Category not found.", "x")
        return row

    async def add_category(self, category: object) -> SimpleNamespace:
        category_id = getattr(category, "id", None) or uuid4()
        slug = str(category.slug)
        if slug in self.by_slug:
            raise ProblemError(409, "Conflict", "slug exists", "x")
        row = SimpleNamespace(
            id=category_id,
            parent_id=getattr(category, "parent_id", None),
            slug=slug,
            name=str(category.name),
            description=getattr(category, "description", None),
            sort_order=int(getattr(category, "sort_order", 0) or 0),
            is_active=bool(getattr(category, "is_active", True)),
            deleted_at=None,
            attributes=[],
        )
        self.categories[row.id] = row
        self.by_slug[row.slug] = row.id
        return row

    async def save_category(self, category: SimpleNamespace) -> SimpleNamespace:
        return category

    async def soft_delete_category(self, category: SimpleNamespace) -> None:
        category.deleted_at = object()
        category.is_active = False

    async def replace_category_attributes(
        self, category: SimpleNamespace, attribute_ids: list[UUID]
    ) -> SimpleNamespace:
        attrs = []
        for attribute_id in attribute_ids:
            attr = self.attributes.get(attribute_id)
            if attr is None:
                raise ProblemError(404, "Not found", "attr", "x")
            attrs.append(attr)
        category.attributes = attrs
        return category

    async def list_attributes(
        self, *, kind: str | None = None, include_inactive: bool = False
    ) -> list[SimpleNamespace]:
        rows = list(self.attributes.values())
        if kind is not None:
            rows = [row for row in rows if row.kind == kind]
        if not include_inactive:
            rows = [row for row in rows if row.is_active]
        return sorted(rows, key=lambda r: (r.kind, r.sort_order, r.name))

    async def get_attribute_by_id(self, attribute_id: UUID) -> SimpleNamespace | None:
        return self.attributes.get(attribute_id)

    async def require_attribute(self, attribute_id: UUID) -> SimpleNamespace:
        row = await self.get_attribute_by_id(attribute_id)
        if row is None:
            raise ProblemError(404, "Not found", "Attribute not found.", "x")
        return row

    async def add_attribute(self, attribute: object) -> SimpleNamespace:
        attribute_id = getattr(attribute, "id", None) or uuid4()
        row = SimpleNamespace(
            id=attribute_id,
            kind=str(attribute.kind),
            slug=str(attribute.slug),
            name=str(attribute.name),
            description=getattr(attribute, "description", None),
            sort_order=int(getattr(attribute, "sort_order", 0) or 0),
            is_active=bool(getattr(attribute, "is_active", True)),
        )
        self.attributes[row.id] = row
        return row

    async def save_attribute(self, attribute: SimpleNamespace) -> SimpleNamespace:
        return attribute


def _service() -> tuple[CatalogService, FakeRepo, FakeAudit]:
    service = CatalogService(FakeSession())  # type: ignore[arg-type]
    repo = FakeRepo()
    audit = FakeAudit()
    service.repo = repo  # type: ignore[assignment]
    service.audit = audit  # type: ignore[assignment]
    return service, repo, audit


@pytest.mark.asyncio
async def test_category_tree_nesting() -> None:
    service, repo, _a = _service()
    root = SimpleNamespace(
        id=uuid4(),
        parent_id=None,
        slug="skincare",
        name="Skincare",
        description=None,
        sort_order=0,
        is_active=True,
        deleted_at=None,
        attributes=[],
    )
    child = SimpleNamespace(
        id=uuid4(),
        parent_id=root.id,
        slug="serum",
        name="Serum",
        description=None,
        sort_order=10,
        is_active=True,
        deleted_at=None,
        attributes=[],
    )
    repo.categories[root.id] = root
    repo.categories[child.id] = child
    repo.by_slug[root.slug] = root.id
    repo.by_slug[child.slug] = child.id

    tree = await service.list_category_tree()
    assert len(tree) == 1
    assert tree[0].slug == "skincare"
    assert len(tree[0].children) == 1
    assert tree[0].children[0].slug == "serum"


@pytest.mark.asyncio
async def test_create_category_with_attributes() -> None:
    service, repo, audit = _service()
    attr = SimpleNamespace(
        id=uuid4(),
        kind="skin_type",
        slug="oily",
        name="Oily",
        description=None,
        sort_order=1,
        is_active=True,
    )
    repo.attributes[attr.id] = attr
    actor = uuid4()
    created = await service.create_category(
        CategoryIn(slug="toner", name="Toner", attribute_ids=[attr.id]),
        actor_user_id=actor,
    )
    assert created.slug == "toner"
    assert created.attribute_ids == [attr.id]
    assert "catalog.category_created" in audit.actions


@pytest.mark.asyncio
async def test_list_attributes_rejects_unknown_kind() -> None:
    service, _r, _a = _service()
    with pytest.raises(ProblemError) as exc:
        await service.list_attributes(kind="nope")
    assert exc.value.status == 422


@pytest.mark.asyncio
async def test_create_attribute() -> None:
    service, _r, audit = _service()
    out = await service.create_attribute(
        AttributeIn(kind="ingredient", slug="niacinamide", name="Niacinamide"),
        actor_user_id=uuid4(),
    )
    assert out.slug == "niacinamide"
    assert out.kind == "ingredient"
    assert "catalog.attribute_created" in audit.actions


@pytest.mark.asyncio
async def test_patch_category_rejects_self_parent() -> None:
    service, repo, _a = _service()
    row = SimpleNamespace(
        id=uuid4(),
        parent_id=None,
        slug="mask",
        name="Mask",
        description=None,
        sort_order=1,
        is_active=True,
        deleted_at=None,
        attributes=[],
    )
    repo.categories[row.id] = row
    repo.by_slug[row.slug] = row.id
    with pytest.raises(ProblemError) as exc:
        await service.patch_category(
            row.id,
            CategoryPatchIn(parent_id=row.id),
            actor_user_id=uuid4(),
        )
    assert exc.value.status == 422
