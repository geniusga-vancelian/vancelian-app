"""add pe_product_definitions table (Portfolio Engine — catalog layer)

Revision ID: 032
Revises: 031
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_product_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("product_code", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("product_type", sa.String(50), nullable=False),
        sa.Column("risk_label", sa.String(30), nullable=True),
        sa.Column("base_currency", sa.String(20), nullable=False, server_default="EUR"),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("metadata", JSONB(astext_type=sa.Text), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_pe_product_definitions_product_code",
        "pe_product_definitions",
        ["product_code"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_pe_product_definitions_product_type",
        "pe_product_definitions",
        ["product_type"],
        schema="public",
    )
    op.create_index(
        "ix_pe_product_definitions_status",
        "pe_product_definitions",
        ["status"],
        schema="public",
    )
    op.create_index(
        "ix_pe_product_definitions_metadata",
        "pe_product_definitions",
        ["metadata"],
        postgresql_using="gin",
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_pe_product_definitions_metadata", table_name="pe_product_definitions", schema="public")
    op.drop_index("ix_pe_product_definitions_status", table_name="pe_product_definitions", schema="public")
    op.drop_index("ix_pe_product_definitions_product_type", table_name="pe_product_definitions", schema="public")
    op.drop_index("ix_pe_product_definitions_product_code", table_name="pe_product_definitions", schema="public")
    op.drop_table("pe_product_definitions", schema="public")
