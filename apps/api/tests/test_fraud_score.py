"""COD fraud scoring and feature-flag gating."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.checkout.schemas import CheckoutAddressSnapshotOut, CheckoutQuoteOut
from app.flags.fraud import score_cod_risk
from app.flags.schemas import FeatureFlagPatchIn
from app.flags.service import FeatureFlagService
from app.problems import PROBLEM_VALIDATION, ProblemError


def test_score_increases_for_risk_signals() -> None:
    score, reasons = score_cod_risk(
        total_poisha=600000,
        high_value_poisha=500000,
        email_verified=False,
        phone_verified=False,
        address_phone=None,
        address_district=None,
        account_created_at=datetime.now(UTC) - timedelta(days=1),
        cancelled_cod_count=2,
    )
    assert score >= 70
    assert "high_order_value" in reasons
    assert "phone_unverified" in reasons
    assert "cancelled_cod_x2" in reasons


def test_low_risk_score() -> None:
    score, reasons = score_cod_risk(
        total_poisha=10000,
        high_value_poisha=500000,
        email_verified=True,
        phone_verified=True,
        address_phone="01700000000",
        address_district="Dhaka",
        account_created_at=datetime.now(UTC) - timedelta(days=90),
        cancelled_cod_count=0,
    )
    assert score == 0
    assert reasons == []


class FakeFlagRepo:
    def __init__(self) -> None:
        self.by_key: dict[str, SimpleNamespace] = {
            "checkout_enabled": SimpleNamespace(
                id=uuid4(),
                key="checkout_enabled",
                enabled=True,
                value=None,
                description=None,
                updated_at=datetime.now(UTC),
            ),
            "cod_enabled": SimpleNamespace(
                id=uuid4(),
                key="cod_enabled",
                enabled=True,
                value=None,
                description=None,
                updated_at=datetime.now(UTC),
            ),
            "cod_fraud_check_enabled": SimpleNamespace(
                id=uuid4(),
                key="cod_fraud_check_enabled",
                enabled=True,
                value={"block_threshold": 50, "high_value_poisha": 100000},
                description=None,
                updated_at=datetime.now(UTC),
            ),
        }

    async def get_by_key(self, key: str) -> SimpleNamespace | None:
        return self.by_key.get(key)

    async def list_all(self) -> list[SimpleNamespace]:
        return list(self.by_key.values())

    async def require(self, flag_id: object) -> SimpleNamespace:
        for row in self.by_key.values():
            if row.id == flag_id:
                return row
        raise AssertionError("missing")

    async def save(self, row: SimpleNamespace) -> SimpleNamespace:
        self.by_key[row.key] = row
        return row

    async def count_cancelled_cod(self, _user_id: object) -> int:
        return 3


class FakeUsers:
    async def get_by_id(self, _user_id: object) -> SimpleNamespace:
        return SimpleNamespace(
            email_verified_at=None,
            phone_verified_at=None,
            created_at=datetime.now(UTC),
        )


class FakeAudit:
    async def record(self, **_kwargs: object) -> None:
        return None


def _quote(total: int = 200000) -> CheckoutQuoteOut:
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from uuid import uuid4 as _uuid4

    from app.cart.schemas import CartOut
    from app.checkout.schemas import CheckoutContactOut
    from app.shipping.schemas import ShippingQuoteOut

    now = _dt.now(_UTC)
    return CheckoutQuoteOut(
        cart=CartOut(
            id=_uuid4(),
            status="active",
            item_count=1,
            subtotal_poisha=total - 6000,
            is_guest=False,
            updated_at=now,
            last_activity_at=now,
            items=[],
        ),
        address=CheckoutAddressSnapshotOut(
            line1="12 Road",
            city="Dhaka",
            district=None,
            phone=None,
            country="BD",
        ),
        shipping=ShippingQuoteOut(
            zone_id=_uuid4(),
            zone_slug="dhaka",
            zone_name="Dhaka",
            total_weight_grams=100,
            charge_poisha=6000,
            free_shipping_applied=False,
            free_shipping_threshold_poisha=300000,
            matched_by="district",
        ),
        stock=[],
        contact=CheckoutContactOut(email_verified=True, phone_verified=False, ok=True),
        merchandise_subtotal_poisha=total - 6000,
        shipping_poisha=6000,
        total_poisha=total,
        ready=True,
        blockers=[],
        quoted_at=now,
        place_order_available=True,
    )


@pytest.mark.asyncio
async def test_assert_can_place_blocks_disabled_cod() -> None:
    service = FeatureFlagService(session=SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeFlagRepo()
    repo.by_key["cod_enabled"].enabled = False
    service.repo = repo  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    with pytest.raises(ProblemError) as exc:
        await service.assert_can_place("cod")
    assert exc.value.type_ == PROBLEM_VALIDATION


@pytest.mark.asyncio
async def test_evaluate_cod_blocks_high_score() -> None:
    service = FeatureFlagService(session=SimpleNamespace())  # type: ignore[arg-type]
    service.repo = FakeFlagRepo()  # type: ignore[assignment]
    service.users = FakeUsers()  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    with pytest.raises(ProblemError) as exc:
        await service.evaluate_cod(user_id=uuid4(), quote=_quote(200000))
    assert "COD is unavailable" in exc.value.detail


@pytest.mark.asyncio
async def test_patch_flag() -> None:
    service = FeatureFlagService(session=SimpleNamespace())  # type: ignore[arg-type]
    repo = FakeFlagRepo()
    service.repo = repo  # type: ignore[assignment]
    service.audit = FakeAudit()  # type: ignore[assignment]
    flag_id = repo.by_key["cod_enabled"].id
    out = await service.patch(
        flag_id,
        FeatureFlagPatchIn(enabled=False),
        actor_user_id=uuid4(),
    )
    assert out.enabled is False
