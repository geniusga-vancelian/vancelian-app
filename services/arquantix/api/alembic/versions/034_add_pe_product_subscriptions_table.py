"""add pe_product_subscriptions table (Portfolio Engine — product subscription layer)

Revision ID: 034
Revises: 033
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_product_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_product_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=True),
            sa.ForeignKey("public.pe_portfolios.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("subscription_amount", sa.Numeric(30, 10), nullable=True),
        sa.Column("subscription_currency", sa.String(20), nullable=False, server_default="EUR"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_pe_product_subscriptions_client_id",
        "pe_product_subscriptions",
        ["client_id"],
        schema="public",
    )
    op.create_index(
        "ix_pe_product_subscriptions_product_id",
        "pe_product_subscriptions",
        ["product_id"],
        schema="public",
    )
    op.create_index(
        "ix_pe_product_subscriptions_status",
        "pe_product_subscriptions",
        ["status"],
        schema="public",
    )
    op.create_index(
        "ix_pe_product_subscriptions_metadata",
        "pe_product_subscriptions",
        ["metadata"],
        postgresql_using="gin",
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_pe_product_subscriptions_metadata", table_name="pe_product_subscriptions", schema="public")
    op.drop_index("ix_pe_product_subscriptions_status", table_name="pe_product_subscriptions", schema="public")
    op.drop_index("ix_pe_product_subscriptions_product_id", table_name="pe_product_subscriptions", schema="public")
    op.drop_index("ix_pe_product_subscriptions_client_id", table_name="pe_product_subscriptions", schema="public")
    op.drop_table("pe_product_subscriptions", schema="public")
