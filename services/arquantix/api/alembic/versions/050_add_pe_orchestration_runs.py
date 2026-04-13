"""add pe_orchestration_runs table

Revision ID: 050
Revises: 049
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_orchestration_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("signals_detected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("actions_taken", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "rebalance_preview_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_rebalance_previews.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("abort_reason", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pe_orchestration_runs_portfolio_id",
        "pe_orchestration_runs",
        ["portfolio_id"],
    )
    op.create_index(
        "ix_pe_orchestration_runs_status",
        "pe_orchestration_runs",
        ["status"],
    )
    op.create_index(
        "ix_pe_orchestration_runs_started_at",
        "pe_orchestration_runs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pe_orchestration_runs_started_at", table_name="pe_orchestration_runs")
    op.drop_index("ix_pe_orchestration_runs_status", table_name="pe_orchestration_runs")
    op.drop_index("ix_pe_orchestration_runs_portfolio_id", table_name="pe_orchestration_runs")
    op.drop_table("pe_orchestration_runs")
