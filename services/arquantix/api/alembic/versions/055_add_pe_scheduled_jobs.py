"""add pe_scheduled_jobs table

Revision ID: 055
Revises: 054
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_scheduled_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column("job_type", sa.String(100), nullable=False),
        sa.Column("scope_type", sa.String(100), nullable=False),
        sa.Column("scope_id", sa.String(255), nullable=True),
        sa.Column("schedule_type", sa.String(30), nullable=False, server_default="interval"),
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("interval_seconds", sa.Integer, nullable=True),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_pe_scheduled_jobs_job_type", "pe_scheduled_jobs", ["job_type"])
    op.create_index("ix_pe_scheduled_jobs_is_enabled", "pe_scheduled_jobs", ["is_enabled"])
    op.create_index("ix_pe_scheduled_jobs_next_run_at", "pe_scheduled_jobs", ["next_run_at"])
    op.create_index("ix_pe_scheduled_jobs_scope", "pe_scheduled_jobs", ["scope_type", "scope_id"])


def downgrade() -> None:
    op.drop_index("ix_pe_scheduled_jobs_scope", table_name="pe_scheduled_jobs")
    op.drop_index("ix_pe_scheduled_jobs_next_run_at", table_name="pe_scheduled_jobs")
    op.drop_index("ix_pe_scheduled_jobs_is_enabled", table_name="pe_scheduled_jobs")
    op.drop_index("ix_pe_scheduled_jobs_job_type", table_name="pe_scheduled_jobs")
    op.drop_table("pe_scheduled_jobs")
