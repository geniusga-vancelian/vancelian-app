"""PR D2 — clés publiques device (ECDSA P-256) pour signatures requêtes refresh.

Revision ID: 132
Revises: 131
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "132"
down_revision = "131"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_device_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("public_key_spki_b64", sa.Text(), nullable=False),
        sa.Column(
            "key_alg",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'EC_P256'"),
        ),
        sa.Column("attestation_level", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_auth_device_credentials_user_device"),
        schema="public",
    )
    op.create_index(
        "ix_auth_device_credentials_user_id",
        "auth_device_credentials",
        ["user_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_auth_device_credentials_user_id", table_name="auth_device_credentials", schema="public")
    op.drop_table("auth_device_credentials", schema="public")
