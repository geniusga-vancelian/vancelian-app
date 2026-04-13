"""Add swap_group_id to exchange_orders for crypto↔crypto swap linking.

Revision ID: 068
Revises: 067
Create Date: 2026-03-19

Links SELL and BUY legs of a swap with a common UUID.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exchange_orders",
        sa.Column("swap_group_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_exchange_orders_swap_group_id",
        "exchange_orders",
        ["swap_group_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_exchange_orders_swap_group_id",
        table_name="exchange_orders",
        schema="public",
    )
    op.drop_column("exchange_orders", "swap_group_id", schema="public")
