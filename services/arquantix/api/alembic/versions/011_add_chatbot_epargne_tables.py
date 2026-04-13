"""add_chatbot_epargne_tables

Revision ID: 011
Revises: 003
Create Date: 2026-01-21

Bot IA épargne: chatbot_sessions, chatbot_profiles, chatbot_conversation_turns,
chatbot_audit_events, chatbot_portfolio_proposals, chatbot_prompt_versions.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) chatbot_sessions
    op.create_table(
        "chatbot_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_chatbot_sessions_created_at", "chatbot_sessions", ["created_at"], schema="public")

    # 2) chatbot_profiles
    op.create_table(
        "chatbot_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("completeness_score", sa.Numeric(5, 4), server_default="0", nullable=False),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["public.chatbot_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_chatbot_profiles_session_id", "chatbot_profiles", ["session_id"], schema="public")
    op.create_index("ix_chatbot_profiles_session_version", "chatbot_profiles", ["session_id", "version"], schema="public")
    op.create_index("ix_chatbot_profiles_created_at", "chatbot_profiles", ["created_at"], schema="public")

    # 3) chatbot_conversation_turns
    op.create_table(
        "chatbot_conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("extracted_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("profile_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["public.chatbot_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_snapshot_id"], ["public.chatbot_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_chatbot_turns_session_id", "chatbot_conversation_turns", ["session_id"], schema="public")
    op.create_index("ix_chatbot_turns_session_created", "chatbot_conversation_turns", ["session_id", "created_at"], schema="public")

    # 4) chatbot_audit_events
    op.create_table(
        "chatbot_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["public.chatbot_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_chatbot_audit_session_id", "chatbot_audit_events", ["session_id"], schema="public")
    op.create_index("ix_chatbot_audit_session_created", "chatbot_audit_events", ["session_id", "created_at"], schema="public")
    op.create_index("ix_chatbot_audit_event_type", "chatbot_audit_events", ["event_type"], schema="public")
    op.create_index("ix_chatbot_audit_payload", "chatbot_audit_events", ["payload"], unique=False, postgresql_using="gin", schema="public")

    # 5) chatbot_portfolio_proposals
    op.create_table(
        "chatbot_portfolio_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("allocation", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("disclaimers", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["public.chatbot_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_chatbot_proposals_profile_id", "chatbot_portfolio_proposals", ["profile_id"], schema="public")
    op.create_index("ix_chatbot_proposals_created_at", "chatbot_portfolio_proposals", ["created_at"], schema="public")

    # 6) chatbot_prompt_versions
    op.create_table(
        "chatbot_prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index("ix_chatbot_prompt_name_hash", "chatbot_prompt_versions", ["name", "hash"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_chatbot_prompt_name_hash", table_name="chatbot_prompt_versions", schema="public")
    op.drop_table("chatbot_prompt_versions", schema="public")

    op.drop_index("ix_chatbot_proposals_created_at", table_name="chatbot_portfolio_proposals", schema="public")
    op.drop_index("ix_chatbot_proposals_profile_id", table_name="chatbot_portfolio_proposals", schema="public")
    op.drop_table("chatbot_portfolio_proposals", schema="public")

    op.drop_index("ix_chatbot_audit_payload", table_name="chatbot_audit_events", schema="public")
    op.drop_index("ix_chatbot_audit_event_type", table_name="chatbot_audit_events", schema="public")
    op.drop_index("ix_chatbot_audit_session_created", table_name="chatbot_audit_events", schema="public")
    op.drop_index("ix_chatbot_audit_session_id", table_name="chatbot_audit_events", schema="public")
    op.drop_table("chatbot_audit_events", schema="public")

    op.drop_index("ix_chatbot_turns_session_created", table_name="chatbot_conversation_turns", schema="public")
    op.drop_index("ix_chatbot_turns_session_id", table_name="chatbot_conversation_turns", schema="public")
    op.drop_table("chatbot_conversation_turns", schema="public")

    op.drop_index("ix_chatbot_profiles_created_at", table_name="chatbot_profiles", schema="public")
    op.drop_index("ix_chatbot_profiles_session_version", table_name="chatbot_profiles", schema="public")
    op.drop_index("ix_chatbot_profiles_session_id", table_name="chatbot_profiles", schema="public")
    op.drop_table("chatbot_profiles", schema="public")

    op.drop_index("ix_chatbot_sessions_created_at", table_name="chatbot_sessions", schema="public")
    op.drop_table("chatbot_sessions", schema="public")
