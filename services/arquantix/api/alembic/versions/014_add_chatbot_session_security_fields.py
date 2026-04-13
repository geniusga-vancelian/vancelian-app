"""add_chatbot_session_security_fields

Revision ID: 014
Revises: 013
Create Date: 2026-01-21

Add expires_at, ip_hash, user_agent_hash to chatbot_sessions for public access security.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TABLE public.chatbot_sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE"))
        op.execute(sa.text("ALTER TABLE public.chatbot_sessions ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(64)"))
        op.execute(sa.text("ALTER TABLE public.chatbot_sessions ADD COLUMN IF NOT EXISTS user_agent_hash VARCHAR(64)"))
        op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_chatbot_sessions_expires_at ON public.chatbot_sessions (expires_at)"))
    else:
        op.add_column(
            "chatbot_sessions",
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            schema="public",
        )
        op.add_column(
            "chatbot_sessions",
            sa.Column("ip_hash", sa.String(64), nullable=True),
            schema="public",
        )
        op.add_column(
            "chatbot_sessions",
            sa.Column("user_agent_hash", sa.String(64), nullable=True),
            schema="public",
        )
        op.create_index(
            "ix_chatbot_sessions_expires_at",
            "chatbot_sessions",
            ["expires_at"],
            schema="public",
        )


def downgrade() -> None:
    op.drop_index("ix_chatbot_sessions_expires_at", table_name="chatbot_sessions", schema="public")
    op.drop_column("chatbot_sessions", "user_agent_hash", schema="public")
    op.drop_column("chatbot_sessions", "ip_hash", schema="public")
    op.drop_column("chatbot_sessions", "expires_at", schema="public")
