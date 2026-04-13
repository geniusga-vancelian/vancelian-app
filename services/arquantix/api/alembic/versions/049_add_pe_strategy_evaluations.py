"""add pe_strategy_evaluations table

Revision ID: 049
Revises: 048
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_strategy_evaluations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "strategy_instance_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_strategy_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("signal_type", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "evaluation_timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pe_strategy_evaluations_portfolio_id",
        "pe_strategy_evaluations",
        ["portfolio_id"],
    )
    op.create_index(
        "ix_pe_strategy_evaluations_instance_id",
        "pe_strategy_evaluations",
        ["strategy_instance_id"],
    )
    op.create_index(
        "ix_pe_strategy_evaluations_signal_type",
        "pe_strategy_evaluations",
        ["signal_type"],
    )
    op.create_index(
        "ix_pe_strategy_evaluations_eval_ts",
        "pe_strategy_evaluations",
        ["evaluation_timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_pe_strategy_evaluations_eval_ts", table_name="pe_strategy_evaluations")
    op.drop_index("ix_pe_strategy_evaluations_signal_type", table_name="pe_strategy_evaluations")
    op.drop_index("ix_pe_strategy_evaluations_instance_id", table_name="pe_strategy_evaluations")
    op.drop_index("ix_pe_strategy_evaluations_portfolio_id", table_name="pe_strategy_evaluations")
    op.drop_table("pe_strategy_evaluations")
