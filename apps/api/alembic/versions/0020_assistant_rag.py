"""RAG assistant conversations, knowledge chunks, feature flag.

Revision ID: 0020_assistant_rag
Revises: 0019_feature_flags_fraud
Create Date: 2026-11-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_assistant_rag"
down_revision: str | None = "0019_feature_flags_fraud"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICY_CHUNKS = [
    (
        "shipping",
        "Delivery in Bangladesh",
        "We ship across Bangladesh. Delivery charges depend on zone and package weight. "
        "Orders over the free-shipping threshold (default ৳3,000) ship free when the zone allows. "
        "After packing you receive a tracking email. Cash on delivery (COD) is available when enabled.",
        ["shipping", "delivery", "zone", "free shipping", "cod"],
    ),
    (
        "returns",
        "Returns and refunds",
        "Unopened products in original packaging may be returned within the stated window after delivery. "
        "Opened or used skincare generally cannot be returned for hygiene. "
        "Approved returns are refunded to the original prepaid method or as store credit for COD. "
        "Start a return from your order page or open a support ticket.",
        ["return", "refund", "unopened", "rma", "exchange"],
    ),
    (
        "payments",
        "Payment methods",
        "You can pay with Cash on Delivery (COD), bKash, or SSLCommerz (card/mobile banking) when those methods are enabled. "
        "Card numbers never touch our servers. Prepaid orders hold stock briefly until payment completes. "
        "COD confirms immediately and you pay the courier on delivery.",
        ["payment", "bkash", "sslcommerz", "cod", "cash on delivery", "card"],
    ),
    (
        "privacy",
        "Privacy basics",
        "We collect account email, delivery address, phone when provided, and order history to fulfil orders and prevent fraud. "
        "Marketing email only with consent. You can update or delete account data from Account settings, or email privacy@example.com.",
        ["privacy", "data", "personal", "gdpr", "delete account"],
    ),
    (
        "routine",
        "Building a simple routine",
        "A barrier-led routine usually goes: cleanser → treatment (serum) → moisturizer → sunscreen (AM). "
        "Introduce one active at a time. Match skin type and concern filters in Shop. "
        "Ask about a specific ingredient or concern and we will suggest catalog products with live price and stock.",
        ["routine", "am", "pm", "cleanser", "serum", "moisturizer", "sunscreen", "barrier"],
    ),
    (
        "ingredients",
        "Ingredient questions",
        "Product pages list ingredients and how-to-use. Common actives include niacinamide, hyaluronic acid, "
        "salicylic acid, vitamin C, and ceramides. Patch-test new products. We are not a medical clinic — "
        "for allergies or prescriptions, talk to a dermatologist and open a support ticket if you need staff help.",
        ["ingredient", "niacinamide", "retinol", "acid", "ceramide", "allergy"],
    ),
]


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_source", "knowledge_chunks", ["source"])

    op.create_table(
        "assistant_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assistant_conversations_user_id", "assistant_conversations", ["user_id"])
    op.create_index("ix_assistant_conversations_status", "assistant_conversations", ["status"])

    op.create_table(
        "assistant_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("product_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["assistant_conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assistant_messages_conversation_id",
        "assistant_messages",
        ["conversation_id"],
    )

    import uuid

    from uuid_utils import uuid7

    chunks = sa.table(
        "knowledge_chunks",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("source", sa.String),
        sa.column("title", sa.String),
        sa.column("body", sa.Text),
        sa.column("tags", postgresql.JSONB),
        sa.column("locale", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        chunks,
        [
            {
                "id": uuid.UUID(str(uuid7())),
                "source": source,
                "title": title,
                "body": body,
                "tags": tags,
                "locale": "en",
                "is_active": True,
            }
            for source, title, body, tags in POLICY_CHUNKS
        ],
    )

    flags = sa.table(
        "feature_flags",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("value", postgresql.JSONB),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        flags,
        [
            {
                "id": uuid.UUID(str(uuid7())),
                "key": "assistant_enabled",
                "enabled": True,
                "value": None,
                "description": "Kill switch for the shopping / policy assistant",
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM feature_flags WHERE key = 'assistant_enabled'")
    op.drop_index("ix_assistant_messages_conversation_id", table_name="assistant_messages")
    op.drop_table("assistant_messages")
    op.drop_index("ix_assistant_conversations_status", table_name="assistant_conversations")
    op.drop_index("ix_assistant_conversations_user_id", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")
    op.drop_index("ix_knowledge_chunks_source", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
