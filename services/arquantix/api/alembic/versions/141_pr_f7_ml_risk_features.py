"""PR F.7 — auth_user_risk_features (ML / anomalies vectorielles).

Revision ID: 141
Revises: 140
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "141"
down_revision = "140"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_user_risk_features",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["public.admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("auth_user_risk_features", schema="public")
