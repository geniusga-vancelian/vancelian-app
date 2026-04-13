"""Admin mobile E.164 + OTP SMS login challenges.

Revision ID: 117
Revises: 116
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "117"
down_revision = "116"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column("mobile_e164", sa.String(length=24), nullable=True),
    )
    op.create_index(
        "uq_admin_users_mobile_e164",
        "admin_users",
        ["mobile_e164"],
        unique=True,
        postgresql_where=sa.text("mobile_e164 IS NOT NULL"),
    )

    op.create_table(
        "auth_mobile_login_otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164_normalized", sa.String(length=24), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "uq_auth_mobile_login_otp_phone",
        "auth_mobile_login_otp_challenges",
        ["phone_e164_normalized"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_auth_mobile_login_otp_expires_at",
        "auth_mobile_login_otp_challenges",
        ["expires_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_mobile_login_otp_expires_at",
        table_name="auth_mobile_login_otp_challenges",
        schema="public",
    )
    op.drop_index(
        "uq_auth_mobile_login_otp_phone",
        table_name="auth_mobile_login_otp_challenges",
        schema="public",
    )
    op.drop_table("auth_mobile_login_otp_challenges", schema="public")
    op.drop_index("uq_admin_users_mobile_e164", table_name="admin_users")
    op.drop_column("admin_users", "mobile_e164")
