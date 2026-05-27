"""Phase 9 — defi_observability_job_runs (historique ticks observabilité)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "168"
down_revision = "167"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "defi_observability_job_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("error_json", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_defi_obs_job_runs_job_name",
        "defi_observability_job_runs",
        ["job_name"],
        schema="public",
    )
    op.create_index(
        "ix_defi_obs_job_runs_started_at",
        "defi_observability_job_runs",
        ["started_at"],
        schema="public",
    )
    op.create_index(
        "ix_defi_obs_job_runs_status",
        "defi_observability_job_runs",
        ["status"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_defi_obs_job_runs_status", table_name="defi_observability_job_runs", schema="public")
    op.drop_index("ix_defi_obs_job_runs_started_at", table_name="defi_observability_job_runs", schema="public")
    op.drop_index("ix_defi_obs_job_runs_job_name", table_name="defi_observability_job_runs", schema="public")
    op.drop_table("defi_observability_job_runs", schema="public")
