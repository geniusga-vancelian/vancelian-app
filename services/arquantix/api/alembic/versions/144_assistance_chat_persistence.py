"""MVP Assistance — persistence chat IA mobile (`assistance_conversations`, `assistance_messages`).

Découplé du `chatbot_epargne` (funnel projet épargne) : ces tables stockent les conversations
génériques de l'« Assistance sur mesure » du Search Screen Flutter, scopées par `client_id`.

Revision ID: 144
Revises: 143
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "144"
down_revision = "143"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistance_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active','closed')",
            name="ck_assistance_conversations_status",
        ),
        schema="public",
    )
    op.create_index(
        "ix_assistance_conversations_client_last",
        "assistance_conversations",
        ["client_id", "last_message_at"],
        postgresql_using="btree",
        schema="public",
    )
    op.create_index(
        "ix_assistance_conversations_client_status",
        "assistance_conversations",
        ["client_id", "status"],
        schema="public",
    )

    op.create_table(
        "assistance_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.assistance_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "role IN ('user','assistant')",
            name="ck_assistance_messages_role",
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "turn_index",
            name="uq_assistance_messages_conversation_turn",
        ),
        schema="public",
    )
    op.create_index(
        "ix_assistance_messages_conversation_created",
        "assistance_messages",
        ["conversation_id", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistance_messages_conversation_created",
        table_name="assistance_messages",
        schema="public",
    )
    op.drop_table("assistance_messages", schema="public")
    op.drop_index(
        "ix_assistance_conversations_client_status",
        table_name="assistance_conversations",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_conversations_client_last",
        table_name="assistance_conversations",
        schema="public",
    )
    op.drop_table("assistance_conversations", schema="public")
