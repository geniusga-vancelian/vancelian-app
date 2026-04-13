"""add pe_wallet_containers table (Portfolio Engine — ledger layer)

Revision ID: 025
Revises: 024
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_wallet_containers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # TODO: add FK to pe_clients.id when the clients module is implemented.
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("wallet_type", sa.String(length=50), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custody_provider", sa.String(length=100), nullable=True),
        sa.Column("blockchain_address", sa.String(length=255), nullable=True),
        sa.Column("ledger_account_ref", sa.String(length=255), nullable=True),
        sa.Column("jurisdiction", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'active'"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["instrument_id"], ["public.pe_instruments.id"], ondelete="SET NULL"),
        schema="public",
    )

    op.create_index("ix_pe_wallet_containers_client_id", "pe_wallet_containers", ["client_id"], unique=False, schema="public")
    op.create_index("ix_pe_wallet_containers_portfolio_id", "pe_wallet_containers", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_wallet_containers_wallet_type", "pe_wallet_containers", ["wallet_type"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_wallet_containers_wallet_type", table_name="pe_wallet_containers", schema="public")
    op.drop_index("ix_pe_wallet_containers_portfolio_id", table_name="pe_wallet_containers", schema="public")
    op.drop_index("ix_pe_wallet_containers_client_id", table_name="pe_wallet_containers", schema="public")
    op.drop_table("pe_wallet_containers", schema="public")
