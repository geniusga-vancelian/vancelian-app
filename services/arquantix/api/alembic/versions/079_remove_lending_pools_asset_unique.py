"""Remove unique constraint on lending_pools.asset.

Multiple exclusive offer pools can share the same asset (e.g. two USDC offers).

Revision ID: 079
Revises: 078
"""
from alembic import op

revision = "079"
down_revision = "078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("lending_pools_asset_key", "lending_pools", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("lending_pools_asset_key", "lending_pools", ["asset"])
