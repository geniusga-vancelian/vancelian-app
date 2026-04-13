"""add logo_filename to market_data_instruments

Revision ID: 021_logo_filename
Revises: 020_add_market_data_bars_1w
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = "021_logo_filename"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_data_instruments",
        sa.Column("logo_filename", sa.String(length=100), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("market_data_instruments", "logo_filename", schema="public")
