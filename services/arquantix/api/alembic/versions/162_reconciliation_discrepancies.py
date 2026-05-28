"""Tables anomalies et audit corrections (réconciliation Phase 4)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "162"
down_revision = "161"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reconciliation_discrepancies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("wallet_address", sa.String(80), nullable=True),
        sa.Column("layer", sa.String(32), nullable=False),
        sa.Column("asset", sa.String(20), nullable=True),
        sa.Column("discrepancy_type", sa.String(64), nullable=False),
        sa.Column("db_amount", sa.Numeric(30, 18), nullable=True),
        sa.Column("onchain_amount", sa.Numeric(30, 18), nullable=True),
        sa.Column("delta", sa.Numeric(30, 18), nullable=True),
        sa.Column("severity", sa.String(10), server_default="P2", nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("reference_type", sa.String(40), nullable=True),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_unique_constraint(
        "uq_reconciliation_discrepancies_fingerprint",
        "reconciliation_discrepancies",
        ["fingerprint"],
        schema="public",
    )
    op.create_index(
        "ix_reconciliation_discrepancies_person_status",
        "reconciliation_discrepancies",
        ["person_id", "status"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_reconciliation_discrepancies_layer",
        "reconciliation_discrepancies",
        ["layer"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "reconciliation_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "discrepancy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.reconciliation_discrepancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("dry_run", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_reconciliation_corrections_discrepancy_id",
        "reconciliation_corrections",
        ["discrepancy_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("reconciliation_corrections", schema="public")
    op.drop_table("reconciliation_discrepancies", schema="public")
