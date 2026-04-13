"""Registration execution events — audit trail + replay timeline (Phase A).

Append-only events linked to registration_sessions for observability.

Revision ID: 094
Revises: 093
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registration_execution_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("flow_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("flow_version", sa.Integer(), nullable=True),
        sa.Column("step_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flow_steps.id", ondelete="SET NULL"), nullable=True),
        sa.Column("screen_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_step_screens.id", ondelete="SET NULL"), nullable=True),
        sa.Column("component_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_screen_components.id", ondelete="SET NULL"), nullable=True),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("public.persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_source", sa.Text(), nullable=False, server_default="runtime"),
        sa.Column("event_status", sa.Text(), nullable=True),
        sa.Column("payload_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_reg_exec_events_session_id", "registration_execution_events", ["session_id"], schema="public")
    op.create_index("ix_reg_exec_events_flow_id", "registration_execution_events", ["flow_id"], schema="public")
    op.create_index("ix_reg_exec_events_created_at", "registration_execution_events", ["created_at"], schema="public")
    op.create_index("ix_reg_exec_events_event_type", "registration_execution_events", ["event_type"], schema="public")
    op.create_index("ix_reg_exec_events_person_id", "registration_execution_events", ["person_id"], schema="public")
    op.create_index("ix_reg_exec_events_client_id", "registration_execution_events", ["client_id"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_reg_exec_events_client_id", table_name="registration_execution_events", schema="public")
    op.drop_index("ix_reg_exec_events_person_id", table_name="registration_execution_events", schema="public")
    op.drop_index("ix_reg_exec_events_event_type", table_name="registration_execution_events", schema="public")
    op.drop_index("ix_reg_exec_events_created_at", table_name="registration_execution_events", schema="public")
    op.drop_index("ix_reg_exec_events_flow_id", table_name="registration_execution_events", schema="public")
    op.drop_index("ix_reg_exec_events_session_id", table_name="registration_execution_events", schema="public")
    op.drop_table("registration_execution_events", schema="public")
