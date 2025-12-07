"""RMA tables and append-only ledger.

Revision ID: 0015_returns_ledger
Revises: 0014_payment_events
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_returns_ledger"
down_revision: str | None = "0014_payment_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "return_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("customer_note", sa.Text(), nullable=True),
        sa.Column("staff_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_return_requests_order_id", "return_requests", ["order_id"])
    op.create_index("ix_return_requests_user_id", "return_requests", ["user_id"])
    op.create_index("ix_return_requests_status", "return_requests", ["status"])

    op.create_table(
        "return_request_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_price_poisha", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["return_request_id"], ["return_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "return_request_id", "order_item_id", name="uq_return_request_items_line"
        ),
    )
    op.create_index(
        "ix_return_request_items_return_request_id",
        "return_request_items",
        ["return_request_id"],
    )

    op.create_table(
        "return_request_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relative_path", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["return_request_id"], ["return_requests.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_return_request_photos_return_request_id",
        "return_request_photos",
        ["return_request_id"],
    )

    op.create_table(
        "ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_poisha", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("return_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("gateway_refund_ref", sa.String(length=128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["return_request_id"], ["return_requests.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ledger_entries_order_id", "ledger_entries", ["order_id"])
    op.create_index("ix_ledger_entries_entry_type", "ledger_entries", ["entry_type"])


def downgrade() -> None:
    op.drop_index("ix_ledger_entries_entry_type", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_order_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index(
        "ix_return_request_photos_return_request_id", table_name="return_request_photos"
    )
    op.drop_table("return_request_photos")
    op.drop_index(
        "ix_return_request_items_return_request_id", table_name="return_request_items"
    )
    op.drop_table("return_request_items")
    op.drop_index("ix_return_requests_status", table_name="return_requests")
    op.drop_index("ix_return_requests_user_id", table_name="return_requests")
    op.drop_index("ix_return_requests_order_id", table_name="return_requests")
    op.drop_table("return_requests")
