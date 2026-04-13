"""add app_runtime_settings table

Revision ID: 057
Revises: 056
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_runtime_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("value", sa.String(500), nullable=True),
        sa.Column("metadata_", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="public",
    )
    op.create_index(
        "ix_app_runtime_settings_key",
        "app_runtime_settings",
        ["key"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_app_runtime_settings_key", table_name="app_runtime_settings", schema="public")
    op.drop_table("app_runtime_settings", schema="public")
