"""Ledger wallet Privy — dépôts on-chain, soldes, webhooks (révision 158).

Tables :
- ``privy_webhook_events`` — ingestion Svix / Privy
- ``person_wallet_deposits`` — mouvements entrants (ledger utilisateur)
- ``person_wallet_balances`` — soldes par wallet + asset
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "158"
down_revision = "157"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "privy_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("svix_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("payload_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(20),
            server_default="received",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_privy_webhook_events_status",
        "privy_webhook_events",
        ["processing_status"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_privy_webhook_events_received",
        "privy_webhook_events",
        ["received_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_privy_webhook_events_event_type",
        "privy_webhook_events",
        ["event_type"],
        unique=False,
        schema="public",
    )
    op.create_unique_constraint(
        "uq_privy_webhook_events_svix_id",
        "privy_webhook_events",
        ["svix_id"],
        schema="public",
    )
    op.create_unique_constraint(
        "uq_privy_webhook_events_idempotency_key",
        "privy_webhook_events",
        ["idempotency_key"],
        schema="public",
    )

    op.create_table(
        "person_wallet_deposits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_crypto_wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.person_crypto_wallets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pe_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "privy_webhook_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.privy_webhook_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "transaction_kind",
            sa.String(40),
            server_default="privy_deposit_in",
            nullable=False,
        ),
        sa.Column("direction", sa.String(10), server_default="credit", nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(30, 18), nullable=False),
        sa.Column("chain_type", sa.String(20), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("tx_hash", sa.String(80), nullable=False),
        sa.Column("log_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=True),
        sa.Column("from_address", sa.String(80), nullable=True),
        sa.Column("to_address", sa.String(80), nullable=False),
        sa.Column("confirmations", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="confirmed", nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("subtitle", sa.String(255), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_deposits_person_id",
        "person_wallet_deposits",
        ["person_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_deposits_wallet_id",
        "person_wallet_deposits",
        ["person_crypto_wallet_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_deposits_asset",
        "person_wallet_deposits",
        ["asset"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_deposits_created_at",
        "person_wallet_deposits",
        ["created_at"],
        unique=False,
        schema="public",
    )
    op.create_unique_constraint(
        "uq_person_wallet_deposits_chain_tx_log",
        "person_wallet_deposits",
        ["chain_id", "tx_hash", "log_index"],
        schema="public",
    )
    op.create_unique_constraint(
        "uq_person_wallet_deposits_idempotency_key",
        "person_wallet_deposits",
        ["idempotency_key"],
        schema="public",
    )

    op.create_table(
        "person_wallet_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_crypto_wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.person_crypto_wallets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("balance", sa.Numeric(30, 18), server_default="0", nullable=False),
        sa.Column(
            "available_balance",
            sa.Numeric(30, 18),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "sync_source",
            sa.String(40),
            server_default="privy_webhook",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_balances_person_id",
        "person_wallet_balances",
        ["person_id"],
        unique=False,
        schema="public",
    )
    op.create_unique_constraint(
        "uq_person_wallet_balances_wallet_asset",
        "person_wallet_balances",
        ["person_crypto_wallet_id", "asset"],
        schema="public",
    )

    op.add_column(
        "privy_webhook_events",
        sa.Column(
            "linked_deposit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.person_wallet_deposits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("privy_webhook_events", "linked_deposit_id", schema="public")

    op.drop_constraint(
        "uq_person_wallet_balances_wallet_asset",
        "person_wallet_balances",
        schema="public",
        type_="unique",
    )
    op.drop_index(
        "ix_person_wallet_balances_person_id",
        table_name="person_wallet_balances",
        schema="public",
    )
    op.drop_table("person_wallet_balances", schema="public")

    op.drop_constraint(
        "uq_person_wallet_deposits_idempotency_key",
        "person_wallet_deposits",
        schema="public",
        type_="unique",
    )
    op.drop_constraint(
        "uq_person_wallet_deposits_chain_tx_log",
        "person_wallet_deposits",
        schema="public",
        type_="unique",
    )
    op.drop_index(
        "ix_person_wallet_deposits_created_at",
        table_name="person_wallet_deposits",
        schema="public",
    )
    op.drop_index(
        "ix_person_wallet_deposits_asset",
        table_name="person_wallet_deposits",
        schema="public",
    )
    op.drop_index(
        "ix_person_wallet_deposits_wallet_id",
        table_name="person_wallet_deposits",
        schema="public",
    )
    op.drop_index(
        "ix_person_wallet_deposits_person_id",
        table_name="person_wallet_deposits",
        schema="public",
    )
    op.drop_table("person_wallet_deposits", schema="public")

    op.drop_constraint(
        "uq_privy_webhook_events_idempotency_key",
        "privy_webhook_events",
        schema="public",
        type_="unique",
    )
    op.drop_constraint(
        "uq_privy_webhook_events_svix_id",
        "privy_webhook_events",
        schema="public",
        type_="unique",
    )
    op.drop_index(
        "ix_privy_webhook_events_event_type",
        table_name="privy_webhook_events",
        schema="public",
    )
    op.drop_index(
        "ix_privy_webhook_events_received",
        table_name="privy_webhook_events",
        schema="public",
    )
    op.drop_index(
        "ix_privy_webhook_events_status",
        table_name="privy_webhook_events",
        schema="public",
    )
    op.drop_table("privy_webhook_events", schema="public")
