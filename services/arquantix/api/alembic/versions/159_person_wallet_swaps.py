"""Person wallet swaps — sessions LI.FI orchestrées par Vancelian."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "159"
down_revision = "158"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_wallet_swaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("from_asset", sa.String(20), nullable=False),
        sa.Column("to_asset", sa.String(20), nullable=False),
        sa.Column("from_chain", sa.String(32), nullable=False),
        sa.Column("to_chain", sa.String(32), nullable=False),
        sa.Column("amount_in", sa.Numeric(30, 18), nullable=False),
        sa.Column("vancelian_fee", sa.Numeric(30, 18), nullable=True),
        sa.Column("vancelian_fee_bps", sa.Integer(), nullable=True),
        sa.Column("network_fee", sa.Numeric(30, 18), nullable=True),
        sa.Column("network_fee_asset", sa.String(20), nullable=True),
        sa.Column("estimated_receive", sa.Numeric(30, 18), nullable=True),
        sa.Column("estimated_receive_min", sa.Numeric(30, 18), nullable=True),
        sa.Column("slippage_bps", sa.Integer(), nullable=True),
        sa.Column("lifi_quote_id", sa.String(120), nullable=True),
        sa.Column("lifi_tool", sa.String(80), nullable=True),
        sa.Column("lifi_quote_raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("transaction_request", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("route_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tx_hash", sa.String(120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("audit_log", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index("ix_person_wallet_swaps_person_id", "person_wallet_swaps", ["person_id"], schema="public")
    op.create_index("ix_person_wallet_swaps_status", "person_wallet_swaps", ["status"], schema="public")
    op.create_index("ix_person_wallet_swaps_created_at", "person_wallet_swaps", ["created_at"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_person_wallet_swaps_created_at", table_name="person_wallet_swaps", schema="public")
    op.drop_index("ix_person_wallet_swaps_status", table_name="person_wallet_swaps", schema="public")
    op.drop_index("ix_person_wallet_swaps_person_id", table_name="person_wallet_swaps", schema="public")
    op.drop_table("person_wallet_swaps", schema="public")
