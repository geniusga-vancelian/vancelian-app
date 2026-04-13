"""Create client_favorites table.

Allows clients to bookmark instruments, exclusive offers and bundles.
Max 10 per entity_type enforced at API level.

Revision ID: 080
Revises: 079
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("pe_clients.id"), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("client_id", "entity_type", "entity_id", name="uq_client_favorites_client_entity"),
        schema="public",
    )
    op.create_index(
        "ix_client_favorites_client_type",
        "client_favorites",
        ["client_id", "entity_type"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_client_favorites_client_type", table_name="client_favorites", schema="public")
    op.drop_table("client_favorites", schema="public")
