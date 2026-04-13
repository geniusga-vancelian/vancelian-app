"""add pe_clients table (Portfolio Engine — ownership layer)

Revision ID: 031
Revises: 030
Create Date: 2026-02-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("kyc_status", sa.String(30), nullable=False, server_default="not_started"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index("ix_pe_clients_email", "pe_clients", ["email"], unique=True, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_clients_email", table_name="pe_clients", schema="public")
    op.drop_table("pe_clients", schema="public")
