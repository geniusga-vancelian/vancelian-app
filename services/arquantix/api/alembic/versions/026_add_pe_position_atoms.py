"""add pe_position_atoms table (Portfolio Engine — position layer)

Revision ID: 026
Revises: 025
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_position_atoms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sleeve_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), nullable=False),
        # TODO: add FK to pe_strategy_instances.id when the strategies module is implemented.
        sa.Column("strategy_instance_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'open'"), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=30, scale=10), server_default=sa.text("0"), nullable=False),
        sa.Column("available_quantity", sa.Numeric(precision=30, scale=10), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_quantity", sa.Numeric(precision=30, scale=10), server_default=sa.text("0"), nullable=False),
        sa.Column("market_value", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("cost_basis", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("average_entry_price", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("accrued_income", sa.Numeric(precision=30, scale=10), server_default=sa.text("0"), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(precision=30, scale=10), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(precision=30, scale=10), server_default=sa.text("0"), nullable=False),
        sa.Column("lockup_status", sa.String(length=30), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["public.pe_portfolios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sleeve_id"], ["public.pe_sleeves.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["wallet_id"], ["public.pe_wallet_containers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["instrument_id"], ["public.pe_instruments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_position_id"], ["public.pe_position_atoms.id"], ondelete="SET NULL"),
        schema="public",
    )

    op.create_index("ix_pe_position_atoms_portfolio_id", "pe_position_atoms", ["portfolio_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_sleeve_id", "pe_position_atoms", ["sleeve_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_wallet_id", "pe_position_atoms", ["wallet_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_instrument_id", "pe_position_atoms", ["instrument_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_strategy_instance_id", "pe_position_atoms", ["strategy_instance_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_parent_position_id", "pe_position_atoms", ["parent_position_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_position_type", "pe_position_atoms", ["position_type"], unique=False, schema="public")
    op.create_index("ix_pe_position_atoms_status", "pe_position_atoms", ["status"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_position_atoms_status", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_position_type", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_parent_position_id", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_strategy_instance_id", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_instrument_id", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_wallet_id", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_sleeve_id", table_name="pe_position_atoms", schema="public")
    op.drop_index("ix_pe_position_atoms_portfolio_id", table_name="pe_position_atoms", schema="public")
    op.drop_table("pe_position_atoms", schema="public")
