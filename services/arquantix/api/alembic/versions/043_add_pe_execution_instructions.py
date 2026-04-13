"""add pe_execution_instructions table

Revision ID: 043
Revises: 042
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "043"
down_revision = "042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_execution_instructions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parent_execution_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_execution_instructions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("venue", sa.String(100), nullable=False),
        sa.Column("execution_type", sa.String(50), nullable=False),
        sa.Column("instrument_id", UUID(as_uuid=True), sa.ForeignKey("public.pe_instruments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("side", sa.String(10), nullable=True),
        sa.Column("quantity", sa.Numeric(30, 10), nullable=True),
        sa.Column("amount", sa.Numeric(30, 10), nullable=True),
        sa.Column("price_limit", sa.Numeric(30, 10), nullable=True),
        sa.Column("currency", sa.String(20), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("venue_order_id", sa.String(255), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(30, 10), nullable=True, server_default="0"),
        sa.Column("average_fill_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column("response_payload", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_exec_order_id", "pe_execution_instructions", ["order_id"], schema="public")
    op.create_index("ix_pe_exec_parent_id", "pe_execution_instructions", ["parent_execution_id"], schema="public")
    op.create_index("ix_pe_exec_venue", "pe_execution_instructions", ["venue"], schema="public")
    op.create_index("ix_pe_exec_instrument_id", "pe_execution_instructions", ["instrument_id"], schema="public")
    op.create_index("ix_pe_exec_status", "pe_execution_instructions", ["status"], schema="public")
    op.create_index("ix_pe_exec_venue_order_id", "pe_execution_instructions", ["venue_order_id"], schema="public")
    op.create_index("ix_pe_exec_requested_at", "pe_execution_instructions", ["requested_at"], schema="public")
    op.create_index("ix_pe_exec_created_at", "pe_execution_instructions", ["created_at"], schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_exec_created_at", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_requested_at", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_venue_order_id", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_status", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_instrument_id", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_venue", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_parent_id", table_name="pe_execution_instructions", schema="public")
    op.drop_index("ix_pe_exec_order_id", table_name="pe_execution_instructions", schema="public")
    op.drop_table("pe_execution_instructions", schema="public")
