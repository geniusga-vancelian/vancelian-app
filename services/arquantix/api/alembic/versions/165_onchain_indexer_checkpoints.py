"""Phase 6 — checkpoints indexer continu Base."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "165"
down_revision = "164"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onchain_indexer_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("indexer_name", sa.String(64), nullable=False),
        sa.Column("last_scanned_block", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="idle"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="public",
    )
    op.create_unique_constraint(
        "uq_onchain_indexer_checkpoints_chain_indexer",
        "onchain_indexer_checkpoints",
        ["chain_id", "indexer_name"],
        schema="public",
    )
    op.create_index(
        "ix_onchain_indexer_checkpoints_chain_id",
        "onchain_indexer_checkpoints",
        ["chain_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_onchain_indexer_checkpoints_chain_id",
        table_name="onchain_indexer_checkpoints",
        schema="public",
    )
    op.drop_constraint(
        "uq_onchain_indexer_checkpoints_chain_indexer",
        "onchain_indexer_checkpoints",
        schema="public",
        type_="unique",
    )
    op.drop_table("onchain_indexer_checkpoints", schema="public")
