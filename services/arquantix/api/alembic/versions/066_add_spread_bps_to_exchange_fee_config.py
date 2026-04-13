"""Add spread_bps column to exchange_fee_config.

Revision ID: 066
Revises: 065
Create Date: 2026-03-19

Supports simulated market execution: BUY at ask, SELL at bid,
with configurable spread per asset when real bid/ask are unavailable.
"""
from alembic import op
import sqlalchemy as sa

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exchange_fee_config",
        sa.Column("spread_bps", sa.Integer(), nullable=False, server_default="50"),
    )


def downgrade() -> None:
    op.drop_column("exchange_fee_config", "spread_bps")
