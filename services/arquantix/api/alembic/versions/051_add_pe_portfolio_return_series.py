"""add pe_portfolio_return_series table

Revision ID: 051
Revises: 050
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_portfolio_return_series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "valuation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_portfolio_valuations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nav", sa.Numeric(30, 10), nullable=False),
        sa.Column("period_return", sa.Numeric(20, 10), nullable=True),
        sa.Column("cumulative_return", sa.Numeric(20, 10), nullable=True),
        sa.Column("drawdown", sa.Numeric(20, 10), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pe_portfolio_return_series_portfolio_id",
        "pe_portfolio_return_series",
        ["portfolio_id"],
    )
    op.create_index(
        "ix_pe_portfolio_return_series_timestamp",
        "pe_portfolio_return_series",
        ["timestamp"],
    )
    op.create_index(
        "ix_pe_portfolio_return_series_pf_ts",
        "pe_portfolio_return_series",
        ["portfolio_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_pe_portfolio_return_series_pf_ts", table_name="pe_portfolio_return_series")
    op.drop_index("ix_pe_portfolio_return_series_timestamp", table_name="pe_portfolio_return_series")
    op.drop_index("ix_pe_portfolio_return_series_portfolio_id", table_name="pe_portfolio_return_series")
    op.drop_table("pe_portfolio_return_series")
