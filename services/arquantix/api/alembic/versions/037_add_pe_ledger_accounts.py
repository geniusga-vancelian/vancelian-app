"""add pe_ledger_accounts table

Revision ID: 037
Revises: 036
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_ledger_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("account_code", sa.String(100), unique=True, nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(20), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("wallet_container_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_wallet_containers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("balance", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_ledger_accounts_client_id", "pe_ledger_accounts", ["client_id"], schema="public")
    op.create_index("ix_pe_ledger_accounts_account_type", "pe_ledger_accounts", ["account_type"], schema="public")
    op.create_index("ix_pe_ledger_accounts_currency", "pe_ledger_accounts", ["currency"], schema="public")
    op.create_index("ix_pe_ledger_accounts_wallet_container_id", "pe_ledger_accounts", ["wallet_container_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_ledger_accounts_wallet_container_id", table_name="pe_ledger_accounts", schema="public")
    op.drop_index("ix_pe_ledger_accounts_currency", table_name="pe_ledger_accounts", schema="public")
    op.drop_index("ix_pe_ledger_accounts_account_type", table_name="pe_ledger_accounts", schema="public")
    op.drop_index("ix_pe_ledger_accounts_client_id", table_name="pe_ledger_accounts", schema="public")
    op.drop_table("pe_ledger_accounts", schema="public")
