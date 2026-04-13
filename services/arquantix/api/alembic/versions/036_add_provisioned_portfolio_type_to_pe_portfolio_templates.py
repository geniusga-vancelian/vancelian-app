"""add provisioned_portfolio_type to pe_portfolio_templates

Revision ID: 036
Revises: 035
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pe_portfolio_templates",
        sa.Column(
            "provisioned_portfolio_type",
            sa.String(50),
            nullable=False,
            server_default="bundle_portfolio",
        ),
        schema="public",
    )
    op.alter_column(
        "pe_portfolio_templates",
        "provisioned_portfolio_type",
        server_default=None,
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("pe_portfolio_templates", "provisioned_portfolio_type", schema="public")
