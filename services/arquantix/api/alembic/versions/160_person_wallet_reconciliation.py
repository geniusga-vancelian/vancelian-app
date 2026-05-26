"""Tables réconciliation ledger Privy ↔ on-chain."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "160"
down_revision = "159"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_wallet_reconciliation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scope", sa.String(20), server_default="person", nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("status", sa.String(40), server_default="running", nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_checked", sa.Integer(), server_default="0", nullable=False),
        sa.Column("matched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("healed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("chain_ahead_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ledger_ahead_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("mismatch_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unresolved_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("replayed_webhooks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_reconciliation_runs_person_id",
        "person_wallet_reconciliation_runs",
        ["person_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_reconciliation_runs_started_at",
        "person_wallet_reconciliation_runs",
        ["started_at"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "person_wallet_reconciliation_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.person_wallet_reconciliation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("wallet_address", sa.String(80), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("chain_label", sa.String(80), nullable=True),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("ledger_balance", sa.Numeric(30, 18), server_default="0", nullable=False),
        sa.Column("on_chain_balance", sa.Numeric(30, 18), server_default="0", nullable=False),
        sa.Column("delta", sa.Numeric(30, 18), server_default="0", nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("action_taken", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_reconciliation_items_run_id",
        "person_wallet_reconciliation_items",
        ["run_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_person_wallet_reconciliation_items_person_id",
        "person_wallet_reconciliation_items",
        ["person_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_person_wallet_reconciliation_items_person_id",
        table_name="person_wallet_reconciliation_items",
        schema="public",
    )
    op.drop_index(
        "ix_person_wallet_reconciliation_items_run_id",
        table_name="person_wallet_reconciliation_items",
        schema="public",
    )
    op.drop_table("person_wallet_reconciliation_items", schema="public")
    op.drop_index(
        "ix_person_wallet_reconciliation_runs_started_at",
        table_name="person_wallet_reconciliation_runs",
        schema="public",
    )
    op.drop_index(
        "ix_person_wallet_reconciliation_runs_person_id",
        table_name="person_wallet_reconciliation_runs",
        schema="public",
    )
    op.drop_table("person_wallet_reconciliation_runs", schema="public")
