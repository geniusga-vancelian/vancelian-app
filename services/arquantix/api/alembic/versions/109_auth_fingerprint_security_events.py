"""Auth Phase 3.1: fingerprint + attestation columns, auth_security_events.

Revision ID: 109
Revises: 108
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "109"
down_revision = "108"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_sessions",
        sa.Column("fingerprint_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_sessions",
        sa.Column("attestation_type", sa.String(length=64), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_sessions",
        sa.Column("attestation_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )

    op.create_table(
        "auth_security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_auth_security_events_user_id", "auth_security_events", ["user_id"], schema="public")
    op.create_index("ix_auth_security_events_device_id", "auth_security_events", ["device_id"], schema="public")
    op.create_index("ix_auth_security_events_ip_address", "auth_security_events", ["ip_address"], schema="public")
    op.create_index("ix_auth_security_events_created_at", "auth_security_events", ["created_at"], schema="public")
    op.create_index("ix_auth_security_events_event_type", "auth_security_events", ["event_type"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_auth_security_events_event_type", table_name="auth_security_events", schema="public")
    op.drop_index("ix_auth_security_events_created_at", table_name="auth_security_events", schema="public")
    op.drop_index("ix_auth_security_events_ip_address", table_name="auth_security_events", schema="public")
    op.drop_index("ix_auth_security_events_device_id", table_name="auth_security_events", schema="public")
    op.drop_index("ix_auth_security_events_user_id", table_name="auth_security_events", schema="public")
    op.drop_table("auth_security_events", schema="public")
    op.drop_column("auth_sessions", "attestation_verified_at", schema="public")
    op.drop_column("auth_sessions", "attestation_type", schema="public")
    op.drop_column("auth_sessions", "fingerprint_metadata", schema="public")
    op.drop_column("auth_sessions", "fingerprint_hash", schema="public")
