"""add pe_trades table

Revision ID: 040
Revises: 039
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_trades",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instrument_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_instruments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(30, 10), nullable=False),
        sa.Column("price", sa.Numeric(30, 10), nullable=False),
        sa.Column("gross_amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("fee_amount", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("currency", sa.String(20), nullable=False),
        sa.Column("counterparty", sa.String(100), nullable=True),
        sa.Column("external_trade_id", sa.String(255), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_trades_order_id", "pe_trades", ["order_id"], schema="public")
    op.create_index("ix_pe_trades_instrument_id", "pe_trades", ["instrument_id"], schema="public")
    op.create_index("ix_pe_trades_executed_at", "pe_trades", ["executed_at"], schema="public")
    op.create_index("ix_pe_trades_external_trade_id", "pe_trades", ["external_trade_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_trades_external_trade_id", table_name="pe_trades", schema="public")
    op.drop_index("ix_pe_trades_executed_at", table_name="pe_trades", schema="public")
    op.drop_index("ix_pe_trades_instrument_id", table_name="pe_trades", schema="public")
    op.drop_index("ix_pe_trades_order_id", table_name="pe_trades", schema="public")
    op.drop_table("pe_trades", schema="public")
