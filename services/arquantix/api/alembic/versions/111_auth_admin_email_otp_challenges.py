"""OTP e-mail connexion admin (fallback passkeys Phase 3.4).

Revision ID: 111
Revises: 110
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "111"
down_revision = "110"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "auth_admin_email_otp_challenges" not in insp.get_table_names(schema="public"):
        op.create_table(
            "auth_admin_email_otp_challenges",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email_normalized", sa.String(length=255), nullable=False),
            sa.Column("code_hash", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            schema="public",
        )
    insp = sa.inspect(bind)
    idx_names = {i["name"] for i in insp.get_indexes("auth_admin_email_otp_challenges", schema="public")}
    if "uq_auth_admin_email_otp_email" not in idx_names:
        op.create_index(
            "uq_auth_admin_email_otp_email",
            "auth_admin_email_otp_challenges",
            ["email_normalized"],
            unique=True,
            schema="public",
        )
    if "ix_auth_admin_email_otp_expires_at" not in idx_names:
        op.create_index(
            "ix_auth_admin_email_otp_expires_at",
            "auth_admin_email_otp_challenges",
            ["expires_at"],
            schema="public",
        )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_admin_email_otp_expires_at",
        table_name="auth_admin_email_otp_challenges",
        schema="public",
    )
    op.drop_index(
        "uq_auth_admin_email_otp_email",
        table_name="auth_admin_email_otp_challenges",
        schema="public",
    )
    op.drop_table("auth_admin_email_otp_challenges", schema="public")
