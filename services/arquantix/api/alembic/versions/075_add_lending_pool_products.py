"""Add lending_pool_products table — Phase 2A.10.

Revision ID: 075
Revises: 074
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "075"
down_revision = "074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lending_pool_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lending_pool_id", UUID(as_uuid=True),
                  sa.ForeignKey("lending_pools.id", ondelete="RESTRICT"),
                  nullable=False, unique=True),
        sa.Column("product_type", sa.String(50), nullable=False, server_default="exclusive_offer"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("borrower_client_id", UUID(as_uuid=True),
                  sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("target_size", sa.Numeric(30, 10), nullable=False),
        sa.Column("current_raised", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("min_ticket", sa.Numeric(30, 10), nullable=True),
        sa.Column("max_ticket", sa.Numeric(30, 10), nullable=True),
        sa.Column("supply_apr_bps", sa.Numeric(10, 2), nullable=False, server_default="300"),
        sa.Column("borrow_apr_bps", sa.Numeric(10, 2), nullable=False, server_default="500"),
        sa.Column("use_of_funds", sa.Text, nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("maturity_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_lpp_pool_id", "lending_pool_products", ["lending_pool_id"])
    op.create_index("ix_lpp_borrower", "lending_pool_products", ["borrower_client_id"])
    op.create_index("ix_lpp_status", "lending_pool_products", ["status"])


def downgrade() -> None:
    op.drop_table("lending_pool_products")
