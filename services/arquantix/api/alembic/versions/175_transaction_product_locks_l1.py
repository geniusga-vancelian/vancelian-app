"""S4 L1 — transaction_product_locks (pessimistic product/asset scope locks)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "175"
down_revision = "174"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transaction_product_locks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "wallet_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.person_crypto_wallets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("product_type", sa.String(40), nullable=False),
        sa.Column(
            "intent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.transaction_intents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("lock_key", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_product_locks_intent_id",
        "transaction_product_locks",
        ["intent_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_product_locks_person_wallet_asset",
        "transaction_product_locks",
        ["person_id", "wallet_id", "asset"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_product_locks_expires_at",
        "transaction_product_locks",
        ["expires_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_product_locks_lock_key",
        "transaction_product_locks",
        ["lock_key"],
        unique=False,
        schema="public",
    )
    # One active lock per (person, wallet, asset, scope).
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_product_locks_active_scope
            ON public.transaction_product_locks (person_id, wallet_id, asset, scope)
            WHERE status = 'active' AND released_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS public.uq_product_locks_active_scope"))
    op.drop_index("ix_product_locks_lock_key", table_name="transaction_product_locks", schema="public")
    op.drop_index("ix_product_locks_expires_at", table_name="transaction_product_locks", schema="public")
    op.drop_index(
        "ix_product_locks_person_wallet_asset",
        table_name="transaction_product_locks",
        schema="public",
    )
    op.drop_index("ix_product_locks_intent_id", table_name="transaction_product_locks", schema="public")
    op.drop_table("transaction_product_locks", schema="public")
