"""add pe_reconciliation_reports table

Revision ID: 054
Revises: 053
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "054"
down_revision = "053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_reconciliation_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reconciliation_type", sa.String(100), nullable=False),
        sa.Column("scope_type", sa.String(100), nullable=False),
        sa.Column("scope_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("differences_found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pe_recon_reports_type", "pe_reconciliation_reports", ["reconciliation_type"])
    op.create_index("ix_pe_recon_reports_scope", "pe_reconciliation_reports", ["scope_type", "scope_id"])
    op.create_index("ix_pe_recon_reports_status", "pe_reconciliation_reports", ["status"])
    op.create_index("ix_pe_recon_reports_created_at", "pe_reconciliation_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_pe_recon_reports_created_at", table_name="pe_reconciliation_reports")
    op.drop_index("ix_pe_recon_reports_status", table_name="pe_reconciliation_reports")
    op.drop_index("ix_pe_recon_reports_scope", table_name="pe_reconciliation_reports")
    op.drop_index("ix_pe_recon_reports_type", table_name="pe_reconciliation_reports")
    op.drop_table("pe_reconciliation_reports")
