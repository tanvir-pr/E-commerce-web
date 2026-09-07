"""Launch readiness gate aggregation."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.admin.readiness import LaunchReadinessService
from app.admin.schemas import LaunchCheckOut


class FakeFlags:
    async def is_enabled(self, key: str, *, default: bool = True) -> bool:
        return True


@pytest.mark.asyncio
async def test_readiness_report_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LaunchReadinessService(
        session=SimpleNamespace(),  # type: ignore[arg-type]
        redis=SimpleNamespace(),  # type: ignore[arg-type]
        settings=SimpleNamespace(
            app_env="local",
            payment_gateway_mode="sandbox",
            smtp_host="mailpit",
            smtp_port=1025,
            jwt_secret="local-dev-only-change-me",
            search_enabled=True,
        ),
    )
    service.flags = FakeFlags()  # type: ignore[assignment]

    async def fake_health(_session: object, _redis: object) -> SimpleNamespace:
        return SimpleNamespace(db="ok", redis="ok", search="ok")

    monkeypatch.setattr("app.admin.readiness.probe_health", fake_health)

    async def fake_alembic(self: LaunchReadinessService) -> str:
        return "0020_assistant_rag"

    async def fake_staff(self: LaunchReadinessService) -> tuple[int, int]:
        return 2, 0

    monkeypatch.setattr(LaunchReadinessService, "_alembic_version", fake_alembic)
    monkeypatch.setattr(LaunchReadinessService, "_staff_2fa_counts", fake_staff)

    out = await service.report()
    assert out.expected_alembic == "0020_assistant_rag"
    assert out.blocking_failures == 0
    assert out.manual_items >= 1
    assert out.ready_for_launch is False  # manuals remain
    assert all(isinstance(c, LaunchCheckOut) for c in out.checks)
    keys = {c.key for c in out.checks}
    assert "migrations" in keys
    assert "staff_2fa" in keys
    assert "backup_drill" in keys
