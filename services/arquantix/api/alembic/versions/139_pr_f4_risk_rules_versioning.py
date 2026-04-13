"""PR F.4.1 — versioning / ruleset / is_active sur auth_risk_rules.

Revision ID: 139
Revises: 138
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "139"
down_revision = "138"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_risk_rules",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        schema="public",
    )
    op.add_column(
        "auth_risk_rules",
        sa.Column(
            "ruleset",
            sa.String(length=64),
            server_default=sa.text("'default'"),
            nullable=False,
        ),
        schema="public",
    )
    op.add_column(
        "auth_risk_rules",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        schema="public",
    )
    op.execute("UPDATE public.auth_risk_rules SET is_active = enabled")
    op.create_index(
        "ix_auth_risk_rules_ruleset_active_priority",
        "auth_risk_rules",
        ["ruleset", "is_active", "priority"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_auth_risk_rules_ruleset_active_priority",
        table_name="auth_risk_rules",
        schema="public",
    )
    op.drop_column("auth_risk_rules", "is_active", schema="public")
    op.drop_column("auth_risk_rules", "ruleset", schema="public")
    op.drop_column("auth_risk_rules", "version", schema="public")
