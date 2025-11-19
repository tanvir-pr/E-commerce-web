"""Delivery failed / returned timestamps and allocation restock flag.

Revision ID: 0013_delivery_returns
Revises: 0012_order_fulfilment
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_delivery_returns"
down_revision: str | None = "0012_order_fulfilment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("delivery_failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "stock_reservation_allocations",
        sa.Column("restocked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_stock_reservation_allocations_restock",
        "stock_reservation_allocations",
        ["order_id"],
        postgresql_where=sa.text("consumed IS true AND restocked_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_reservation_allocations_restock",
        table_name="stock_reservation_allocations",
    )
    op.drop_column("stock_reservation_allocations", "restocked_at")
    op.drop_column("orders", "returned_at")
    op.drop_column("orders", "delivery_failed_at")
