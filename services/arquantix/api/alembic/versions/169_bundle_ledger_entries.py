"""Phase 4A — journal bundle append-only (shadow mode).

Table ``bundle_ledger_entries`` — audit trail structuré miroir des flux PE/Li.FI.
Les atoms PE restent la source de vérité comptable court terme.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "169"
down_revision = "168"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bundle_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("asset_symbol", sa.String(32), nullable=False),
        sa.Column("asset_instrument_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(30, 10), nullable=False),
        sa.Column("amount_usd", sa.Numeric(30, 10), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("source_system", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("batch_id", sa.String(255), nullable=True),
        sa.Column("leg_id", sa.String(255), nullable=True),
        sa.Column("transaction_intent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), server_default="confirmed", nullable=False),
        sa.Column("idempotency_key", sa.String(512), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_bundle_ledger_entries_idempotency_key"),
        schema="public",
    )
    op.create_index(
        "ix_bundle_ledger_entries_portfolio_created",
        "bundle_ledger_entries",
        ["bundle_portfolio_id", "created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_bundle_ledger_entries_person_created",
        "bundle_ledger_entries",
        ["person_id", "created_at"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_bundle_ledger_entries_batch_id",
        "bundle_ledger_entries",
        ["batch_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_bundle_ledger_entries_event_type",
        "bundle_ledger_entries",
        ["event_type"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_bundle_ledger_entries_event_type",
        table_name="bundle_ledger_entries",
        schema="public",
    )
    op.drop_index(
        "ix_bundle_ledger_entries_batch_id",
        table_name="bundle_ledger_entries",
        schema="public",
    )
    op.drop_index(
        "ix_bundle_ledger_entries_person_created",
        table_name="bundle_ledger_entries",
        schema="public",
    )
    op.drop_index(
        "ix_bundle_ledger_entries_portfolio_created",
        table_name="bundle_ledger_entries",
        schema="public",
    )
    op.drop_table("bundle_ledger_entries", schema="public")
