"""add pe_instruments table (Portfolio Engine — Instruments registry)

Revision ID: 023
Revises: 022
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("instrument_type", sa.String(length=50), nullable=False),
        sa.Column("liquidity_profile", sa.String(length=50), nullable=True),
        sa.Column("lockup_period_days", sa.Integer(), nullable=True),
        sa.Column("valuation_method", sa.String(length=50), nullable=True),
        sa.Column("yield_source", sa.String(length=100), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.ForeignKeyConstraint(["asset_id"], ["public.pe_assets.id"], ondelete="RESTRICT"),
        schema="public",
    )

    op.create_index("ix_pe_instruments_code", "pe_instruments", ["code"], unique=True, schema="public")
    op.create_index("ix_pe_instruments_asset_id", "pe_instruments", ["asset_id"], unique=False, schema="public")
    op.create_index("ix_pe_instruments_instrument_type", "pe_instruments", ["instrument_type"], unique=False, schema="public")
    op.create_index(
        "ix_pe_instruments_metadata",
        "pe_instruments",
        ["metadata"],
        unique=False,
        schema="public",
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_pe_instruments_metadata", table_name="pe_instruments", schema="public")
    op.drop_index("ix_pe_instruments_instrument_type", table_name="pe_instruments", schema="public")
    op.drop_index("ix_pe_instruments_asset_id", table_name="pe_instruments", schema="public")
    op.drop_index("ix_pe_instruments_code", table_name="pe_instruments", schema="public")
    op.drop_table("pe_instruments", schema="public")
