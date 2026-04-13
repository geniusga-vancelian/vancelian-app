"""add pe_job_runs table

Revision ID: 053
Revises: 052
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "053"
down_revision = "052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_job_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("scope_type", sa.String(100), nullable=False),
        sa.Column("scope_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="started"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pe_job_runs_job_type", "pe_job_runs", ["job_type"])
    op.create_index("ix_pe_job_runs_scope", "pe_job_runs", ["scope_type", "scope_id"])
    op.create_index("ix_pe_job_runs_status", "pe_job_runs", ["status"])
    op.create_index("ix_pe_job_runs_started_at", "pe_job_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_pe_job_runs_started_at", table_name="pe_job_runs")
    op.drop_index("ix_pe_job_runs_status", table_name="pe_job_runs")
    op.drop_index("ix_pe_job_runs_scope", table_name="pe_job_runs")
    op.drop_index("ix_pe_job_runs_job_type", table_name="pe_job_runs")
    op.drop_table("pe_job_runs")
