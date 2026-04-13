"""Passkeys / WebAuthn Phase 3.2: auth_passkeys + auth_webauthn_challenges.

Revision ID: 110
Revises: 109
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "110"
down_revision = "109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_webauthn_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("challenge_b64", sa.String(length=512), nullable=False),
        sa.Column("flow_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("identifier", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_webauthn_challenges_challenge_b64",
        "auth_webauthn_challenges",
        ["challenge_b64"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_auth_webauthn_challenges_expires_at",
        "auth_webauthn_challenges",
        ["expires_at"],
        schema="public",
    )

    op.create_table(
        "auth_passkeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credential_id_b64", sa.String(length=512), nullable=False),
        sa.Column("public_key_b64", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("transports_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("device_label", sa.String(length=255), nullable=True),
        sa.Column("aaguid", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_auth_passkeys_user_id",
        "auth_passkeys",
        ["user_id"],
        schema="public",
    )
    op.create_index(
        "uq_auth_passkeys_credential_id_b64",
        "auth_passkeys",
        ["credential_id_b64"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("uq_auth_passkeys_credential_id_b64", table_name="auth_passkeys", schema="public")
    op.drop_index("ix_auth_passkeys_user_id", table_name="auth_passkeys", schema="public")
    op.drop_table("auth_passkeys", schema="public")
    op.drop_index("ix_auth_webauthn_challenges_expires_at", table_name="auth_webauthn_challenges", schema="public")
    op.drop_index("ix_auth_webauthn_challenges_challenge_b64", table_name="auth_webauthn_challenges", schema="public")
    op.drop_table("auth_webauthn_challenges", schema="public")
