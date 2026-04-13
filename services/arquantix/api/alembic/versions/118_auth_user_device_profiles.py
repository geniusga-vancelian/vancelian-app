"""Per-user device trust profiles for login scoring (no parallel risk engine).

Revision ID: 118
Revises: 117
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "118"
down_revision = "117"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user_device_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_hash", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("fingerprint_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("login_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "successful_login_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "failed_login_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_ip", sa.String(length=45), nullable=True),
        sa.Column("last_country", sa.String(length=8), nullable=True),
        sa.Column("trust_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "trust_level",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'LOW'"),
        ),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("last_auth_strength", sa.String(length=64), nullable=True),
        sa.Column("last_attestation_level", sa.String(length=64), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_hash", name="uq_auth_user_device_profiles_user_device"),
        schema="public",
    )
    op.create_index(
        "ix_auth_user_device_profiles_user_id",
        "auth_user_device_profiles",
        ["user_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_auth_user_device_profiles_device_hash",
        "auth_user_device_profiles",
        ["device_hash"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_user_device_profiles_device_hash",
        table_name="auth_user_device_profiles",
        schema="public",
    )
    op.drop_index(
        "ix_auth_user_device_profiles_user_id",
        table_name="auth_user_device_profiles",
        schema="public",
    )
    op.drop_table("auth_user_device_profiles", schema="public")
