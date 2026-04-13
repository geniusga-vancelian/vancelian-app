"""Zero Trust: décisions persistées + rôles staff + auth_strength session.

Revision ID: 116
Revises: 115
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "116"
down_revision = "115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column(
            "zero_trust_role",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'admin'"),
        ),
        schema="public",
    )
    op.add_column(
        "auth_sessions",
        sa.Column(
            "auth_strength",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'password'"),
        ),
        schema="public",
    )
    op.create_table(
        "auth_security_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=256), nullable=False),
        sa.Column("resource", sa.String(length=512), nullable=False),
        sa.Column("allow", sa.Boolean(), nullable=False),
        sa.Column("require_step_up", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deny_reason", sa.Text(), nullable=True),
        sa.Column("policy_id", sa.String(length=128), nullable=False),
        sa.Column(
            "context_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["public.auth_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_security_decisions_user_id",
        "auth_security_decisions",
        ["user_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_auth_security_decisions_created_at",
        "auth_security_decisions",
        ["created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_auth_security_decisions_action",
        "auth_security_decisions",
        ["action"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_auth_security_decisions_action", table_name="auth_security_decisions", schema="public")
    op.drop_index("ix_auth_security_decisions_created_at", table_name="auth_security_decisions", schema="public")
    op.drop_index("ix_auth_security_decisions_user_id", table_name="auth_security_decisions", schema="public")
    op.drop_table("auth_security_decisions", schema="public")
    op.drop_column("auth_sessions", "auth_strength", schema="public")
    op.drop_column("admin_users", "zero_trust_role", schema="public")
