"""add origin_product_id to pe_portfolios (nullable FK to pe_product_definitions)

Revision ID: 035
Revises: 034
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pe_portfolios",
        sa.Column(
            "origin_product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_product_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )
    op.create_index(
        "ix_pe_portfolios_origin_product_id",
        "pe_portfolios",
        ["origin_product_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_pe_portfolios_origin_product_id", table_name="pe_portfolios", schema="public")
    op.drop_column("pe_portfolios", "origin_product_id", schema="public")
