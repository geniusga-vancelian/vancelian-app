"""PRD Conversational Action Layer — Phase 1 : persistance ``action_drafts``.

Table ``assistance_action_drafts`` : brouillons transactionnels préparés
par l''agent ``action`` (aucune exécution métier — cf.
``docs/arquantix/PRD_CONVERSATIONAL_ACTION_LAYER.md``).

Colonnes minimales :
  - liaison ``conversation_id`` + ``client_id`` (audit, filtre)
  - ``action_type`` (ex. ``crypto_buy``)
  - ``status`` (``draft``, futurs ``awaiting_confirmation``, …)
  - ``payload`` JSONB (montants estimés, disclaimers — recalcul serveur Phase 2+)

Additive only ; FK CASCADE vers ``assistance_conversations`` et ``pe_clients``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "154"
down_revision = "153"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistance_action_drafts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.assistance_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_assistance_action_drafts_conversation_id",
        "assistance_action_drafts",
        ["conversation_id"],
        schema="public",
    )
    op.create_index(
        "ix_assistance_action_drafts_client_created",
        "assistance_action_drafts",
        ["client_id", "created_at"],
        schema="public",
        postgresql_ops={"created_at": "DESC NULLS LAST"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistance_action_drafts_client_created",
        table_name="assistance_action_drafts",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_action_drafts_conversation_id",
        table_name="assistance_action_drafts",
        schema="public",
    )
    op.drop_table("assistance_action_drafts", schema="public")
