"""PR F.2 — baseline risque par utilisateur.

Revision ID: 136
Revises: 135
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "136"
down_revision = "135"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user_risk_baselines",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("primary_country", sa.String(length=8), nullable=True),
        sa.Column(
            "countries_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "frequent_ips_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("device_count_ema", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("actions_per_hour_ema", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("baseline_sample_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("auth_user_risk_baselines", schema="public")
