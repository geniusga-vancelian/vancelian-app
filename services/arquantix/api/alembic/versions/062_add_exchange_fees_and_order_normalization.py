"""Add exchange_fee_config table and normalize exchange_orders.

Revision ID: 062
Revises: 061
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchange_fee_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("fee_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset", name="uq_exchange_fee_config_asset"),
        schema="public",
    )

    op.add_column("exchange_orders", sa.Column("from_asset", sa.String(20), nullable=True), schema="public")
    op.add_column("exchange_orders", sa.Column("to_asset", sa.String(20), nullable=True), schema="public")
    op.add_column("exchange_orders", sa.Column("amount_from", sa.Numeric(30, 10), nullable=True), schema="public")
    op.add_column("exchange_orders", sa.Column("amount_to", sa.Numeric(30, 18), nullable=True), schema="public")
    op.add_column("exchange_orders", sa.Column("fee_amount", sa.Numeric(30, 18), nullable=True), schema="public")
    op.add_column("exchange_orders", sa.Column("fee_asset", sa.String(20), nullable=True), schema="public")


def downgrade() -> None:
    op.drop_column("exchange_orders", "fee_asset", schema="public")
    op.drop_column("exchange_orders", "fee_amount", schema="public")
    op.drop_column("exchange_orders", "amount_to", schema="public")
    op.drop_column("exchange_orders", "amount_from", schema="public")
    op.drop_column("exchange_orders", "to_asset", schema="public")
    op.drop_column("exchange_orders", "from_asset", schema="public")
    op.drop_table("exchange_fee_config", schema="public")
