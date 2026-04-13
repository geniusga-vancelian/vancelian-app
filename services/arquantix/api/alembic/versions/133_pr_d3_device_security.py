"""PR D3 — cycle de vie device, nonces signature sensibles.

Revision ID: 133
Revises: 132
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "133"
down_revision = "132"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_device_credentials",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_device_credentials",
        sa.Column("device_label", sa.String(length=128), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_device_credentials",
        sa.Column("public_key_sha256_hex", sa.String(length=64), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_device_credentials",
        sa.Column("attestation_bound_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )

    op.create_table(
        "auth_device_signature_nonces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("nonce_hash", name="uq_auth_device_signature_nonces_hash"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_signature_nonces_user_device",
        "auth_device_signature_nonces",
        ["user_id", "device_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_auth_device_signature_nonces_expires",
        "auth_device_signature_nonces",
        ["expires_at"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_auth_device_signature_nonces_expires", table_name="auth_device_signature_nonces", schema="public")
    op.drop_index("ix_auth_device_signature_nonces_user_device", table_name="auth_device_signature_nonces", schema="public")
    op.drop_table("auth_device_signature_nonces", schema="public")
    op.drop_column("auth_device_credentials", "attestation_bound_at", schema="public")
    op.drop_column("auth_device_credentials", "public_key_sha256_hex", schema="public")
    op.drop_column("auth_device_credentials", "device_label", schema="public")
    op.drop_column("auth_device_credentials", "revoked_at", schema="public")
