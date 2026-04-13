"""Add price_alerts and notifications tables.

Revision ID: 069
Revises: 068
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "price_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id"), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("target_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("price_source", sa.String(10), nullable=False, server_default="mid"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("action_type", sa.String(20), nullable=False, server_default="alert"),
        sa.Column("order_payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_price", sa.Numeric(20, 8), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_price_alerts_client_asset_status",
        "price_alerts",
        ["client_id", "asset", "status"],
        schema="public",
    )

    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_notifications_client_read",
        "notifications",
        ["client_id", "is_read"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_client_read", table_name="notifications", schema="public")
    op.drop_table("notifications", schema="public")
    op.drop_index("ix_price_alerts_client_asset_status", table_name="price_alerts", schema="public")
    op.drop_table("price_alerts", schema="public")
