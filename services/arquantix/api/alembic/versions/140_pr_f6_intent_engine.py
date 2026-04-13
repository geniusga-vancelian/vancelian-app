"""PR F.6 — auth_user_intent_events (Intent Engine).

Revision ID: 140
Revises: 139
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "140"
down_revision = "139"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user_intent_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_user_intent_events_user_created",
        "auth_user_intent_events",
        ["user_id", "created_at"],
        unique=False,
        schema="public",
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    op.drop_index("ix_auth_user_intent_events_user_created", table_name="auth_user_intent_events", schema="public")
    op.drop_table("auth_user_intent_events", schema="public")
