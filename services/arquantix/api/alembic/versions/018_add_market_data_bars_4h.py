"""add_market_data_bars_4h

Revision ID: 018
Revises: 017
Create Date: 2026-02-18

4-hour candle table for Binance crypto instruments.
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_bars_4h",
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
        op.f("ix_market_data_bars_4h_instrument_id"),
        "market_data_bars_4h",
        ["instrument_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        op.f("ix_market_data_bars_4h_open_time"),
        "market_data_bars_4h",
        ["open_time"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_market_data_bars_4h_open_time"),
        table_name="market_data_bars_4h",
        schema="public",
    )
    op.drop_index(
        op.f("ix_market_data_bars_4h_instrument_id"),
        table_name="market_data_bars_4h",
        schema="public",
    )
    op.drop_table("market_data_bars_4h", schema="public")
