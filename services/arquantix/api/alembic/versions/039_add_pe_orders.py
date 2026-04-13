"""add pe_orders table

Revision ID: 039
Revises: 038
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("portfolio_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_portfolios.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instrument_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_instruments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_type", sa.String(50), nullable=False),
        sa.Column("side", sa.String(10), nullable=True),
        sa.Column("quantity", sa.Numeric(30, 10), nullable=True),
        sa.Column("amount", sa.Numeric(30, 10), nullable=True),
        sa.Column("currency", sa.String(20), nullable=True),
        sa.Column("price_limit", sa.Numeric(30, 10), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_orders_client_id", "pe_orders", ["client_id"], schema="public")
    op.create_index("ix_pe_orders_portfolio_id", "pe_orders", ["portfolio_id"], schema="public")
    op.create_index("ix_pe_orders_instrument_id", "pe_orders", ["instrument_id"], schema="public")
    op.create_index("ix_pe_orders_order_type", "pe_orders", ["order_type"], schema="public")
    op.create_index("ix_pe_orders_status", "pe_orders", ["status"], schema="public")
    op.create_index("ix_pe_orders_created_at", "pe_orders", ["created_at"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_orders_created_at", table_name="pe_orders", schema="public")
    op.drop_index("ix_pe_orders_status", table_name="pe_orders", schema="public")
    op.drop_index("ix_pe_orders_order_type", table_name="pe_orders", schema="public")
    op.drop_index("ix_pe_orders_instrument_id", table_name="pe_orders", schema="public")
    op.drop_index("ix_pe_orders_portfolio_id", table_name="pe_orders", schema="public")
    op.drop_index("ix_pe_orders_client_id", table_name="pe_orders", schema="public")
    op.drop_table("pe_orders", schema="public")
