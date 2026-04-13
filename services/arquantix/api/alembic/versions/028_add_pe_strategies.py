"""add pe_strategy_definitions and pe_strategy_instances tables (Portfolio Engine — strategy layer)

Revision ID: 028
Revises: 027
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pe_strategy_definitions ──
    op.create_table(
        "pe_strategy_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("strategy_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parameters_schema", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_pe_strategy_definitions_code"),
        schema="public",
    )

    op.create_index("ix_pe_strategy_definitions_type", "pe_strategy_definitions", ["strategy_type"], unique=False, schema="public")

    # ── pe_strategy_instances ──
    op.create_table(
        "pe_strategy_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sleeve_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'active'"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sleeve_id"], ["public.pe_sleeves.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["strategy_definition_id"], ["public.pe_strategy_definitions.id"], ondelete="RESTRICT"),
        schema="public",
    )

    op.create_index("ix_pe_strategy_instances_portfolio_id", "pe_strategy_instances", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_strategy_instances_sleeve_id", "pe_strategy_instances", ["sleeve_id"], unique=False, schema="public")
    op.create_index("ix_pe_strategy_instances_definition_id", "pe_strategy_instances", ["strategy_definition_id"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_strategy_instances_definition_id", table_name="pe_strategy_instances", schema="public")
    op.drop_index("ix_pe_strategy_instances_sleeve_id", table_name="pe_strategy_instances", schema="public")
    op.drop_index("ix_pe_strategy_instances_portfolio_id", table_name="pe_strategy_instances", schema="public")
    op.drop_table("pe_strategy_instances", schema="public")
    op.drop_index("ix_pe_strategy_definitions_type", table_name="pe_strategy_definitions", schema="public")
    op.drop_table("pe_strategy_definitions", schema="public")
