"""W3/W4 — unique (intent_id, event_type) on transaction_outbox (race-safe enqueue)."""
from __future__ import annotations

from alembic import op

revision = "174"
down_revision = "173"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_outbox_intent_event_type",
        "transaction_outbox",
        ["intent_id", "event_type"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "uq_outbox_intent_event_type",
        table_name="transaction_outbox",
        schema="public",
    )
