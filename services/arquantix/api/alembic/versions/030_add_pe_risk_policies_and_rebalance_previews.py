"""add pe_risk_policies, pe_rebalance_previews, pe_rebalance_preview_items (Portfolio Engine)

Revision ID: 030
Revises: 029
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pe_risk_policies ──
    op.create_table(
        "pe_risk_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sleeve_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("max_asset_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("max_asset_class_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("max_position_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("max_leverage", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("volatility_limit", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("liquidity_profile_limit", sa.String(length=50), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sleeve_id"], ["public.pe_sleeves.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "(portfolio_id IS NOT NULL AND sleeve_id IS NULL) "
            "OR (portfolio_id IS NULL AND sleeve_id IS NOT NULL)",
            name="ck_pe_risk_policies_xor_context",
        ),
        schema="public",
    )

    op.create_index("ix_pe_risk_policies_portfolio_id", "pe_risk_policies", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_risk_policies_sleeve_id", "pe_risk_policies", ["sleeve_id"], unique=False, schema="public")
    op.create_unique_constraint("uq_pe_risk_policies_portfolio", "pe_risk_policies", ["portfolio_id"], schema="public")
    op.create_unique_constraint("uq_pe_risk_policies_sleeve", "pe_risk_policies", ["sleeve_id"], schema="public")

    # ── pe_rebalance_previews ──
    op.create_table(
        "pe_rebalance_previews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rebalance_policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("drift_score", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("total_turnover", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rebalance_policy_id"], ["public.pe_rebalance_policies.id"], ondelete="SET NULL"),
        schema="public",
    )

    op.create_index("ix_pe_rebalance_previews_portfolio_id", "pe_rebalance_previews", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_rebalance_previews_generated_at", "pe_rebalance_previews", ["generated_at"], unique=False, schema="public")

    # ── pe_rebalance_preview_items ──
    op.create_table(
        "pe_rebalance_preview_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preview_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("target_weight", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("drift", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("trade_required", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("trade_direction", sa.String(length=10), nullable=True),
        sa.Column("estimated_trade_size", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["preview_id"], ["public.pe_rebalance_previews.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["public.pe_instruments.id"], ondelete="CASCADE"),
        schema="public",
    )

    op.create_index("ix_pe_rebalance_preview_items_preview_id", "pe_rebalance_preview_items", ["preview_id"], unique=False, schema="public")
    op.create_index("ix_pe_rebalance_preview_items_instrument_id", "pe_rebalance_preview_items", ["instrument_id"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_rebalance_preview_items_instrument_id", table_name="pe_rebalance_preview_items", schema="public")
    op.drop_index("ix_pe_rebalance_preview_items_preview_id", table_name="pe_rebalance_preview_items", schema="public")
    op.drop_table("pe_rebalance_preview_items", schema="public")
    op.drop_index("ix_pe_rebalance_previews_generated_at", table_name="pe_rebalance_previews", schema="public")
    op.drop_index("ix_pe_rebalance_previews_portfolio_id", table_name="pe_rebalance_previews", schema="public")
    op.drop_table("pe_rebalance_previews", schema="public")
    op.drop_constraint("uq_pe_risk_policies_sleeve", "pe_risk_policies", schema="public", type_="unique")
    op.drop_constraint("uq_pe_risk_policies_portfolio", "pe_risk_policies", schema="public", type_="unique")
    op.drop_index("ix_pe_risk_policies_sleeve_id", table_name="pe_risk_policies", schema="public")
    op.drop_index("ix_pe_risk_policies_portfolio_id", table_name="pe_risk_policies", schema="public")
    op.drop_table("pe_risk_policies", schema="public")
