"""Registration Engine Hardening (Phase 2B).

Adds:
  - registration_sessions.flow_version  (version locking)
  - registration_flow_steps.is_blocking (blocking vs non-blocking steps)
  - registration_session_steps table    (per-step state tracking)

Backfills:
  - flow_version from linked flow
  - is_blocking = true for all existing steps

Revision ID: 086
Revises: 085
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "086"
down_revision = "085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add is_blocking to registration_flow_steps (default true)
    op.add_column(
        "registration_flow_steps",
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default="true"),
        schema="public",
    )

    # 2. Add flow_version to registration_sessions
    op.add_column(
        "registration_sessions",
        sa.Column("flow_version", sa.Integer(), nullable=True),
        schema="public",
    )

    # Backfill flow_version from linked flow
    conn = op.get_bind()
    conn.execute(text(
        "UPDATE public.registration_sessions s "
        "SET flow_version = f.version "
        "FROM public.registration_flows f "
        "WHERE s.flow_id = f.id AND s.flow_version IS NULL"
    ))

    # Default remaining (if any) to 1
    conn.execute(text(
        "UPDATE public.registration_sessions SET flow_version = 1 WHERE flow_version IS NULL"
    ))

    op.alter_column(
        "registration_sessions", "flow_version",
        nullable=False, server_default="1",
        schema="public",
    )

    # 3. Create registration_session_steps table
    op.create_table(
        "registration_session_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flow_steps.id"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_screen_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_step_screens.id"), nullable=True),
        sa.Column("metadata_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("session_id", "step_id", name="uq_reg_session_step"),
        schema="public",
    )

    # Make consent step non-blocking in seeded flows
    conn.execute(text(
        "UPDATE public.registration_flow_steps SET is_blocking = false "
        "WHERE step_key = 'consent'"
    ))


def downgrade() -> None:
    op.drop_table("registration_session_steps", schema="public")
    op.drop_column("registration_sessions", "flow_version", schema="public")
    op.drop_column("registration_flow_steps", "is_blocking", schema="public")
