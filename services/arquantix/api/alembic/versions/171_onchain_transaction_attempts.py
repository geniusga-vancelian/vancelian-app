"""Phase 2 — table onchain_transaction_attempts (dual-write, legacy inchangé)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "171"
down_revision = "170"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onchain_transaction_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.transaction_intents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "parent_intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.transaction_intents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_crypto_wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.person_crypto_wallets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(32), nullable=False),
        sa.Column("operation_type", sa.String(32), nullable=False),
        sa.Column("step_type", sa.String(32), nullable=False),
        sa.Column("step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("group_key", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="prepared"),
        sa.Column("tx_hash", sa.String(80), nullable=True),
        sa.Column("nonce", sa.BigInteger(), nullable=True),
        sa.Column("from_address", sa.String(80), nullable=True),
        sa.Column("to_address", sa.String(80), nullable=True),
        sa.Column("log_index", sa.Integer(), nullable=True),
        sa.Column("asset_in", sa.String(32), nullable=True),
        sa.Column("asset_out", sa.String(32), nullable=True),
        sa.Column("amount_in", sa.Numeric(30, 18), nullable=True),
        sa.Column("amount_out_expected", sa.Numeric(30, 18), nullable=True),
        sa.Column("amount_out_actual", sa.Numeric(30, 18), nullable=True),
        sa.Column("block_number", sa.BigInteger(), nullable=True),
        sa.Column("block_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gas_used", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_request_json", postgresql.JSONB(), nullable=True),
        sa.Column("raw_signed_payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("raw_submission_json", postgresql.JSONB(), nullable=True),
        sa.Column("raw_receipt_json", postgresql.JSONB(), nullable=True),
        sa.Column("raw_revert_json", postgresql.JSONB(), nullable=True),
        sa.Column("linked_table", sa.String(64), nullable=True),
        sa.Column("linked_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_reference_id", sa.String(80), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            "step_type",
            name="uq_onchain_transaction_attempts_idempotency_step",
        ),
        schema="public",
    )
    op.create_index(
        "ix_attempts_person_created",
        "onchain_transaction_attempts",
        ["person_id", "created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_attempts_intent_id",
        "onchain_transaction_attempts",
        ["intent_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_attempts_group_key",
        "onchain_transaction_attempts",
        ["group_key"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_attempts_status",
        "onchain_transaction_attempts",
        ["status"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_attempts_protocol_chain",
        "onchain_transaction_attempts",
        ["protocol", "chain_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_attempts_tx_hash",
        "onchain_transaction_attempts",
        ["tx_hash"],
        unique=False,
        schema="public",
        postgresql_where=sa.text("tx_hash IS NOT NULL"),
    )
    op.create_index(
        "uq_attempts_chain_tx_hash",
        "onchain_transaction_attempts",
        ["chain_id", "tx_hash"],
        unique=True,
        schema="public",
        postgresql_where=sa.text("tx_hash IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_attempts_chain_tx_hash",
        table_name="onchain_transaction_attempts",
        schema="public",
        postgresql_where=sa.text("tx_hash IS NOT NULL"),
    )
    op.drop_index(
        "ix_attempts_tx_hash",
        table_name="onchain_transaction_attempts",
        schema="public",
        postgresql_where=sa.text("tx_hash IS NOT NULL"),
    )
    op.drop_index("ix_attempts_protocol_chain", table_name="onchain_transaction_attempts", schema="public")
    op.drop_index("ix_attempts_status", table_name="onchain_transaction_attempts", schema="public")
    op.drop_index("ix_attempts_group_key", table_name="onchain_transaction_attempts", schema="public")
    op.drop_index("ix_attempts_intent_id", table_name="onchain_transaction_attempts", schema="public")
    op.drop_index("ix_attempts_person_created", table_name="onchain_transaction_attempts", schema="public")
    op.drop_table("onchain_transaction_attempts", schema="public")
