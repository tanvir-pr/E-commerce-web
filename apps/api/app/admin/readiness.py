"""Launch / security readiness report for staff."""

from __future__ import annotations

from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.schemas import LaunchCheckOut, LaunchReadinessOut
from app.config import Settings, get_settings
from app.flags.service import FeatureFlagService
from app.health import probe_health
from app.models.role import Role, UserRole
from app.models.user import User
from app.rbac import STAFF_ROLES

EXPECTED_ALEMBIC = "0020_assistant_rag"
CheckStatus = Literal["pass", "fail", "warn", "manual"]


class LaunchReadinessService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        *,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings or get_settings()
        self.flags = FeatureFlagService(session)

    async def report(self) -> LaunchReadinessOut:
        checks: list[LaunchCheckOut] = []
        health = await probe_health(self.session, self.redis)

        checks.append(
            self._check(
                "health_db",
                "Postgres reachable",
                "pass" if health.db == "ok" else "fail",
                health.db,
            )
        )
        checks.append(
            self._check(
                "health_redis",
                "Redis reachable",
                "pass" if health.redis == "ok" else "fail",
                health.redis,
            )
        )
        if self.settings.search_enabled:
            checks.append(
                self._check(
                    "health_search",
                    "Meilisearch reachable",
                    "pass" if health.search == "ok" else "fail",
                    health.search,
                )
            )
        else:
            checks.append(
                self._check(
                    "health_search",
                    "Meilisearch",
                    "warn",
                    "search_enabled=false",
                )
            )

        alembic = await self._alembic_version()
        checks.append(
            self._check(
                "migrations",
                f"Alembic head is {EXPECTED_ALEMBIC}",
                "pass" if alembic == EXPECTED_ALEMBIC else "fail",
                alembic or "unknown",
            )
        )

        env = self.settings.app_env
        checks.append(
            self._check(
                "app_env",
                "APP_ENV is not accidental production secrets leak",
                "pass" if env in {"local", "test", "staging", "production"} else "warn",
                env,
            )
        )

        pay_mode = self.settings.payment_gateway_mode
        checks.append(
            self._check(
                "payment_mode",
                "Payment gateway mode",
                "warn" if pay_mode != "live" else "pass",
                f"{pay_mode} — confirm sandbox vs live before launch",
            )
        )

        checks.append(
            self._check(
                "smtp",
                "SMTP host configured",
                "pass" if bool(self.settings.smtp_host) else "fail",
                f"{self.settings.smtp_host}:{self.settings.smtp_port}",
            )
        )

        jwt = self.settings.jwt_secret
        checks.append(
            self._check(
                "jwt_secret",
                "JWT secret is not the local default",
                "fail" if jwt == "local-dev-only-change-me" and env == "production" else (
                    "warn" if jwt == "local-dev-only-change-me" else "pass"
                ),
                "default" if jwt == "local-dev-only-change-me" else "custom",
            )
        )

        for key in (
            "checkout_enabled",
            "cod_enabled",
            "bkash_enabled",
            "sslcommerz_enabled",
            "assistant_enabled",
        ):
            on = await self.flags.is_enabled(key, default=True)
            checks.append(
                self._check(
                    f"flag_{key}",
                    f"Feature flag {key}",
                    "pass" if on else "warn",
                    "enabled" if on else "disabled",
                )
            )

        staff_total, staff_missing_2fa = await self._staff_2fa_counts()
        checks.append(
            self._check(
                "staff_2fa",
                "All staff have TOTP enrolled",
                "pass" if staff_missing_2fa == 0 else "fail",
                f"{staff_total - staff_missing_2fa}/{staff_total} enrolled",
            )
        )

        checks.extend(
            [
                self._check(
                    "backup_drill",
                    "Monthly Postgres backup restore drill signed off",
                    "manual",
                    "See docs/runbooks/backup-restore-drill.md",
                ),
                self._check(
                    "oversell_load",
                    "Oversell concurrency script run (stock M, N buyers)",
                    "manual",
                    "python -m app.scripts.oversell_load_test --help",
                ),
                self._check(
                    "live_payment",
                    "One live bKash + SSLCommerz transaction verified",
                    "manual",
                    "Required before flipping payment_gateway_mode=live",
                ),
                self._check(
                    "policies",
                    "Privacy, terms, shipping, returns pages published",
                    "manual",
                    "Confirm legal pages on the storefront",
                ),
                self._check(
                    "rollback",
                    "Rollback plan documented (image tag + alembic downgrade)",
                    "manual",
                    "Keep previous image + DB snapshot before deploy",
                ),
            ]
        )

        blocking = sum(1 for c in checks if c.status == "fail")
        manual = sum(1 for c in checks if c.status == "manual")
        ready = blocking == 0 and manual == 0
        return LaunchReadinessOut(
            ready_for_launch=ready,
            blocking_failures=blocking,
            manual_items=manual,
            expected_alembic=EXPECTED_ALEMBIC,
            checks=checks,
        )

    def _check(
        self, key: str, title: str, status: CheckStatus, detail: str
    ) -> LaunchCheckOut:
        return LaunchCheckOut(key=key, title=title, status=status, detail=detail)

    async def _alembic_version(self) -> str | None:
        try:
            result = await self.session.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.scalar_one_or_none()
            return str(row) if row else None
        except Exception:
            return None

    async def _staff_2fa_counts(self) -> tuple[int, int]:
        result = await self.session.execute(
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name.in_(tuple(STAFF_ROLES)), User.deleted_at.is_(None))
            .distinct()
        )
        staff = list(result.scalars().unique().all())
        missing = sum(1 for u in staff if u.totp_confirmed_at is None)
        return len(staff), missing
