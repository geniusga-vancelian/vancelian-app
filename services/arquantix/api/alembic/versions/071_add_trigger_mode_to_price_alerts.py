"""Add trigger_mode and trigger_count to price_alerts.

Revision ID: 071
Revises: 070
Create Date: 2026-03-20

Supports recurring alerts that stay active after trigger.
"""
from alembic import op
import sqlalchemy as sa

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "price_alerts",
        sa.Column("trigger_mode", sa.String(20), nullable=False, server_default="once"),
        schema="public",
    )
    op.add_column(
        "price_alerts",
        sa.Column("trigger_count", sa.Integer, nullable=False, server_default="0"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("price_alerts", "trigger_count", schema="public")
    op.drop_column("price_alerts", "trigger_mode", schema="public")
