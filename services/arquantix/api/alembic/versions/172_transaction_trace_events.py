"""Phase 2 — table transaction_trace_events (observabilité append-only)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "172"
down_revision = "171"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transaction_trace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.transaction_intents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.onchain_transaction_attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("group_key", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("protocol", sa.String(32), nullable=True),
        sa.Column("operation_type", sa.String(32), nullable=True),
        sa.Column("step_type", sa.String(32), nullable=True),
        sa.Column("status_from", sa.String(32), nullable=True),
        sa.Column("status_to", sa.String(32), nullable=True),
        sa.Column("tx_hash", sa.String(80), nullable=True),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("linked_table", sa.String(64), nullable=True),
        sa.Column("linked_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_reference_id", sa.String(80), nullable=True),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index(
        "ix_trace_events_person_created",
        "transaction_trace_events",
        ["person_id", "created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_trace_events_attempt_id",
        "transaction_trace_events",
        ["attempt_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_trace_events_intent_id",
        "transaction_trace_events",
        ["intent_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_trace_events_event_type",
        "transaction_trace_events",
        ["event_type", "created_at"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_trace_events_event_type", table_name="transaction_trace_events", schema="public")
    op.drop_index("ix_trace_events_intent_id", table_name="transaction_trace_events", schema="public")
    op.drop_index("ix_trace_events_attempt_id", table_name="transaction_trace_events", schema="public")
    op.drop_index("ix_trace_events_person_created", table_name="transaction_trace_events", schema="public")
    op.drop_table("transaction_trace_events", schema="public")
