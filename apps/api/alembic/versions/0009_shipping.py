"""Delivery zones and weight tiers.

Revision ID: 0009_shipping
Revises: 0008_carts
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_shipping"
down_revision: str | None = "0008_carts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "match_districts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("free_shipping_threshold_poisha", sa.Integer(), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_delivery_zones_slug"),
    )
    op.create_index("ix_delivery_zones_is_active", "delivery_zones", ["is_active"])
    op.create_index("ix_delivery_zones_is_default", "delivery_zones", ["is_default"])

    op.create_table(
        "delivery_weight_tiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("max_weight_grams", sa.Integer(), nullable=False),
        sa.Column("charge_poisha", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["zone_id"], ["delivery_zones.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "zone_id",
            "max_weight_grams",
            name="uq_delivery_weight_tiers_zone_max",
        ),
    )
    op.create_index("ix_delivery_weight_tiers_zone_id", "delivery_weight_tiers", ["zone_id"])

    # Seed Bangladesh baseline zones (poisha = BDT * 100).
    # asyncpg rejects multi-statement prepared SQL — keep each execute as one command.
    op.execute(
        sa.text(
            """
            INSERT INTO delivery_zones (
              id, slug, name, match_districts, is_default, is_active, sort_order,
              free_shipping_threshold_poisha
            ) VALUES
            (
              '019a0000-0000-7000-8000-000000000001',
              'dhaka-metro',
              'Dhaka metro',
              '["Dhaka","Gazipur","Narayanganj"]'::jsonb,
              false,
              true,
              10,
              250000
            ),
            (
              '019a0000-0000-7000-8000-000000000002',
              'rest-of-bangladesh',
              'Rest of Bangladesh',
              '[]'::jsonb,
              true,
              true,
              100,
              350000
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO delivery_weight_tiers (id, zone_id, max_weight_grams, charge_poisha) VALUES
            ('019a0000-0000-7000-8000-000000000011', '019a0000-0000-7000-8000-000000000001', 500, 6000),
            ('019a0000-0000-7000-8000-000000000012', '019a0000-0000-7000-8000-000000000001', 1000, 8000),
            ('019a0000-0000-7000-8000-000000000013', '019a0000-0000-7000-8000-000000000001', 50000, 12000),
            ('019a0000-0000-7000-8000-000000000021', '019a0000-0000-7000-8000-000000000002', 500, 12000),
            ('019a0000-0000-7000-8000-000000000022', '019a0000-0000-7000-8000-000000000002', 1000, 15000),
            ('019a0000-0000-7000-8000-000000000023', '019a0000-0000-7000-8000-000000000002', 50000, 20000)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_weight_tiers_zone_id", table_name="delivery_weight_tiers")
    op.drop_table("delivery_weight_tiers")
    op.drop_index("ix_delivery_zones_is_default", table_name="delivery_zones")
    op.drop_index("ix_delivery_zones_is_active", table_name="delivery_zones")
    op.drop_table("delivery_zones")
