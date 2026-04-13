"""Device reputation + usage graph + blacklist + findings persistés.

Revision ID: 115
Revises: 114
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "115"
down_revision = "114"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_device_reputation",
        sa.Column("device_hash", sa.String(length=64), nullable=False),
        sa.Column("global_risk_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reputation_level", sa.String(length=16), nullable=False, server_default=sa.text("'LOW'")),
        sa.Column("total_sessions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unique_user_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unique_ip_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("suspicious_event_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("device_hash"),
        schema="public",
    )

    op.create_table(
        "auth_device_usage_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["auth_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_usage_edges_device_hash",
        "auth_device_usage_edges",
        ["device_hash"],
        schema="public",
    )
    op.create_index(
        "ix_auth_device_usage_edges_user_id",
        "auth_device_usage_edges",
        ["user_id"],
        schema="public",
    )
    op.create_index(
        "ix_auth_device_usage_edges_created_at",
        "auth_device_usage_edges",
        ["created_at"],
        schema="public",
    )

    op.create_table(
        "auth_device_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_blacklist_device_hash",
        "auth_device_blacklist",
        ["device_hash"],
        schema="public",
    )

    op.create_table(
        "auth_device_graph_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_hash", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("finding_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_graph_findings_device_hash",
        "auth_device_graph_findings",
        ["device_hash"],
        schema="public",
    )
    op.create_index(
        "ix_auth_device_graph_findings_created_at",
        "auth_device_graph_findings",
        ["created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("auth_device_graph_findings", schema="public")
    op.drop_table("auth_device_blacklist", schema="public")
    op.drop_index("ix_auth_device_usage_edges_created_at", table_name="auth_device_usage_edges", schema="public")
    op.drop_index("ix_auth_device_usage_edges_user_id", table_name="auth_device_usage_edges", schema="public")
    op.drop_index("ix_auth_device_usage_edges_device_hash", table_name="auth_device_usage_edges", schema="public")
    op.drop_table("auth_device_usage_edges", schema="public")
    op.drop_table("auth_device_reputation", schema="public")
