"""Add exchange engine tables: crypto_positions, exchange_orders, crypto_settlement_deltas.

Revision ID: 061
Revises: 060
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crypto_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("balance", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("available_balance", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["public.pe_clients.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("client_id", "asset", name="uq_crypto_positions_client_asset"),
        schema="public",
    )
    op.create_index("ix_crypto_positions_client_id", "crypto_positions", ["client_id"], schema="public")

    op.create_table(
        "exchange_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("amount_crypto", sa.Numeric(30, 18), nullable=False),
        sa.Column("amount_fiat", sa.Numeric(30, 10), nullable=False),
        sa.Column("price", sa.Numeric(30, 10), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="EUR"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("external_reference", sa.String(255), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata_", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["client_id"], ["public.pe_clients.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("external_reference", name="uq_exchange_orders_ext_ref"),
        schema="public",
    )
    op.create_index("ix_exchange_orders_client_id", "exchange_orders", ["client_id"], schema="public")
    op.create_index("ix_exchange_orders_asset", "exchange_orders", ["asset"], schema="public")
    op.create_index("ix_exchange_orders_created_at", "exchange_orders", ["created_at"], schema="public")

    op.create_table(
        "crypto_settlement_deltas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("delta_amount", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("settled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset", "settlement_date", name="uq_crypto_settlement_delta_asset_date"),
        schema="public",
    )
    op.create_index("ix_crypto_settlement_deltas_date", "crypto_settlement_deltas", ["settlement_date"], schema="public")


def downgrade() -> None:
    op.drop_table("crypto_settlement_deltas", schema="public")
    op.drop_table("exchange_orders", schema="public")
    op.drop_table("crypto_positions", schema="public")
