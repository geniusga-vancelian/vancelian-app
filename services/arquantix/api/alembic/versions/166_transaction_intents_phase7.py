"""Phase 7 — transaction_intents branchés aux flux DeFi."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "166"
down_revision = "165"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "transaction_intents",
        "product",
        new_column_name="product_type",
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("wallet_address", sa.String(80), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("chain_id", sa.Integer(), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("operation_type", sa.String(32), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("tx_hash", sa.String(80), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column(
            "raw_onchain_event_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("linked_table", sa.String(64), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("linked_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="public",
    )

    op.execute(
        sa.text(
            "UPDATE public.transaction_intents "
            "SET operation_type = 'swap', product_type = COALESCE(product_type, 'legacy') "
            "WHERE operation_type IS NULL"
        )
    )

    op.alter_column(
        "transaction_intents",
        "operation_type",
        nullable=False,
        server_default="swap",
        schema="public",
    )
    op.alter_column(
        "transaction_intents",
        "status",
        server_default="created",
        schema="public",
    )

    op.drop_constraint(
        "uq_transaction_intents_idempotency_key",
        "transaction_intents",
        schema="public",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_transaction_intents_person_product_op_key",
        "transaction_intents",
        ["person_id", "product_type", "operation_type", "idempotency_key"],
        schema="public",
    )
    op.create_index(
        "ix_transaction_intents_tx_hash",
        "transaction_intents",
        ["tx_hash"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_transaction_intents_linked",
        "transaction_intents",
        ["linked_table", "linked_id"],
        unique=False,
        schema="public",
    )
    op.create_foreign_key(
        "fk_transaction_intents_raw_onchain_event",
        "transaction_intents",
        "raw_onchain_events",
        ["raw_onchain_event_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transaction_intents_raw_onchain_event",
        "transaction_intents",
        schema="public",
        type_="foreignkey",
    )
    op.drop_index("ix_transaction_intents_linked", table_name="transaction_intents", schema="public")
    op.drop_index("ix_transaction_intents_tx_hash", table_name="transaction_intents", schema="public")
    op.drop_constraint(
        "uq_transaction_intents_person_product_op_key",
        "transaction_intents",
        schema="public",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_transaction_intents_idempotency_key",
        "transaction_intents",
        ["idempotency_key"],
        schema="public",
    )
    for col in (
        "linked_id",
        "linked_table",
        "raw_onchain_event_id",
        "tx_hash",
        "operation_type",
        "chain_id",
        "wallet_address",
    ):
        op.drop_column("transaction_intents", col, schema="public")
    op.alter_column(
        "transaction_intents",
        "product_type",
        new_column_name="product",
        schema="public",
    )
