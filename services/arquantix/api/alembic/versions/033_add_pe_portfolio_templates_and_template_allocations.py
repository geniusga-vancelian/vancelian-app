"""add pe_portfolio_templates and pe_template_allocations tables
(Portfolio Engine — catalog / template layer)

Revision ID: 033
Revises: 032
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- pe_portfolio_templates ------------------------------------------------
    op.create_table(
        "pe_portfolio_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_product_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("template_code", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("base_currency", sa.String(20), nullable=False, server_default="EUR"),
        sa.Column("risk_profile", sa.String(50), nullable=True),
        sa.Column(
            "strategy_definition_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_strategy_definitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_pe_portfolio_templates_template_code",
        "pe_portfolio_templates",
        ["template_code"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_pe_portfolio_templates_product_id",
        "pe_portfolio_templates",
        ["product_id"],
        schema="public",
    )
    op.create_index(
        "ix_pe_portfolio_templates_metadata",
        "pe_portfolio_templates",
        ["metadata"],
        postgresql_using="gin",
        schema="public",
    )

    # -- pe_template_allocations -----------------------------------------------
    op.create_table(
        "pe_template_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_portfolio_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "instrument_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_instruments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_weight", sa.Numeric(12, 6), nullable=False),
        sa.Column("min_weight", sa.Numeric(12, 6), nullable=True),
        sa.Column("max_weight", sa.Numeric(12, 6), nullable=True),
        sa.Column("allocation_priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "instrument_id", name="uq_pe_template_allocations_template_instrument"),
        schema="public",
    )
    op.create_index(
        "ix_pe_template_allocations_template_id",
        "pe_template_allocations",
        ["template_id"],
        schema="public",
    )
    op.create_index(
        "ix_pe_template_allocations_instrument_id",
        "pe_template_allocations",
        ["instrument_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_pe_template_allocations_instrument_id", table_name="pe_template_allocations", schema="public")
    op.drop_index("ix_pe_template_allocations_template_id", table_name="pe_template_allocations", schema="public")
    op.drop_table("pe_template_allocations", schema="public")

    op.drop_index("ix_pe_portfolio_templates_metadata", table_name="pe_portfolio_templates", schema="public")
    op.drop_index("ix_pe_portfolio_templates_product_id", table_name="pe_portfolio_templates", schema="public")
    op.drop_index("ix_pe_portfolio_templates_template_code", table_name="pe_portfolio_templates", schema="public")
    op.drop_table("pe_portfolio_templates", schema="public")
