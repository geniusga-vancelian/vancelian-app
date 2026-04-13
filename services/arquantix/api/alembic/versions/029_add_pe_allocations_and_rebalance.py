"""add pe_target_allocations and pe_rebalance_policies tables (Portfolio Engine)

Revision ID: 029
Revises: 028
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pe_target_allocations ──
    op.create_table(
        "pe_target_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sleeve_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_weight", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("min_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("max_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("rebalance_priority", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sleeve_id"], ["public.pe_sleeves.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["public.pe_instruments.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "(portfolio_id IS NOT NULL AND sleeve_id IS NULL) "
            "OR (portfolio_id IS NULL AND sleeve_id IS NOT NULL)",
            name="ck_pe_target_allocations_xor_context",
        ),
        schema="public",
    )

    op.create_index("ix_pe_target_allocations_portfolio_id", "pe_target_allocations", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_target_allocations_sleeve_id", "pe_target_allocations", ["sleeve_id"], unique=False, schema="public")
    op.create_index("ix_pe_target_allocations_instrument_id", "pe_target_allocations", ["instrument_id"], unique=False, schema="public")
    op.create_unique_constraint("uq_pe_target_allocations_portfolio_instrument", "pe_target_allocations", ["portfolio_id", "instrument_id"], schema="public")
    op.create_unique_constraint("uq_pe_target_allocations_sleeve_instrument", "pe_target_allocations", ["sleeve_id", "instrument_id"], schema="public")

    # ── pe_rebalance_policies ──
    op.create_table(
        "pe_rebalance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sleeve_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("frequency", sa.String(length=50), nullable=True),
        sa.Column("drift_threshold", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("min_trade_size", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("transaction_cost_model", sa.String(length=50), nullable=True),
        sa.Column("lockup_aware", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("cash_flow_priority", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sleeve_id"], ["public.pe_sleeves.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "(portfolio_id IS NOT NULL AND sleeve_id IS NULL) "
            "OR (portfolio_id IS NULL AND sleeve_id IS NOT NULL)",
            name="ck_pe_rebalance_policies_xor_context",
        ),
        schema="public",
    )

    op.create_index("ix_pe_rebalance_policies_portfolio_id", "pe_rebalance_policies", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_rebalance_policies_sleeve_id", "pe_rebalance_policies", ["sleeve_id"], unique=False, schema="public")
    op.create_unique_constraint("uq_pe_rebalance_policies_portfolio", "pe_rebalance_policies", ["portfolio_id"], schema="public")
    op.create_unique_constraint("uq_pe_rebalance_policies_sleeve", "pe_rebalance_policies", ["sleeve_id"], schema="public")


def downgrade() -> None:
    op.drop_constraint("uq_pe_rebalance_policies_sleeve", "pe_rebalance_policies", schema="public", type_="unique")
    op.drop_constraint("uq_pe_rebalance_policies_portfolio", "pe_rebalance_policies", schema="public", type_="unique")
    op.drop_index("ix_pe_rebalance_policies_sleeve_id", table_name="pe_rebalance_policies", schema="public")
    op.drop_index("ix_pe_rebalance_policies_portfolio_id", table_name="pe_rebalance_policies", schema="public")
    op.drop_table("pe_rebalance_policies", schema="public")
    op.drop_constraint("uq_pe_target_allocations_sleeve_instrument", "pe_target_allocations", schema="public", type_="unique")
    op.drop_constraint("uq_pe_target_allocations_portfolio_instrument", "pe_target_allocations", schema="public", type_="unique")
    op.drop_index("ix_pe_target_allocations_instrument_id", table_name="pe_target_allocations", schema="public")
    op.drop_index("ix_pe_target_allocations_sleeve_id", table_name="pe_target_allocations", schema="public")
    op.drop_index("ix_pe_target_allocations_portfolio_id", table_name="pe_target_allocations", schema="public")
    op.drop_table("pe_target_allocations", schema="public")
