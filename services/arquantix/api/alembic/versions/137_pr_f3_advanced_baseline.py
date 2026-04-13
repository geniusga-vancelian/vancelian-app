"""PR F.3 — baseline temporelle et actions (Welford + last actions).

Revision ID: 137
Revises: 136
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "137"
down_revision = "136"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column("avg_hour_of_day", sa.Float(), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column("std_hour_of_day", sa.Float(), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column("avg_weekday", sa.Float(), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column("std_weekday", sa.Float(), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column("avg_session_duration_sec", sa.Float(), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column("std_session_duration_sec", sa.Float(), nullable=True),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column(
            "last_10_actions_types",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema="public",
    )
    op.add_column(
        "auth_user_risk_baselines",
        sa.Column(
            "temporal_welford_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="public",
    )


def downgrade() -> None:
    for col in (
        "temporal_welford_json",
        "last_10_actions_types",
        "std_session_duration_sec",
        "avg_session_duration_sec",
        "std_weekday",
        "avg_weekday",
        "std_hour_of_day",
        "avg_hour_of_day",
    ):
        op.drop_column("auth_user_risk_baselines", col, schema="public")
