"""add partial unique index for open positions

Revision ID: 045
Revises: 044
Create Date: 2026-03-15
"""
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX ix_pe_position_atoms_unique_open
        ON public.pe_position_atoms (portfolio_id, instrument_id)
        WHERE status = 'open'
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_pe_position_atoms_unique_open")
