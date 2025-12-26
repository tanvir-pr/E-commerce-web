"""Feature flags and order fraud_score.

Revision ID: 0019_feature_flags_fraud
Revises: 0018_support_notifications
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_feature_flags_fraud"
down_revision: str | None = "0018_support_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_FLAGS = [
    ("checkout_enabled", True, None, "Master kill switch for placing orders"),
    ("cod_enabled", True, None, "Allow cash-on-delivery at checkout"),
    ("bkash_enabled", True, None, "Allow bKash prepaid checkout"),
    ("sslcommerz_enabled", True, None, "Allow SSLCommerz prepaid checkout"),
    (
        "cod_fraud_check_enabled",
        True,
        {"block_threshold": 70, "high_value_poisha": 500000},
        "Score COD risk and block above threshold",
    ),
]


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_feature_flags_key", "feature_flags", ["key"])

    op.add_column(
        "orders",
        sa.Column("fraud_score", sa.Integer(), nullable=True),
    )

    flags = sa.table(
        "feature_flags",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    import uuid

    from uuid_utils import uuid7

    op.bulk_insert(
        flags,
        [
            {
                "id": uuid.UUID(str(uuid7())),
                "key": key,
                "enabled": enabled,
                "value": value,
                "description": description,
            }
            for key, enabled, value, description in DEFAULT_FLAGS
        ],
    )


def downgrade() -> None:
    op.drop_column("orders", "fraud_score")
    op.drop_index("ix_feature_flags_key", table_name="feature_flags")
    op.drop_table("feature_flags")
