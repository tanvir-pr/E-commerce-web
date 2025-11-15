"""Stock reservation allocations and expiry index.

Revision ID: 0011_stock_reservations
Revises: 0010_orders
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_stock_reservations"
down_revision: str | None = "0010_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_reservation_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["batch_id"], ["stock_batches.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_stock_reservation_allocations_order_id",
        "stock_reservation_allocations",
        ["order_id"],
    )
    op.create_index(
        "ix_stock_reservation_allocations_order_item_id",
        "stock_reservation_allocations",
        ["order_item_id"],
    )
    op.create_index(
        "ix_stock_reservation_allocations_variant_id",
        "stock_reservation_allocations",
        ["variant_id"],
    )
    op.create_index(
        "ix_stock_reservation_allocations_batch_id",
        "stock_reservation_allocations",
        ["batch_id"],
    )
    op.create_index(
        "ix_stock_reservation_allocations_active",
        "stock_reservation_allocations",
        ["order_id"],
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.create_index(
        "ix_orders_reservation_expires_at",
        "orders",
        ["reservation_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_orders_reservation_expires_at", table_name="orders")
    op.drop_index(
        "ix_stock_reservation_allocations_active",
        table_name="stock_reservation_allocations",
    )
    op.drop_index(
        "ix_stock_reservation_allocations_batch_id",
        table_name="stock_reservation_allocations",
    )
    op.drop_index(
        "ix_stock_reservation_allocations_variant_id",
        table_name="stock_reservation_allocations",
    )
    op.drop_index(
        "ix_stock_reservation_allocations_order_item_id",
        table_name="stock_reservation_allocations",
    )
    op.drop_index(
        "ix_stock_reservation_allocations_order_id",
        table_name="stock_reservation_allocations",
    )
    op.drop_table("stock_reservation_allocations")
