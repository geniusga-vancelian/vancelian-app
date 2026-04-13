"""Add project_id to lending_pool_products — Phase 2A.11.

Links CMS projects (Prisma) to lending pool products.

Revision ID: 076
Revises: 075
"""
from alembic import op
import sqlalchemy as sa

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lending_pool_products",
                  sa.Column("project_id", sa.String(30), nullable=True, unique=True))
    op.create_index("ix_lpp_project_id", "lending_pool_products", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_lpp_project_id", table_name="lending_pool_products")
    op.drop_column("lending_pool_products", "project_id")
