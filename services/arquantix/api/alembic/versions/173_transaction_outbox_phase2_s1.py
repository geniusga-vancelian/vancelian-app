"""Phase 2 S1 — transaction_outbox, transaction_intent_transitions, intent extensions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "173"
down_revision = "172"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- transaction_intents extensions (non-breaking) ---
    op.add_column(
        "transaction_intents",
        sa.Column(
            "correlation_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("current_phase", sa.String(64), server_default="created", nullable=False),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("requested_action", sa.String(32), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("assets_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column(
            "reconciliation_report_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column(
            "blocked_assets_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="public",
    )
    op.create_index(
        "ix_transaction_intents_correlation_id",
        "transaction_intents",
        ["correlation_id"],
        unique=False,
        schema="public",
    )

    # --- transaction_intent_transitions ---
    op.create_table(
        "transaction_intent_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(64), nullable=True),
        sa.Column("actor", sa.String(64), nullable=False, server_default="system"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_index(
        "ix_intent_transitions_intent_created",
        "transaction_intent_transitions",
        ["intent_id", "created_at"],
        unique=False,
        schema="public",
    )

    # --- transaction_outbox ---
    op.create_table(
        "transaction_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "next_retry_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_outbox_intent_created",
        "transaction_outbox",
        ["intent_id", "created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_outbox_poll",
        "transaction_outbox",
        ["status", "next_retry_at"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("status IN ('pending', 'processing')"),
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_poll", table_name="transaction_outbox", schema="public")
    op.drop_index("ix_outbox_intent_created", table_name="transaction_outbox", schema="public")
    op.drop_table("transaction_outbox", schema="public")

    op.drop_index(
        "ix_intent_transitions_intent_created",
        table_name="transaction_intent_transitions",
        schema="public",
    )
    op.drop_table("transaction_intent_transitions", schema="public")

    op.drop_index(
        "ix_transaction_intents_correlation_id",
        table_name="transaction_intents",
        schema="public",
    )
    op.drop_column("transaction_intents", "blocked_assets_json", schema="public")
    op.drop_column("transaction_intents", "reconciliation_report_json", schema="public")
    op.drop_column("transaction_intents", "expires_at", schema="public")
    op.drop_column("transaction_intents", "assets_json", schema="public")
    op.drop_column("transaction_intents", "requested_action", schema="public")
    op.drop_column("transaction_intents", "current_phase", schema="public")
    op.drop_column("transaction_intents", "correlation_id", schema="public")
