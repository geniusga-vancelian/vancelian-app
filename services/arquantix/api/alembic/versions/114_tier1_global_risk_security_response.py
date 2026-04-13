"""Tier-1 security: global risk score table + account enforcement columns.

Revision ID: 114
Revises: 113
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "114"
down_revision = "113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_global_risk_score",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("level", sa.String(length=32), nullable=False, server_default=sa.text("'LOW'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        schema="public",
    )
    op.add_column(
        "admin_users",
        sa.Column("security_account_locked_until", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "admin_users",
        sa.Column(
            "security_flagged",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="public",
    )
    op.add_column(
        "admin_users",
        sa.Column(
            "security_refresh_blocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("admin_users", "security_refresh_blocked", schema="public")
    op.drop_column("admin_users", "security_flagged", schema="public")
    op.drop_column("admin_users", "security_account_locked_until", schema="public")
    op.drop_table("auth_global_risk_score", schema="public")
