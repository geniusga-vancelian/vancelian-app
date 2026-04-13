"""add custody tables

Revision ID: 058
Revises: 057
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- custody_providers ---
    op.create_table(
        "custody_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("provider_type", sa.String(20), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=True),
        sa.Column("api_base_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata_", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )

    # --- custody_accounts ---
    op.create_table(
        "custody_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_providers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("iban", sa.String(50), nullable=True),
        sa.Column("bic", sa.String(20), nullable=True),
        sa.Column("account_holder_name", sa.String(255), nullable=False),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ledger_account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_ledger_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_master_account", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata_", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_custody_accounts_client_id", "custody_accounts", ["client_id"], schema="public")
    op.create_index("ix_custody_accounts_provider_id", "custody_accounts", ["provider_id"], schema="public")
    op.create_index("ix_custody_accounts_account_type", "custody_accounts", ["account_type"], schema="public")
    op.create_index("ix_custody_accounts_ledger_account_id", "custody_accounts", ["ledger_account_id"], schema="public")

    # --- custody_account_balances ---
    op.create_table(
        "custody_account_balances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_accounts.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("available_balance", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("pending_balance", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )

    # --- custody_transactions ---
    op.create_table(
        "custody_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("transaction_type", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("metadata_", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_custody_transactions_account_id", "custody_transactions", ["account_id"], schema="public")
    op.create_index("ix_custody_transactions_type", "custody_transactions", ["transaction_type"], schema="public")
    op.create_index("ix_custody_transactions_created_at", "custody_transactions", ["created_at"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_custody_transactions_created_at", table_name="custody_transactions", schema="public")
    op.drop_index("ix_custody_transactions_type", table_name="custody_transactions", schema="public")
    op.drop_index("ix_custody_transactions_account_id", table_name="custody_transactions", schema="public")
    op.drop_table("custody_transactions", schema="public")
    op.drop_table("custody_account_balances", schema="public")
    op.drop_index("ix_custody_accounts_ledger_account_id", table_name="custody_accounts", schema="public")
    op.drop_index("ix_custody_accounts_account_type", table_name="custody_accounts", schema="public")
    op.drop_index("ix_custody_accounts_provider_id", table_name="custody_accounts", schema="public")
    op.drop_index("ix_custody_accounts_client_id", table_name="custody_accounts", schema="public")
    op.drop_table("custody_accounts", schema="public")
    op.drop_table("custody_providers", schema="public")
