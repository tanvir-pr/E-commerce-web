"""Catalog use cases: category tree and attributes."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import AuditService
from app.catalog.constants import ATTRIBUTE_KINDS
from app.catalog.repository import CatalogRepository
from app.catalog.schemas import (
    AttributeIn,
    AttributeListOut,
    AttributeOut,
    AttributePatchIn,
    CategoryDetailOut,
    CategoryIn,
    CategoryListOut,
    CategoryOut,
    CategoryPatchIn,
    CategoryTreeOut,
)
from app.models.catalog import Attribute, Category
from app.problems import PROBLEM_NOT_FOUND, PROBLEM_VALIDATION, ProblemError


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CatalogRepository(session)
        self.audit = AuditService(session)

    async def list_category_tree(self, *, include_inactive: bool = False) -> list[CategoryTreeOut]:
        rows = await self.repo.list_categories(include_inactive=include_inactive)
        by_id = {row.id: row for row in rows}
        children_map: dict[UUID | None, list[Category]] = {}
        for row in rows:
            children_map.setdefault(row.parent_id, []).append(row)

        def build(node: Category) -> CategoryTreeOut:
            kids = [
                build(child)
                for child in children_map.get(node.id, [])
                if child.id in by_id
            ]
            base = _category_out(node)
            return CategoryTreeOut(**base.model_dump(), children=kids)

        roots = children_map.get(None, [])
        # Orphans whose parent was filtered out become roots for this response.
        for row in rows:
            if row.parent_id is not None and row.parent_id not in by_id:
                roots.append(row)
        roots = sorted(roots, key=lambda c: (c.sort_order, c.name))
        return [build(root) for root in roots]

    async def list_categories_flat(
        self, *, include_inactive: bool = False
    ) -> CategoryListOut:
        rows = await self.repo.list_categories(include_inactive=include_inactive)
        return CategoryListOut(items=[_category_out(row) for row in rows])

    async def get_category(self, slug: str) -> CategoryDetailOut:
        row = await self.repo.get_category_by_slug(slug)
        if row is None:
            raise ProblemError(404, "Not found", "Category not found.", PROBLEM_NOT_FOUND)
        return CategoryDetailOut(
            **_category_out(row).model_dump(),
            attributes=[_attribute_out(attr) for attr in _sorted_attrs(row.attributes)],
        )

    async def create_category(
        self, body: CategoryIn, *, actor_user_id: UUID
    ) -> CategoryDetailOut:
        if body.parent_id is not None:
            await self.repo.require_category(body.parent_id)
        row = Category(
            parent_id=body.parent_id,
            slug=body.slug,
            name=body.name,
            description=body.description,
            sort_order=body.sort_order,
            is_active=body.is_active,
        )
        saved = await self.repo.add_category(row)
        if body.attribute_ids:
            saved = await self.repo.replace_category_attributes(saved, body.attribute_ids)
        await self.audit.record(
            action="catalog.category_created",
            actor_user_id=actor_user_id,
            subject_type="category",
            subject_id=str(saved.id),
        )
        return CategoryDetailOut(
            **_category_out(saved).model_dump(),
            attributes=[_attribute_out(attr) for attr in _sorted_attrs(saved.attributes)],
        )

    async def patch_category(
        self, category_id: UUID, body: CategoryPatchIn, *, actor_user_id: UUID
    ) -> CategoryDetailOut:
        row = await self.repo.require_category(category_id)
        data = body.model_dump(exclude_unset=True)
        attribute_ids = data.pop("attribute_ids", None)
        if "parent_id" in data:
            parent_id = data["parent_id"]
            if parent_id is not None:
                if parent_id == row.id:
                    raise ProblemError(
                        422,
                        "Validation error",
                        "A category cannot be its own parent.",
                        PROBLEM_VALIDATION,
                    )
                await self.repo.require_category(parent_id)
            row.parent_id = parent_id
            data.pop("parent_id", None)
        for key, value in data.items():
            setattr(row, key, value)
        saved = await self.repo.save_category(row)
        if attribute_ids is not None:
            saved = await self.repo.replace_category_attributes(saved, attribute_ids)
        await self.audit.record(
            action="catalog.category_updated",
            actor_user_id=actor_user_id,
            subject_type="category",
            subject_id=str(saved.id),
        )
        return CategoryDetailOut(
            **_category_out(saved).model_dump(),
            attributes=[_attribute_out(attr) for attr in _sorted_attrs(saved.attributes)],
        )

    async def delete_category(self, category_id: UUID, *, actor_user_id: UUID) -> None:
        row = await self.repo.require_category(category_id)
        await self.repo.soft_delete_category(row)
        await self.audit.record(
            action="catalog.category_deleted",
            actor_user_id=actor_user_id,
            subject_type="category",
            subject_id=str(category_id),
        )

    async def list_attributes(
        self, *, kind: str | None = None, include_inactive: bool = False
    ) -> AttributeListOut:
        if kind is not None and kind not in ATTRIBUTE_KINDS:
            raise ProblemError(
                422,
                "Validation error",
                f"kind must be one of: {', '.join(sorted(ATTRIBUTE_KINDS))}",
                PROBLEM_VALIDATION,
            )
        rows = await self.repo.list_attributes(kind=kind, include_inactive=include_inactive)
        return AttributeListOut(items=[_attribute_out(row) for row in rows])

    async def create_attribute(
        self, body: AttributeIn, *, actor_user_id: UUID
    ) -> AttributeOut:
        row = Attribute(
            kind=body.kind,
            slug=body.slug,
            name=body.name,
            description=body.description,
            sort_order=body.sort_order,
            is_active=body.is_active,
        )
        saved = await self.repo.add_attribute(row)
        await self.audit.record(
            action="catalog.attribute_created",
            actor_user_id=actor_user_id,
            subject_type="attribute",
            subject_id=str(saved.id),
        )
        return _attribute_out(saved)

    async def patch_attribute(
        self, attribute_id: UUID, body: AttributePatchIn, *, actor_user_id: UUID
    ) -> AttributeOut:
        row = await self.repo.require_attribute(attribute_id)
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(row, key, value)
        saved = await self.repo.save_attribute(row)
        await self.audit.record(
            action="catalog.attribute_updated",
            actor_user_id=actor_user_id,
            subject_type="attribute",
            subject_id=str(saved.id),
        )
        return _attribute_out(saved)


def _sorted_attrs(attrs: list[Attribute]) -> list[Attribute]:
    return sorted(attrs, key=lambda a: (a.kind, a.sort_order, a.name))


def _category_out(row: Category) -> CategoryOut:
    return CategoryOut(
        id=row.id,
        parent_id=row.parent_id,
        slug=row.slug,
        name=row.name,
        description=row.description,
        sort_order=row.sort_order,
        is_active=row.is_active,
        attribute_ids=[attr.id for attr in _sorted_attrs(list(row.attributes or []))],
    )


def _attribute_out(row: Attribute) -> AttributeOut:
    return AttributeOut(
        id=row.id,
        kind=row.kind,
        slug=row.slug,
        name=row.name,
        description=row.description,
        sort_order=row.sort_order,
        is_active=row.is_active,
    )
