"""PR F.7.2 — auth_user_temporal_features (temporal ML).

Revision ID: 142
Revises: 141
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "142"
down_revision = "141"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user_temporal_features",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hour_distribution", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("weekday_distribution", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "action_transition_matrix",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("ema_activity_drift", sa.Float(), nullable=True),
        sa.Column(
            "activity_rate_ema",
            sa.Float(),
            nullable=True,
            comment="EMA du débit moyen (évts/jour) pour détection de drift",
        ),
        sa.Column("sample_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        schema="public",
    )
    # idx_temporal_features_user_id : couvert par la clé primaire sur user_id


def downgrade() -> None:
    op.drop_table("auth_user_temporal_features", schema="public")
