"""B1 — transaction_intents bundle parent/child columns (additive, no runtime wiring)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "176"
down_revision = "175"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transaction_intents",
        sa.Column(
            "parent_intent_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("intent_role", sa.String(16), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column("leg_index", sa.Integer(), nullable=True),
        schema="public",
    )
    op.add_column(
        "transaction_intents",
        sa.Column(
            "bundle_execution_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="public",
    )
    op.create_foreign_key(
        "fk_transaction_intents_parent_intent_id",
        "transaction_intents",
        "transaction_intents",
        ["parent_intent_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_transaction_intents_parent_intent_id",
        "transaction_intents",
        ["parent_intent_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_transaction_intents_bundle_execution_id",
        "transaction_intents",
        ["bundle_execution_id"],
        unique=False,
        schema="public",
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_transaction_intents_parent_leg_index
            ON public.transaction_intents (parent_intent_id, leg_index)
            WHERE parent_intent_id IS NOT NULL AND leg_index IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DROP INDEX IF EXISTS public.uq_transaction_intents_parent_leg_index")
    )
    op.drop_index(
        "ix_transaction_intents_bundle_execution_id",
        table_name="transaction_intents",
        schema="public",
    )
    op.drop_index(
        "ix_transaction_intents_parent_intent_id",
        table_name="transaction_intents",
        schema="public",
    )
    op.drop_constraint(
        "fk_transaction_intents_parent_intent_id",
        "transaction_intents",
        schema="public",
        type_="foreignkey",
    )
    op.drop_column("transaction_intents", "bundle_execution_id", schema="public")
    op.drop_column("transaction_intents", "leg_index", schema="public")
    op.drop_column("transaction_intents", "intent_role", schema="public")
    op.drop_column("transaction_intents", "parent_intent_id", schema="public")
