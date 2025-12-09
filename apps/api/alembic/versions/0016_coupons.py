"""Coupons, redemptions, and order discount columns.

Revision ID: 0016_coupons
Revises: 0015_returns_ledger
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_coupons"
down_revision: str | None = "0015_returns_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("discount_type", sa.String(length=16), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("min_spend_poisha", sa.Integer(), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("max_per_user", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"])
    op.create_index("ix_coupons_category_id", "coupons", ["category_id"])

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("discount_poisha", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_coupon_redemptions_order"),
    )
    op.create_index("ix_coupon_redemptions_coupon_id", "coupon_redemptions", ["coupon_id"])
    op.create_index("ix_coupon_redemptions_user_id", "coupon_redemptions", ["user_id"])

    op.add_column(
        "orders",
        sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("orders", sa.Column("coupon_code", sa.String(length=64), nullable=True))
    op.add_column(
        "orders",
        sa.Column("discount_poisha", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_orders_coupon_id",
        "orders",
        "coupons",
        ["coupon_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_coupon_id", "orders", type_="foreignkey")
    op.drop_column("orders", "discount_poisha")
    op.drop_column("orders", "coupon_code")
    op.drop_column("orders", "coupon_id")
    op.drop_index("ix_coupon_redemptions_user_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")
    op.drop_index("ix_coupons_category_id", table_name="coupons")
    op.drop_index("ix_coupons_code", table_name="coupons")
    op.drop_table("coupons")
