"""add pe_assets table (Portfolio Engine — Assets registry)

Revision ID: 022
Revises: 021_logo_filename
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "022"
down_revision = "021_logo_filename"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("valuation_source", sa.String(length=100), nullable=True),
        sa.Column("liquidity_profile", sa.String(length=50), nullable=True),
        sa.Column("risk_profile", sa.String(length=50), nullable=True),
        sa.Column("supports_staking", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("supports_collateral", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("supports_borrowing", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("supports_yield", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
        schema="public",
    )

    op.create_index("ix_pe_assets_symbol", "pe_assets", ["symbol"], unique=True, schema="public")
    op.create_index("ix_pe_assets_asset_type", "pe_assets", ["asset_type"], unique=False, schema="public")
    op.create_index(
        "ix_pe_assets_metadata",
        "pe_assets",
        ["metadata"],
        unique=False,
        schema="public",
        postgresql_using="gin",
    )

def downgrade() -> None:
    op.drop_index("ix_pe_assets_metadata", table_name="pe_assets", schema="public")
    op.drop_index("ix_pe_assets_asset_type", table_name="pe_assets", schema="public")
    op.drop_index("ix_pe_assets_symbol", table_name="pe_assets", schema="public")
    op.drop_table("pe_assets", schema="public")
