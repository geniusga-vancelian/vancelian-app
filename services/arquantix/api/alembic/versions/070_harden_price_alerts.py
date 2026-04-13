"""Harden price_alerts: add cooldown, execution_status, metadata.

Revision ID: 070
Revises: 069
Create Date: 2026-03-20

Adds:
- cooldown_seconds (default 0 = no cooldown)
- last_triggered_at (for cooldown window enforcement)
- execution_status (pending/executed/failed for order triggers)
- metadata_ (JSONB, observability context)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "price_alerts",
        sa.Column("cooldown_seconds", sa.Integer, nullable=False, server_default="0"),
        schema="public",
    )
    op.add_column(
        "price_alerts",
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "price_alerts",
        sa.Column(
            "execution_status",
            sa.String(20),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "price_alerts",
        sa.Column("metadata_", JSONB, nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("price_alerts", "metadata_", schema="public")
    op.drop_column("price_alerts", "execution_status", schema="public")
    op.drop_column("price_alerts", "last_triggered_at", schema="public")
    op.drop_column("price_alerts", "cooldown_seconds", schema="public")
