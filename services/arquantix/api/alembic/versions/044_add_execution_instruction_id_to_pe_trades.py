"""add execution_instruction_id to pe_trades

Revision ID: 044
Revises: 043
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pe_trades",
        sa.Column("execution_instruction_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_pe_trades_execution_instruction_id",
        "pe_trades",
        "pe_execution_instructions",
        ["execution_instruction_id"],
        ["id"],
        ondelete="SET NULL",
        source_schema="public",
        referent_schema="public",
    )
    op.create_index(
        "ix_pe_trades_execution_instruction_id",
        "pe_trades",
        ["execution_instruction_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_pe_trades_execution_instruction_id", table_name="pe_trades", schema="public")
    op.drop_constraint("fk_pe_trades_execution_instruction_id", "pe_trades", schema="public", type_="foreignkey")
    op.drop_column("pe_trades", "execution_instruction_id", schema="public")
