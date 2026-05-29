"""Cost basis V2 — exécutions normalisées (PRU multi-sources, FX figé)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "170"
down_revision = "169"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cost_basis_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position_asset", sa.String(20), nullable=False),
        sa.Column("event_kind", sa.String(16), nullable=False),
        sa.Column("quantity", sa.Numeric(30, 18), nullable=False),
        sa.Column("native_quote_asset", sa.String(20), nullable=False),
        sa.Column("native_execution_price", sa.Numeric(30, 18), nullable=False),
        sa.Column("native_notional", sa.Numeric(30, 18), nullable=False),
        sa.Column("execution_price_usdc", sa.Numeric(30, 18), nullable=False),
        sa.Column("execution_notional_usdc", sa.Numeric(30, 18), nullable=False),
        sa.Column("execution_price_eur", sa.Numeric(30, 18), nullable=False),
        sa.Column("execution_notional_eur", sa.Numeric(30, 18), nullable=False),
        sa.Column("eurusd_rate_at_execution", sa.Numeric(30, 10), nullable=False),
        sa.Column("fees_usdc", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("fees_eur", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("provider_source", sa.String(32), nullable=False),
        sa.Column("provider_execution_id", sa.String(255), nullable=False),
        sa.Column("tx_hash", sa.String(120), nullable=True),
        sa.Column("counterparty_asset", sa.String(20), nullable=True),
        sa.Column("portfolio_scope", sa.String(32), nullable=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_cost_basis_executions_client_asset",
        "cost_basis_executions",
        ["client_id", "position_asset"],
        schema="public",
    )
    op.create_index(
        "ix_cost_basis_executions_executed_at",
        "cost_basis_executions",
        ["executed_at"],
        schema="public",
    )
    op.create_unique_constraint(
        "uq_cost_basis_executions_provider",
        "cost_basis_executions",
        ["provider_source", "provider_execution_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_cost_basis_executions_provider",
        "cost_basis_executions",
        schema="public",
        type_="unique",
    )
    op.drop_index("ix_cost_basis_executions_executed_at", table_name="cost_basis_executions", schema="public")
    op.drop_index("ix_cost_basis_executions_client_asset", table_name="cost_basis_executions", schema="public")
    op.drop_table("cost_basis_executions", schema="public")
