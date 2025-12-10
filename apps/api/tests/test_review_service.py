"""Verified reviews and wishlist."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.problems import PROBLEM_FORBIDDEN, PROBLEM_VALIDATION, ProblemError
from app.reviews.schemas import ReviewIn, WishlistAddIn
from app.reviews.service import ReviewService


class FakeRepo:
    def __init__(self) -> None:
        self.product = SimpleNamespace(
            id=uuid4(),
            slug="serum",
            name="Serum",
            subtitle="Barrier",
            status="published",
            variants=[SimpleNamespace(is_active=True, price_poisha=145000)],
        )
        self.order = SimpleNamespace(id=uuid4())
        self.reviews: list[SimpleNamespace] = []
        self.wishlist: list[SimpleNamespace] = []

    async def get_product_by_slug(self, slug: str) -> SimpleNamespace | None:
        return self.product if slug == self.product.slug else None

    async def get_product(self, product_id: object) -> SimpleNamespace | None:
        return self.product if product_id == self.product.id else None

    async def require_published_product(self, product_id: object) -> SimpleNamespace:
        row = await self.get_product(product_id)
        assert row is not None
        return row

    async def get_user_review(self, *, user_id: object, product_id: object) -> SimpleNamespace | None:
        for row in self.reviews:
            if row.user_id == user_id and row.product_id == product_id:
                return row
        return None

    async def delivered_order_for_product(
        self, *, user_id: object, product_id: object
    ) -> SimpleNamespace | None:
        _ = (user_id, product_id)
        return self.order

    async def list_published_for_product(self, product_id: object) -> list[SimpleNamespace]:
        return [r for r in self.reviews if r.product_id == product_id and r.is_published]

    async def rating_stats(self, product_id: object) -> tuple[float | None, int]:
        rows = [r for r in self.reviews if r.product_id == product_id and r.is_published]
        if not rows:
            return None, 0
        avg = sum(r.rating for r in rows) / len(rows)
        return avg, len(rows)

    async def add_review(self, row: SimpleNamespace) -> SimpleNamespace:
        if not getattr(row, "id", None):
            row.id = uuid4()
        if not getattr(row, "created_at", None):
            row.created_at = datetime.now(UTC)
        self.reviews.append(row)
        return row

    async def user_display_names(self, user_ids: list[object]) -> dict[object, str]:
        return {uid: "A***" for uid in user_ids}

    async def get_wishlist_item(
        self, *, user_id: object, product_id: object
    ) -> SimpleNamespace | None:
        for row in self.wishlist:
            if row.user_id == user_id and row.product_id == product_id:
                return row
        return None

    async def add_wishlist(self, row: SimpleNamespace) -> SimpleNamespace:
        if not getattr(row, "id", None):
            row.id = uuid4()
        if not getattr(row, "created_at", None):
            row.created_at = datetime.now(UTC)
        self.wishlist.append(row)
        return row

    async def list_wishlist(
        self, user_id: object
    ) -> list[tuple[SimpleNamespace, SimpleNamespace]]:
        return [
            (row, self.product)
            for row in self.wishlist
            if row.user_id == user_id
        ]

    async def delete_wishlist(self, row: SimpleNamespace) -> None:
        self.wishlist = [r for r in self.wishlist if r.id != row.id]


class FakeUsers:
    async def get_by_id(self, _user_id: object) -> SimpleNamespace:
        return SimpleNamespace(
            display_name="Asha",
            email="asha@example.com",
            skin_type="oily",
        )


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


def _service() -> tuple[ReviewService, FakeRepo]:
    service = ReviewService(session=SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeRepo()
    service.repo = repo  # type: ignore[assignment]
    service.users = FakeUsers()  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    return service, repo


@pytest.mark.asyncio
async def test_create_verified_review() -> None:
    service, repo = _service()
    user_id = uuid4()
    out = await service.create_for_product(
        "serum",
        ReviewIn(rating=5, body="Helped my barrier a lot."),
        user_id=user_id,
    )
    assert out.is_verified is True
    assert out.rating == 5
    assert out.skin_type == "oily"
    assert len(repo.reviews) == 1


@pytest.mark.asyncio
async def test_create_requires_delivered_order() -> None:
    service, repo = _service()
    repo.order = None  # type: ignore[assignment]
    with pytest.raises(ProblemError) as exc:
        await service.create_for_product(
            "serum",
            ReviewIn(rating=4, body="Nice texture overall."),
            user_id=uuid4(),
        )
    assert exc.value.type_ == PROBLEM_FORBIDDEN


@pytest.mark.asyncio
async def test_duplicate_review_rejected() -> None:
    service, repo = _service()
    user_id = uuid4()
    await service.create_for_product(
        "serum",
        ReviewIn(rating=5, body="Helped my barrier a lot."),
        user_id=user_id,
    )
    with pytest.raises(ProblemError) as exc:
        await service.create_for_product(
            "serum",
            ReviewIn(rating=3, body="Second thoughts somehow."),
            user_id=user_id,
        )
    assert exc.value.type_ == PROBLEM_VALIDATION


@pytest.mark.asyncio
async def test_list_sets_can_review() -> None:
    service, _repo = _service()
    listed = await service.list_for_product("serum", user_id=uuid4())
    assert listed.can_review is True
    assert listed.rating_count == 0


@pytest.mark.asyncio
async def test_wishlist_add_and_list() -> None:
    service, repo = _service()
    user_id = uuid4()
    item = await service.add_wishlist(
        WishlistAddIn(product_id=repo.product.id), user_id=user_id
    )
    assert item.product_slug == "serum"
    listed = await service.list_wishlist(user_id)
    assert len(listed.items) == 1
    await service.remove_wishlist(repo.product.id, user_id=user_id)
    listed2 = await service.list_wishlist(user_id)
    assert listed2.items == []
