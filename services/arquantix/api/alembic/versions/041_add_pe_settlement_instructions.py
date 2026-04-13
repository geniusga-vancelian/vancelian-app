"""add pe_settlement_instructions table

Revision ID: 041
Revises: 040
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_settlement_instructions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trade_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_trades.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("settlement_group_id", UUID(as_uuid=True), nullable=True),
        sa.Column("settlement_type", sa.String(50), nullable=False),
        sa.Column("from_account_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_ledger_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("to_account_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_ledger_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_sett_order_id", "pe_settlement_instructions", ["order_id"], schema="public")
    op.create_index("ix_pe_sett_trade_id", "pe_settlement_instructions", ["trade_id"], schema="public")
    op.create_index("ix_pe_sett_group_id", "pe_settlement_instructions", ["settlement_group_id"], schema="public")
    op.create_index("ix_pe_sett_from_account", "pe_settlement_instructions", ["from_account_id"], schema="public")
    op.create_index("ix_pe_sett_to_account", "pe_settlement_instructions", ["to_account_id"], schema="public")
    op.create_index("ix_pe_sett_asset_id", "pe_settlement_instructions", ["asset_id"], schema="public")
    op.create_index("ix_pe_sett_status", "pe_settlement_instructions", ["status"], schema="public")
    op.create_index("ix_pe_sett_scheduled_at", "pe_settlement_instructions", ["scheduled_at"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_sett_scheduled_at", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_status", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_asset_id", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_to_account", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_from_account", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_group_id", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_trade_id", table_name="pe_settlement_instructions", schema="public")
    op.drop_index("ix_pe_sett_order_id", table_name="pe_settlement_instructions", schema="public")
    op.drop_table("pe_settlement_instructions", schema="public")
