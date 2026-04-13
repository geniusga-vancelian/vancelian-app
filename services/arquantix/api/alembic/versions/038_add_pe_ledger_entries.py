"""add pe_ledger_entries table

Revision ID: 038
Revises: 037
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_ledger_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_ledger_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entry_type", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("currency", sa.String(20), nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=False),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("counterpart_entry_id", UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_ledger_entries_account_effective", "pe_ledger_entries", ["account_id", "effective_at"], schema="public")
    op.create_index("ix_pe_ledger_entries_reference", "pe_ledger_entries", ["reference_type", "reference_id"], schema="public")
    op.create_index("ix_pe_ledger_entries_counterpart", "pe_ledger_entries", ["counterpart_entry_id"], schema="public")
    op.create_index("ix_pe_ledger_entries_created_at", "pe_ledger_entries", ["created_at"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_ledger_entries_created_at", table_name="pe_ledger_entries", schema="public")
    op.drop_index("ix_pe_ledger_entries_counterpart", table_name="pe_ledger_entries", schema="public")
    op.drop_index("ix_pe_ledger_entries_reference", table_name="pe_ledger_entries", schema="public")
    op.drop_index("ix_pe_ledger_entries_account_effective", table_name="pe_ledger_entries", schema="public")
    op.drop_table("pe_ledger_entries", schema="public")
