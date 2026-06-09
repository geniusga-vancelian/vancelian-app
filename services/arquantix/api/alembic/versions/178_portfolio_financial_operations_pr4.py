"""PR-4 — portfolio_financial_operations (1 portefeuille = 1 opération active)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "178"
down_revision = "176"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_financial_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("operation_type", sa.String(40), nullable=False),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index(
        "ix_pfo_portfolio_id",
        "portfolio_financial_operations",
        ["portfolio_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_pfo_expires_at",
        "portfolio_financial_operations",
        ["expires_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_pfo_execution_id",
        "portfolio_financial_operations",
        ["execution_id"],
        unique=False,
        schema="public",
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_pfo_active_portfolio
            ON public.portfolio_financial_operations (portfolio_id)
            WHERE status = 'ACTIVE' AND released_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS public.uq_pfo_active_portfolio"))
    op.drop_index("ix_pfo_execution_id", table_name="portfolio_financial_operations", schema="public")
    op.drop_index("ix_pfo_expires_at", table_name="portfolio_financial_operations", schema="public")
    op.drop_index("ix_pfo_portfolio_id", table_name="portfolio_financial_operations", schema="public")
    op.drop_table("portfolio_financial_operations", schema="public")
