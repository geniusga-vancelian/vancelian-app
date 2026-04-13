"""add_conversation_summary_fields

Revision ID: 013
Revises: 012
Create Date: 2026-01-21

Add conversation_summary and conversation_facts to chatbot_sessions for narrative memory.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS so migration does not fail when columns were added manually or by a previous run
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TABLE public.chatbot_sessions ADD COLUMN IF NOT EXISTS conversation_summary TEXT"))
        op.execute(sa.text("ALTER TABLE public.chatbot_sessions ADD COLUMN IF NOT EXISTS conversation_facts JSONB DEFAULT '[]'"))
        op.execute(sa.text("ALTER TABLE public.chatbot_sessions ADD COLUMN IF NOT EXISTS last_next_question_id TEXT"))
    else:
        op.add_column(
            "chatbot_sessions",
            sa.Column("conversation_summary", sa.Text(), nullable=True),
            schema="public",
        )
        op.add_column(
            "chatbot_sessions",
            sa.Column("conversation_facts", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=True),
            schema="public",
        )
        op.add_column(
            "chatbot_sessions",
            sa.Column("last_next_question_id", sa.Text(), nullable=True),
            schema="public",
        )


def downgrade() -> None:
    op.drop_column("chatbot_sessions", "last_next_question_id", schema="public")
    op.drop_column("chatbot_sessions", "conversation_facts", schema="public")
    op.drop_column("chatbot_sessions", "conversation_summary", schema="public")
