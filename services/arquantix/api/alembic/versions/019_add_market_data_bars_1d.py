"""add_market_data_bars_1d

Revision ID: 019
Revises: 018
Create Date: 2026-02-18

1-day candle table for Binance crypto instruments.
"""
from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_bars_1d",
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("volume", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="binance", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["market_data_instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("instrument_id", "open_time"),
        schema="public",
    )
    op.create_index(
        op.f("ix_market_data_bars_1d_instrument_id"),
        "market_data_bars_1d",
        ["instrument_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        op.f("ix_market_data_bars_1d_open_time"),
        "market_data_bars_1d",
        ["open_time"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_market_data_bars_1d_open_time"),
        table_name="market_data_bars_1d",
        schema="public",
    )
    op.drop_index(
        op.f("ix_market_data_bars_1d_instrument_id"),
        table_name="market_data_bars_1d",
        schema="public",
    )
    op.drop_table("market_data_bars_1d", schema="public")
