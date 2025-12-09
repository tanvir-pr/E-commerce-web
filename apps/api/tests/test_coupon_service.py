"""Coupon apply: percent/fixed, min spend, category, expiry, limits."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.cart.schemas import CartItemOut, CartOut
from app.coupons.schemas import CouponIn
from app.coupons.service import CouponService
from app.problems import PROBLEM_VALIDATION, ProblemError


def _cart(*, subtotal: int = 100000, category_slug: str = "serum") -> CartOut:
    now = datetime.now(UTC)
    return CartOut(
        id=uuid4(),
        status="active",
        item_count=1,
        subtotal_poisha=subtotal,
        is_guest=False,
        updated_at=now,
        last_activity_at=now,
        items=[
            CartItemOut(
                id=uuid4(),
                variant_id=uuid4(),
                product_id=uuid4(),
                product_slug="serum",
                product_name="Serum",
                size_label="30ml",
                shade_name=None,
                spf=None,
                sku="SER-1",
                qty=1,
                unit_price_poisha=subtotal,
                line_total_poisha=subtotal,
                routine_step=None,
                category_slug=category_slug,
                qty_available=5,
            )
        ],
    )


class FakeRepo:
    def __init__(self) -> None:
        self.by_code: dict[str, SimpleNamespace] = {}
        self.redemptions: dict[object, int] = {}
        self.user_redemptions: dict[tuple[object, object], int] = {}
        self.category_slugs: dict[object, str] = {}
        self.rows: list[SimpleNamespace] = []

    async def get_by_code(self, code: str) -> SimpleNamespace | None:
        return self.by_code.get(code.strip().upper())

    async def redemption_count(self, coupon_id: object) -> int:
        return self.redemptions.get(coupon_id, 0)

    async def user_redemption_count(self, coupon_id: object, user_id: object) -> int:
        return self.user_redemptions.get((coupon_id, user_id), 0)

    async def category_slug(self, category_id: object) -> str | None:
        return self.category_slugs.get(category_id)

    async def list_all(self) -> list[SimpleNamespace]:
        return list(self.rows)

    async def add(self, row: SimpleNamespace) -> SimpleNamespace:
        if not getattr(row, "id", None):
            row.id = uuid4()
        if not getattr(row, "created_at", None):
            row.created_at = datetime.now(UTC)
        self.rows.append(row)
        self.by_code[row.code] = row
        return row

    async def save(self, row: SimpleNamespace) -> SimpleNamespace:
        self.by_code[row.code] = row
        return row

    async def require(self, coupon_id: object) -> SimpleNamespace:
        for row in self.rows:
            if row.id == coupon_id:
                return row
        raise ProblemError(404, "Not found", "Coupon not found.", "about:blank")

    async def delete(self, row: SimpleNamespace) -> None:
        self.rows = [r for r in self.rows if r.id != row.id]
        self.by_code.pop(row.code, None)

    async def add_redemption(self, row: SimpleNamespace) -> SimpleNamespace:
        self.redemptions[row.coupon_id] = self.redemptions.get(row.coupon_id, 0) + 1
        key = (row.coupon_id, row.user_id)
        self.user_redemptions[key] = self.user_redemptions.get(key, 0) + 1
        return row


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


def _service() -> tuple[CouponService, FakeRepo]:
    service = CouponService(session=SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeRepo()
    service.repo = repo  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    return service, repo


def _coupon(**kwargs: object) -> SimpleNamespace:
    base = {
        "id": uuid4(),
        "code": "SAVE10",
        "discount_type": "percent",
        "value": 10,
        "min_spend_poisha": None,
        "category_id": None,
        "starts_at": None,
        "expires_at": None,
        "max_redemptions": None,
        "max_per_user": None,
        "is_active": True,
        "created_at": datetime.now(UTC),
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_percent_discount_applies() -> None:
    service, repo = _service()
    coupon = _coupon(code="SAVE10", discount_type="percent", value=10)
    repo.by_code["SAVE10"] = coupon
    result = await service.apply_to_cart(
        "save10", cart=_cart(subtotal=100000), user_id=uuid4()
    )
    assert result.ok is True
    assert result.discount_poisha == 10000


@pytest.mark.asyncio
async def test_fixed_capped_to_eligible() -> None:
    service, repo = _service()
    coupon = _coupon(code="FLAT", discount_type="fixed", value=50000)
    repo.by_code["FLAT"] = coupon
    result = await service.apply_to_cart(
        "FLAT", cart=_cart(subtotal=20000), user_id=uuid4()
    )
    assert result.ok is True
    assert result.discount_poisha == 20000


@pytest.mark.asyncio
async def test_min_spend_soft_fail() -> None:
    service, repo = _service()
    coupon = _coupon(code="BIG", min_spend_poisha=200000)
    repo.by_code["BIG"] = coupon
    result = await service.apply_to_cart(
        "BIG", cart=_cart(subtotal=100000), user_id=uuid4(), strict=False
    )
    assert result.ok is False
    assert result.discount_poisha == 0
    assert result.message is not None


@pytest.mark.asyncio
async def test_min_spend_strict_raises() -> None:
    service, repo = _service()
    coupon = _coupon(code="BIG", min_spend_poisha=200000)
    repo.by_code["BIG"] = coupon
    with pytest.raises(ProblemError) as exc:
        await service.apply_to_cart(
            "BIG", cart=_cart(subtotal=100000), user_id=uuid4(), strict=True
        )
    assert exc.value.type_ == PROBLEM_VALIDATION


@pytest.mark.asyncio
async def test_category_limits_eligible_subtotal() -> None:
    service, repo = _service()
    cat_id = uuid4()
    coupon = _coupon(code="SERUM", category_id=cat_id, discount_type="fixed", value=5000)
    repo.by_code["SERUM"] = coupon
    repo.category_slugs[cat_id] = "serum"
    result = await service.apply_to_cart(
        "SERUM",
        cart=_cart(subtotal=100000, category_slug="cleanser"),
        user_id=uuid4(),
    )
    assert result.ok is False


@pytest.mark.asyncio
async def test_expired_coupon_rejected() -> None:
    service, repo = _service()
    coupon = _coupon(
        code="OLD",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    repo.by_code["OLD"] = coupon
    result = await service.apply_to_cart("OLD", cart=_cart(), user_id=uuid4())
    assert result.ok is False


@pytest.mark.asyncio
async def test_max_redemptions_enforced() -> None:
    service, repo = _service()
    coupon = _coupon(code="ONCE", max_redemptions=1)
    repo.by_code["ONCE"] = coupon
    repo.redemptions[coupon.id] = 1
    result = await service.apply_to_cart("ONCE", cart=_cart(), user_id=uuid4())
    assert result.ok is False


@pytest.mark.asyncio
async def test_create_rejects_bad_percent() -> None:
    service, _repo = _service()
    with pytest.raises(ProblemError):
        await service.create(
            CouponIn(code="BAD", discount_type="percent", value=150),
            actor_user_id=uuid4(),
        )
