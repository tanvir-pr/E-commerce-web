"""Stock batches and stock_movements ledger.

Revision ID: 0007_inventory
Revises: 0006_product_images
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_inventory"
down_revision: str | None = "0006_product_images"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lot_code", sa.String(length=64), nullable=True),
        sa.Column("qty_on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("variant_id", "lot_code", name="uq_stock_batches_variant_lot"),
    )
    op.create_index("ix_stock_batches_variant_id", "stock_batches", ["variant_id"])
    op.create_index("ix_stock_batches_expires_on", "stock_batches", ["expires_on"])

    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qty_delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["stock_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_stock_movements_variant_id", "stock_movements", ["variant_id"])
    op.create_index("ix_stock_movements_batch_id", "stock_movements", ["batch_id"])
    op.create_index("ix_stock_movements_reason", "stock_movements", ["reason"])


def downgrade() -> None:
    op.drop_index("ix_stock_movements_reason", table_name="stock_movements")
    op.drop_index("ix_stock_movements_batch_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_variant_id", table_name="stock_movements")
    op.drop_table("stock_movements")
    op.drop_index("ix_stock_batches_expires_on", table_name="stock_batches")
    op.drop_index("ix_stock_batches_variant_id", table_name="stock_batches")
    op.drop_table("stock_batches")
