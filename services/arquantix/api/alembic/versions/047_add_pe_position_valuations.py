"""add pe_position_valuations table

Revision ID: 047
Revises: 046
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_position_valuations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("position_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_position_atoms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(30, 10), nullable=False),
        sa.Column("price", sa.Numeric(30, 10), nullable=True),
        sa.Column("market_value", sa.Numeric(30, 10), nullable=True),
        sa.Column("average_entry_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(30, 10), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("pricing_status", sa.String(20), nullable=False),
        sa.Column("valuation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_position_valuations_position_id", "pe_position_valuations", ["position_id"], schema="public")
    op.create_index("ix_pe_position_valuations_portfolio_id", "pe_position_valuations", ["portfolio_id"], schema="public")
    op.create_index("ix_pe_position_valuations_valuation_ts", "pe_position_valuations", ["valuation_timestamp"], schema="public")
    op.create_index("ix_pe_position_valuations_portfolio_ts", "pe_position_valuations", ["portfolio_id", "valuation_timestamp"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_position_valuations_portfolio_ts", table_name="pe_position_valuations", schema="public")
    op.drop_index("ix_pe_position_valuations_valuation_ts", table_name="pe_position_valuations", schema="public")
    op.drop_index("ix_pe_position_valuations_portfolio_id", table_name="pe_position_valuations", schema="public")
    op.drop_index("ix_pe_position_valuations_position_id", table_name="pe_position_valuations", schema="public")
    op.drop_table("pe_position_valuations", schema="public")
