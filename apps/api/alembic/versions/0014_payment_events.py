"""Idempotent payment_events for gateway webhooks/returns.

Revision ID: 0014_payment_events
Revises: 0013_delivery_returns
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_payment_events"
down_revision: str | None = "0013_delivery_returns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gateway", sa.String(length=32), nullable=False),
        sa.Column("gateway_event_id", sa.String(length=128), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_ref", sa.String(length=128), nullable=True),
        sa.Column("amount_poisha", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "gateway", "gateway_event_id", name="uq_payment_events_gateway_event"
        ),
    )
    op.create_index("ix_payment_events_gateway", "payment_events", ["gateway"])
    op.create_index("ix_payment_events_order_id", "payment_events", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_payment_events_order_id", table_name="payment_events")
    op.drop_index("ix_payment_events_gateway", table_name="payment_events")
    op.drop_table("payment_events")
