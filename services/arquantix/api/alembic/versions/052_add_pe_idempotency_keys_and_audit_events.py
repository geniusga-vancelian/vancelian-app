"""add pe_idempotency_keys and pe_audit_events tables

Revision ID: 052
Revises: 051
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pe_idempotency_keys ──
    op.create_table(
        "pe_idempotency_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_pe_idempotency_key_scope",
        "pe_idempotency_keys",
        ["idempotency_key", "scope"],
        unique=True,
    )
    op.create_index(
        "ix_pe_idempotency_keys_expires_at",
        "pe_idempotency_keys",
        ["expires_at"],
    )

    # ── pe_audit_events ──
    op.create_table(
        "pe_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column(
            "actor_type", sa.String(50), nullable=False, server_default="system"
        ),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_pe_audit_events_entity",
        "pe_audit_events",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_pe_audit_events_action",
        "pe_audit_events",
        ["action"],
    )
    op.create_index(
        "ix_pe_audit_events_actor",
        "pe_audit_events",
        ["actor_type", "actor_id"],
    )
    op.create_index(
        "ix_pe_audit_events_created_at",
        "pe_audit_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pe_audit_events_created_at", table_name="pe_audit_events")
    op.drop_index("ix_pe_audit_events_actor", table_name="pe_audit_events")
    op.drop_index("ix_pe_audit_events_action", table_name="pe_audit_events")
    op.drop_index("ix_pe_audit_events_entity", table_name="pe_audit_events")
    op.drop_table("pe_audit_events")

    op.drop_index("ix_pe_idempotency_keys_expires_at", table_name="pe_idempotency_keys")
    op.drop_index("uq_pe_idempotency_key_scope", table_name="pe_idempotency_keys")
    op.drop_table("pe_idempotency_keys")
