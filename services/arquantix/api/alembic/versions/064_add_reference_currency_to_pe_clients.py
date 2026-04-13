"""Add reference_currency column to pe_clients.

Revision ID: 064
Revises: 063
"""
from alembic import op
import sqlalchemy as sa

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pe_clients",
        sa.Column("reference_currency", sa.String(3), nullable=False, server_default="EUR"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("pe_clients", "reference_currency", schema="public")
