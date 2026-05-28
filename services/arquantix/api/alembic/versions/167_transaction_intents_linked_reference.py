"""Phase 7B — linked_reference_id pour OnchainVaultTransaction (cuid)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "167"
down_revision = "166"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transaction_intents",
        sa.Column("linked_reference_id", sa.String(80), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_transaction_intents_linked_reference",
        "transaction_intents",
        ["linked_table", "linked_reference_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_transaction_intents_linked_reference",
        table_name="transaction_intents",
        schema="public",
    )
    op.drop_column("transaction_intents", "linked_reference_id", schema="public")
