"""Payment event persistence."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import PaymentEvent


class PaymentEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_gateway_event(
        self, *, gateway: str, gateway_event_id: str
    ) -> PaymentEvent | None:
        result = await self.session.execute(
            select(PaymentEvent).where(
                PaymentEvent.gateway == gateway,
                PaymentEvent.gateway_event_id == gateway_event_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_status(self, status: str, *, limit: int = 100) -> list[PaymentEvent]:
        result = await self.session.execute(
            select(PaymentEvent)
            .where(PaymentEvent.status == status)
            .order_by(PaymentEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def try_insert(
        self,
        *,
        id: UUID,
        gateway: str,
        gateway_event_id: str,
        order_id: UUID,
        provider_ref: str | None,
        amount_poisha: int,
        status: str,
        source: str,
        raw_payload: dict[str, Any] | None,
    ) -> PaymentEvent | None:
        """Insert once. Returns None when gateway_event_id already exists."""
        stmt = (
            insert(PaymentEvent)
            .values(
                id=id,
                gateway=gateway,
                gateway_event_id=gateway_event_id,
                order_id=order_id,
                provider_ref=provider_ref,
                amount_poisha=amount_poisha,
                status=status,
                source=source,
                raw_payload=raw_payload,
            )
            .on_conflict_do_nothing(constraint="uq_payment_events_gateway_event")
            .returning(PaymentEvent)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            await self.session.flush()
        return row

    async def save(self, event: PaymentEvent) -> PaymentEvent:
        self.session.add(event)
        await self.session.flush()
        return event
