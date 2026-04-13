"""Device attestation Tier 1: trust session + nonces + replay artifacts.

Revision ID: 112
Revises: 111
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "112"
down_revision = "111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("attestation_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_sessions",
        sa.Column(
            "device_trust_level",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'UNKNOWN'"),
        ),
        schema="public",
    )
    op.add_column(
        "auth_sessions",
        sa.Column(
            "step_up_otp_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="public",
    )

    op.create_table(
        "auth_device_attest_nonces",
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("device_id_prefix", sa.String(length=16), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("nonce_hash"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_attest_nonces_expires_at",
        "auth_device_attest_nonces",
        ["expires_at"],
        schema="public",
    )

    op.create_table(
        "auth_device_attest_artifacts",
        sa.Column("digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("digest"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_attest_artifacts_expires_at",
        "auth_device_attest_artifacts",
        ["expires_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_device_attest_artifacts_expires_at",
        table_name="auth_device_attest_artifacts",
        schema="public",
    )
    op.drop_table("auth_device_attest_artifacts", schema="public")
    op.drop_index(
        "ix_auth_device_attest_nonces_expires_at",
        table_name="auth_device_attest_nonces",
        schema="public",
    )
    op.drop_table("auth_device_attest_nonces", schema="public")
    op.drop_column("auth_sessions", "step_up_otp_required", schema="public")
    op.drop_column("auth_sessions", "device_trust_level", schema="public")
    op.drop_column("auth_sessions", "attestation_metadata", schema="public")
