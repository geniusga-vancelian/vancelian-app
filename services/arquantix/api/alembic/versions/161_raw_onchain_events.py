"""Raw on-chain events + squelette transaction_intents (réconciliation Phase 3)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "161"
down_revision = "160"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_onchain_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("tx_hash", sa.String(80), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contract_address", sa.String(80), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False, server_default="erc20_transfer"),
        sa.Column("wallet_address", sa.String(80), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("amount_raw", sa.Numeric(78, 0), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "parsed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_unique_constraint(
        "uq_raw_onchain_events_chain_tx_log",
        "raw_onchain_events",
        ["chain_id", "tx_hash", "log_index"],
        schema="public",
    )
    op.create_index(
        "ix_raw_onchain_events_wallet_chain",
        "raw_onchain_events",
        ["wallet_address", "chain_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_raw_onchain_events_tx_hash",
        "raw_onchain_events",
        ["tx_hash"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "transaction_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("product", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
    op.create_unique_constraint(
        "uq_transaction_intents_idempotency_key",
        "transaction_intents",
        ["idempotency_key"],
        schema="public",
    )
    op.create_index(
        "ix_transaction_intents_person_id",
        "transaction_intents",
        ["person_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("transaction_intents", schema="public")
    op.drop_table("raw_onchain_events", schema="public")
