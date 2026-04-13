"""Add cost_basis_consumed and realized_pnl_generated to exchange_orders.

Revision ID: 067
Revises: 066
Create Date: 2026-03-19

PnL hardening: persist WAC cost basis consumed and realized PnL per SELL order
for auditability and invariant checks.
"""
from alembic import op
import sqlalchemy as sa

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exchange_orders",
        sa.Column("cost_basis_consumed", sa.Numeric(30, 10), nullable=True),
        schema="public",
    )
    op.add_column(
        "exchange_orders",
        sa.Column("realized_pnl_generated", sa.Numeric(30, 10), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("exchange_orders", "realized_pnl_generated", schema="public")
    op.drop_column("exchange_orders", "cost_basis_consumed", schema="public")
