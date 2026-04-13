"""Phase 2 auth: server-side sessions, refresh jti rotation, spent jti denylist.

Revision ID: 108
Revises: 107
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "108"
down_revision = "107"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("refresh_jti", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False, schema="public")
    op.create_index("ix_auth_sessions_user_device", "auth_sessions", ["user_id", "device_id"], unique=False, schema="public")
    op.create_index("ix_auth_sessions_refresh_jti", "auth_sessions", ["refresh_jti"], unique=True, schema="public")

    op.create_table(
        "auth_spent_refresh_jti",
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("spent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("jti"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("auth_spent_refresh_jti", schema="public")
    op.drop_index("ix_auth_sessions_refresh_jti", table_name="auth_sessions", schema="public")
    op.drop_index("ix_auth_sessions_user_device", table_name="auth_sessions", schema="public")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions", schema="public")
    op.drop_table("auth_sessions", schema="public")
