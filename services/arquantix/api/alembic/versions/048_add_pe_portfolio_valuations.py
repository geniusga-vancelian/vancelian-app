"""add pe_portfolio_valuations table

Revision ID: 048
Revises: 047
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_portfolio_valuations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("portfolio_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nav", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_realized_pnl", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_unrealized_pnl", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_pnl", sa.Numeric(30, 10), nullable=False),
        sa.Column("priced_positions_count", sa.Integer, nullable=False),
        sa.Column("unpriced_positions_count", sa.Integer, nullable=False),
        sa.Column("valuation_source", sa.String(30), nullable=False),
        sa.Column("valuation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_portfolio_valuations_portfolio_id", "pe_portfolio_valuations", ["portfolio_id"], schema="public")
    op.create_index("ix_pe_portfolio_valuations_valuation_ts", "pe_portfolio_valuations", ["valuation_timestamp"], schema="public")
    op.create_index("ix_pe_portfolio_valuations_portfolio_ts", "pe_portfolio_valuations", ["portfolio_id", "valuation_timestamp"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_portfolio_valuations_portfolio_ts", table_name="pe_portfolio_valuations", schema="public")
    op.drop_index("ix_pe_portfolio_valuations_valuation_ts", table_name="pe_portfolio_valuations", schema="public")
    op.drop_index("ix_pe_portfolio_valuations_portfolio_id", table_name="pe_portfolio_valuations", schema="public")
    op.drop_table("pe_portfolio_valuations", schema="public")
