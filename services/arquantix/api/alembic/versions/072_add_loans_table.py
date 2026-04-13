"""Add loans and loan_interest_accruals tables for P2P lending.

Revision ID: 072
Revises: 071
Create Date: 2026-03-21

Phase 2A: Internal P2P Lending Engine.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lender_client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("borrower_client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("principal", sa.Numeric(30, 10), nullable=False),
        sa.Column("interest_rate_bps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("platform_fee_bps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_days", sa.Integer, nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("repaid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("lender_position_atom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("borrower_position_atom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_loans_lender_client_id", "loans", ["lender_client_id"], schema="public")
    op.create_index("ix_loans_borrower_client_id", "loans", ["borrower_client_id"], schema="public")
    op.create_index("ix_loans_status", "loans", ["status"], schema="public")
    op.create_index("ix_loans_asset", "loans", ["asset"], schema="public")

    op.create_table(
        "loan_interest_accruals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("loan_id", UUID(as_uuid=True), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accrued_amount", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("last_accrual_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_loan_interest_accruals_loan_id", "loan_interest_accruals", ["loan_id"], schema="public")


def downgrade() -> None:
    op.drop_table("loan_interest_accruals", schema="public")
    op.drop_table("loans", schema="public")
