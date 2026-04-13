"""add asset_id to pe_ledger_entries

Revision ID: 042
Revises: 041
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pe_ledger_entries",
        sa.Column("asset_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_pe_ledger_entries_asset_id",
        "pe_ledger_entries",
        "pe_assets",
        ["asset_id"],
        ["id"],
        ondelete="RESTRICT",
        source_schema="public",
        referent_schema="public",
    )
    op.create_index(
        "ix_pe_ledger_entries_asset_id",
        "pe_ledger_entries",
        ["asset_id"],
        schema="public",
    )

    op.execute("""
        UPDATE public.pe_ledger_entries e
        SET asset_id = a.asset_id
        FROM public.pe_ledger_accounts a
        WHERE e.account_id = a.id
          AND e.asset_id IS NULL
          AND a.asset_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_index("ix_pe_ledger_entries_asset_id", table_name="pe_ledger_entries", schema="public")
    op.drop_constraint("fk_pe_ledger_entries_asset_id", "pe_ledger_entries", schema="public", type_="foreignkey")
    op.drop_column("pe_ledger_entries", "asset_id", schema="public")
