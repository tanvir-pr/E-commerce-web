"""Order fulfilment: courier, tracking, packed_at.

Revision ID: 0012_order_fulfilment
Revises: 0011_stock_reservations
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_order_fulfilment"
down_revision: str | None = "0011_stock_reservations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("courier_name", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("tracking_number", sa.String(length=128), nullable=True))
    op.add_column(
        "orders",
        sa.Column("packed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_orders_courier_name", "orders", ["courier_name"])
    op.create_index("ix_orders_tracking_number", "orders", ["tracking_number"])


def downgrade() -> None:
    op.drop_index("ix_orders_tracking_number", table_name="orders")
    op.drop_index("ix_orders_courier_name", table_name="orders")
    op.drop_column("orders", "packed_at")
    op.drop_column("orders", "tracking_number")
    op.drop_column("orders", "courier_name")
