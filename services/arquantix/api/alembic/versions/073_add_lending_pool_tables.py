"""Add pool-based lending tables.

Revision ID: 073
Revises: 072
Create Date: 2026-03-21

Phase 2A.6bis: Pool-based P2P Lending (Soft Pool / Commitment Model).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "073"
down_revision = "072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lending_pools",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("asset", sa.String(20), unique=True, nullable=False),
        sa.Column("total_committed", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("total_borrowed", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("utilization_rate", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )

    op.create_table(
        "pool_supply_commitments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pool_id", UUID(as_uuid=True), sa.ForeignKey("lending_pools.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("reserved_amount", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("available_amount", sa.Numeric(30, 10), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pool_supply_commitments_pool_id", "pool_supply_commitments", ["pool_id"], schema="public")
    op.create_index("ix_pool_supply_commitments_client_id", "pool_supply_commitments", ["client_id"], schema="public")
    op.create_index("ix_pool_supply_commitments_status", "pool_supply_commitments", ["status"], schema="public")

    op.create_table(
        "pool_borrow_positions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pool_id", UUID(as_uuid=True), sa.ForeignKey("lending_pools.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("borrowed_amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("borrowing_position_atom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pool_borrow_positions_pool_id", "pool_borrow_positions", ["pool_id"], schema="public")
    op.create_index("ix_pool_borrow_positions_client_id", "pool_borrow_positions", ["client_id"], schema="public")
    op.create_index("ix_pool_borrow_positions_status", "pool_borrow_positions", ["status"], schema="public")

    op.create_table(
        "pool_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("supply_commitment_id", UUID(as_uuid=True), sa.ForeignKey("pool_supply_commitments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("borrow_position_id", UUID(as_uuid=True), sa.ForeignKey("pool_borrow_positions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("lending_position_atom_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pool_allocations_supply_id", "pool_allocations", ["supply_commitment_id"], schema="public")
    op.create_index("ix_pool_allocations_borrow_id", "pool_allocations", ["borrow_position_id"], schema="public")


def downgrade() -> None:
    op.drop_table("pool_allocations", schema="public")
    op.drop_table("pool_borrow_positions", schema="public")
    op.drop_table("pool_supply_commitments", schema="public")
    op.drop_table("lending_pools", schema="public")
