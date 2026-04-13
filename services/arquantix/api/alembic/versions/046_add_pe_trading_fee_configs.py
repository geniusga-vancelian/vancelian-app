"""add pe_trading_fee_configs table

Revision ID: 046
Revises: 045
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "046"
down_revision = "045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_trading_fee_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=True),
        sa.Column("fee_type", sa.String(30), nullable=False, server_default="trading"),
        sa.Column("fee_rate", sa.Numeric(12, 8), nullable=False),
        sa.Column("min_fee", sa.Numeric(30, 10), nullable=True),
        sa.Column("max_fee", sa.Numeric(30, 10), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_trading_fee_configs_scope", "pe_trading_fee_configs", ["scope_type", "scope_id"], schema="public")
    op.create_index("ix_pe_trading_fee_configs_status", "pe_trading_fee_configs", ["status"], schema="public")
    op.create_index("ix_pe_trading_fee_configs_fee_type", "pe_trading_fee_configs", ["fee_type"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_trading_fee_configs_fee_type", table_name="pe_trading_fee_configs", schema="public")
    op.drop_index("ix_pe_trading_fee_configs_status", table_name="pe_trading_fee_configs", schema="public")
    op.drop_index("ix_pe_trading_fee_configs_scope", table_name="pe_trading_fee_configs", schema="public")
    op.drop_table("pe_trading_fee_configs", schema="public")
