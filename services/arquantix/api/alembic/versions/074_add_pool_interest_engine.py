"""Add pool interest engine tables + rate columns.

Revision ID: 074
Revises: 073
Create Date: 2026-03-21

Phase 2A.7: Pool-based Interest Engine (daily, pro-rata, bounded).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rate columns on lending_pools
    op.add_column("lending_pools", sa.Column("borrow_rate_bps", sa.Numeric(10, 2), nullable=False, server_default="500"), schema="public")
    op.add_column("lending_pools", sa.Column("supply_rate_bps", sa.Numeric(10, 2), nullable=False, server_default="300"), schema="public")

    # Daily snapshot
    op.create_table(
        "pool_interest_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pool_id", UUID(as_uuid=True), sa.ForeignKey("lending_pools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("total_borrowed", sa.Numeric(30, 10), nullable=False),
        sa.Column("borrow_rate_bps", sa.Numeric(10, 2), nullable=False),
        sa.Column("supply_rate_bps", sa.Numeric(10, 2), nullable=False),
        sa.Column("interest_generated", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("interest_to_lenders", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("platform_fee", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_pool_interest_snapshots_pool_date",
        "pool_interest_snapshots", ["pool_id", "date"],
        unique=True, schema="public",
    )

    # Lender daily accrual
    op.create_table(
        "lender_interest_accruals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pool_id", UUID(as_uuid=True), sa.ForeignKey("lending_pools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("allocated_amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("interest_earned", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_lender_interest_accruals_client_pool_date",
        "lender_interest_accruals", ["client_id", "pool_id", "date"],
        unique=True, schema="public",
    )

    # Borrower daily accrual
    op.create_table(
        "borrower_interest_accruals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pool_id", UUID(as_uuid=True), sa.ForeignKey("lending_pools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("borrowed_amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("interest_due", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_borrower_interest_accruals_client_pool_date",
        "borrower_interest_accruals", ["client_id", "pool_id", "date"],
        unique=True, schema="public",
    )


def downgrade() -> None:
    op.drop_table("borrower_interest_accruals", schema="public")
    op.drop_table("lender_interest_accruals", schema="public")
    op.drop_table("pool_interest_snapshots", schema="public")
    op.drop_column("lending_pools", "supply_rate_bps", schema="public")
    op.drop_column("lending_pools", "borrow_rate_bps", schema="public")
