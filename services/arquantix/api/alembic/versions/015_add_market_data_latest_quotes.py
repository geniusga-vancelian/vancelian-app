"""add_market_data_latest_quotes

Revision ID: 015
Revises: 014
Create Date: 2026-02-18

Snapshot table for latest market quotes (one row per instrument).
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_data_latest_quotes",
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_symbol", sa.String(length=50), nullable=True),
        sa.Column("last_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("bid_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("ask_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("volume", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("quote_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["instrument_id"], ["market_data_instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("instrument_id"),
        schema="public",
    )
    op.create_index(
        op.f("ix_market_data_latest_quotes_instrument_id"),
        "market_data_latest_quotes",
        ["instrument_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_market_data_latest_quotes_instrument_id"),
        table_name="market_data_latest_quotes",
        schema="public",
    )
    op.drop_table("market_data_latest_quotes", schema="public")
