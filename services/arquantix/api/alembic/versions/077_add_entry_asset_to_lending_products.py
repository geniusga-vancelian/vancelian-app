"""Add entry_asset_default and entry_assets_allowed to lending_pool_products — Phase 2A.12.

Enables Bundle-style invest flow with configurable entry assets.

Revision ID: 077
Revises: 076
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lending_pool_products",
        sa.Column("entry_asset_default", sa.String(20), nullable=True),
    )
    op.add_column(
        "lending_pool_products",
        sa.Column("entry_assets_allowed", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lending_pool_products", "entry_assets_allowed")
    op.drop_column("lending_pool_products", "entry_asset_default")
