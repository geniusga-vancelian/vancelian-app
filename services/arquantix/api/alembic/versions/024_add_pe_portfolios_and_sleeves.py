"""add pe_portfolios and pe_sleeves tables (Portfolio Engine)

Revision ID: 024
Revises: 023
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pe_portfolios ──
    op.create_table(
        "pe_portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # TODO: add FK to pe_clients.id when the clients module is implemented.
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("portfolio_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_currency", sa.String(length=20), server_default=sa.text("'EUR'"), nullable=False),
        sa.Column("risk_profile", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'active'"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_portfolio_id"], ["public.pe_portfolios.id"], ondelete="SET NULL"),
        schema="public",
    )

    op.create_index("ix_pe_portfolios_client_id", "pe_portfolios", ["client_id"], unique=False, schema="public")
    op.create_index("ix_pe_portfolios_portfolio_type", "pe_portfolios", ["portfolio_type"], unique=False, schema="public")

    # ── pe_sleeves ──
    op.create_table(
        "pe_sleeves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sleeve_type", sa.String(length=50), nullable=False),
        sa.Column("allocation_target", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        schema="public",
    )

    op.create_index("ix_pe_sleeves_portfolio_id", "pe_sleeves", ["portfolio_id"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_sleeves_portfolio_id", table_name="pe_sleeves", schema="public")
    op.drop_table("pe_sleeves", schema="public")
    op.drop_index("ix_pe_portfolios_portfolio_type", table_name="pe_portfolios", schema="public")
    op.drop_index("ix_pe_portfolios_client_id", table_name="pe_portfolios", schema="public")
    op.drop_table("pe_portfolios", schema="public")
