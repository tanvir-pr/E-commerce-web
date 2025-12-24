"""Support tickets and notification preferences.

Revision ID: 0018_support_notifications
Revises: 0017_reviews_wishlist
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_support_notifications"
down_revision: str | None = "0017_reviews_wishlist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_updates", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("marketing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stock_back", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("support_replies", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "support_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"])
    op.create_index("ix_support_tickets_topic", "support_tickets", ["topic"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_staff", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["support_tickets.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_support_ticket_messages_ticket_id", table_name="support_ticket_messages"
    )
    op.drop_table("support_ticket_messages")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_topic", table_name="support_tickets")
    op.drop_index("ix_support_tickets_user_id", table_name="support_tickets")
    op.drop_table("support_tickets")
    op.drop_table("notification_preferences")
