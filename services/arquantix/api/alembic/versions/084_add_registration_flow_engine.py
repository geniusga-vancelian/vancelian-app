"""Add Registration Flow Engine tables (Phase 2A).

Creates 7 tables:
  - registration_jurisdictions
  - registration_flows
  - registration_flow_steps
  - registration_step_screens
  - registration_screen_components
  - registration_sessions
  - registration_session_data

Revision ID: 084
Revises: 083
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- registration_jurisdictions ---
    op.create_table(
        "registration_jurisdictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("entity_name", sa.Text(), nullable=True),
        sa.Column("default_language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )

    # --- registration_flows ---
    op.create_table(
        "registration_flows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("jurisdiction_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_jurisdictions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("entrypoint_type", sa.Text(), nullable=False, server_default="individual"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("jurisdiction_id", "entrypoint_type", "version", name="uq_reg_flow_jurisdiction_entry_version"),
        schema="public",
    )

    # --- registration_flow_steps ---
    op.create_table(
        "registration_flow_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("flow_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("visibility_rule_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("completion_rule_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("flow_id", "step_key", name="uq_reg_step_flow_key"),
        schema="public",
    )

    # --- registration_step_screens ---
    op.create_table(
        "registration_step_screens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("step_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flow_steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("screen_key", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("layout_type", sa.Text(), nullable=False, server_default="form"),
        sa.Column("config_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("step_id", "screen_key", name="uq_reg_screen_step_key"),
        schema="public",
    )

    # --- registration_screen_components ---
    op.create_table(
        "registration_screen_components",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("screen_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_step_screens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_type", sa.Text(), nullable=False),
        sa.Column("component_key", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("props_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("binding_slug", sa.Text(), nullable=True),
        sa.Column("visibility_rule_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_rule_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("screen_id", "component_key", name="uq_reg_component_screen_key"),
        schema="public",
    )

    # --- registration_sessions ---
    op.create_table(
        "registration_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("jurisdiction_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_jurisdictions.id"), nullable=False),
        sa.Column("flow_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flows.id"), nullable=False),
        sa.Column("person_id", UUID(as_uuid=True), sa.ForeignKey("public.persons.id"), nullable=True),
        sa.Column("client_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="in_progress"),
        sa.Column("current_step_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_flow_steps.id"), nullable=True),
        sa.Column("current_screen_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_step_screens.id"), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_reg_session_person", "registration_sessions", ["person_id"], schema="public")

    # --- registration_session_data ---
    op.create_table(
        "registration_session_data",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("public.registration_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_slug", sa.Text(), nullable=False),
        sa.Column("value_json", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="user_input"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "field_slug", name="uq_reg_session_data_slug"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("registration_session_data", schema="public")
    op.drop_index("ix_reg_session_person", table_name="registration_sessions", schema="public")
    op.drop_table("registration_sessions", schema="public")
    op.drop_table("registration_screen_components", schema="public")
    op.drop_table("registration_step_screens", schema="public")
    op.drop_table("registration_flow_steps", schema="public")
    op.drop_table("registration_flows", schema="public")
    op.drop_table("registration_jurisdictions", schema="public")
