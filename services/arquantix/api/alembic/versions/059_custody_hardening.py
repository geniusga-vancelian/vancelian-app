"""custody hardening — webhook events, tx lifecycle, balance versioning

Revision ID: 059
Revises: 058
Create Date: 2026-03-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── custody_transactions: new columns ──────────────────────────────
    op.add_column(
        "custody_transactions",
        sa.Column(
            "provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_providers.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "custody_transactions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.func.now(),
        ),
        schema="public",
    )
    op.add_column(
        "custody_transactions",
        sa.Column("failure_reason", sa.Text, nullable=True),
        schema="public",
    )
    op.add_column(
        "custody_transactions",
        sa.Column(
            "reversal_of_transaction_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )

    # Backfill provider_id from custody_accounts
    op.execute(
        """
        UPDATE public.custody_transactions t
        SET provider_id = a.provider_id
        FROM public.custody_accounts a
        WHERE t.account_id = a.id
          AND t.provider_id IS NULL
        """
    )

    # Unique partial index: one transaction per (provider, external_reference)
    op.create_index(
        "uq_custody_tx_provider_extref",
        "custody_transactions",
        ["provider_id", "external_reference"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("external_reference IS NOT NULL"),
    )

    op.create_index(
        "ix_custody_transactions_provider_id",
        "custody_transactions",
        ["provider_id"],
        schema="public",
    )

    # ── custody_account_balances: version column ───────────────────────
    op.add_column(
        "custody_account_balances",
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        schema="public",
    )

    # ── custody_webhook_events (new table) ─────────────────────────────
    op.create_table(
        "custody_webhook_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_providers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("payload_raw", JSONB, nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(20),
            nullable=False,
            server_default="received",
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "linked_transaction_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.custody_transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", JSONB, nullable=False, server_default="{}"),
        schema="public",
    )
    op.create_index(
        "ix_custody_webhook_events_provider_ref",
        "custody_webhook_events",
        ["provider_id", "external_reference"],
        schema="public",
    )
    op.create_index(
        "ix_custody_webhook_events_status",
        "custody_webhook_events",
        ["processing_status"],
        schema="public",
    )
    op.create_index(
        "ix_custody_webhook_events_received",
        "custody_webhook_events",
        ["received_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_custody_webhook_events_received", table_name="custody_webhook_events", schema="public")
    op.drop_index("ix_custody_webhook_events_status", table_name="custody_webhook_events", schema="public")
    op.drop_index("ix_custody_webhook_events_provider_ref", table_name="custody_webhook_events", schema="public")
    op.drop_table("custody_webhook_events", schema="public")

    op.drop_column("custody_account_balances", "version", schema="public")

    op.drop_index("ix_custody_transactions_provider_id", table_name="custody_transactions", schema="public")
    op.drop_index("uq_custody_tx_provider_extref", table_name="custody_transactions", schema="public")
    op.drop_column("custody_transactions", "reversal_of_transaction_id", schema="public")
    op.drop_column("custody_transactions", "failure_reason", schema="public")
    op.drop_column("custody_transactions", "updated_at", schema="public")
    op.drop_column("custody_transactions", "provider_id", schema="public")
