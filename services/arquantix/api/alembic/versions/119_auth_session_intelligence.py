"""Session intelligence + continuous auth state per auth session.

Revision ID: 119
Revises: 118
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "119"
down_revision = "118"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_session_intelligence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("auth_strength", sa.String(length=64), server_default=sa.text("'password'"), nullable=False),
        sa.Column("session_trust_level", sa.String(length=32), server_default=sa.text("'UNKNOWN'"), nullable=False),
        sa.Column("device_trust_level", sa.String(length=32), server_default=sa.text("'UNKNOWN'"), nullable=False),
        sa.Column("last_risk_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_fraud_score", sa.Float(), nullable=True),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_sensitive_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_ip", sa.String(length=45), nullable=True),
        sa.Column("last_country", sa.String(length=8), nullable=True),
        sa.Column("relock_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("step_up_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_step_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reason_codes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["session_id"], ["public.auth_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_auth_session_intelligence_session_id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_session_intelligence_user_id",
        "auth_session_intelligence",
        ["user_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_auth_session_intelligence_user_id", table_name="auth_session_intelligence", schema="public")
    op.drop_index("ix_auth_session_intelligence_session_id", table_name="auth_session_intelligence", schema="public")
    op.drop_table("auth_session_intelligence", schema="public")
