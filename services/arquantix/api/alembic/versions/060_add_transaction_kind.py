"""add transaction_kind to custody_transactions

Revision ID: 060
Revises: 059
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custody_transactions",
        sa.Column("transaction_kind", sa.String(30), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_custody_transactions_kind",
        "custody_transactions",
        ["transaction_kind"],
        schema="public",
    )
    op.execute("""
        UPDATE public.custody_transactions
        SET transaction_kind = CASE
            WHEN transaction_type = 'deposit' AND direction = 'credit' THEN 'bank_transfer_in'
            WHEN transaction_type = 'withdrawal' AND direction = 'debit' THEN 'bank_transfer_out'
            WHEN transaction_type = 'transfer_internal' THEN 'internal_transfer'
            ELSE NULL
        END
    """)


def downgrade() -> None:
    op.drop_index("ix_custody_transactions_kind", table_name="custody_transactions", schema="public")
    op.drop_column("custody_transactions", "transaction_kind", schema="public")
