"""Phase 1 multi-agents — colonnes agent / type / payload sur les messages.

Ajoute les colonnes nécessaires au système d'orchestration multi-agents
documenté dans `docs/arquantix/MULTI_AGENTS.md` (§ 1.3 et § 4.1).

──────────────────────────────────────────────────────────────────────
Colonnes ajoutées sur `assistance_messages` :

  - `agent_used        VARCHAR(32) NULL` :
      identifiant de l'agent qui a produit la réponse côté assistant
      (`default`, `compliance`, `advisor`, `product`, `market`,
      `router`). NULL pour les messages user et pour les anciens
      messages assistant antérieurs au multi-agents (rétrocompat).
      Une valeur connue côté code permet d'afficher un badge dans
      Flutter et de filtrer en SQL pour l'analytics
      (`WHERE agent_used = 'compliance'`).

  - `message_type      VARCHAR(16) NOT NULL DEFAULT 'text'` :
      discriminant du format du message. V1 supporte :
        - `'text'`    (défaut) — bulle Markdown classique.
        - `'choices'` — QCM poussé par le router quand il est indécis,
          ouvre des boutons cliquables côté Flutter (cf. § 1.9 du doc).
      Champ extensible vers d'autres types riches (`'card'`,
      `'simulation'`, …) sans nouvelle migration.

  - `message_payload   JSONB NULL` :
      données structurées associées au message quand
      `message_type != 'text'`. Pour `'choices'` :
          {
            "options": [
              {"id": "compliance", "label": "Mon compte / dépôts / transactions"},
              {"id": "freeform",   "label": "Rien de tout ça — je reformule"}
            ],
            "allow_freeform": true
          }
      `content` reste un fallback texte lisible (pour les clients
      legacy / les transcriptions / le summarizer).

──────────────────────────────────────────────────────────────────────
Index additionnel :

  - `ix_assistance_messages_agent_used` (B-tree partiel équivalent via
    SQL standard) pour les requêtes analytiques par agent. La
    cardinalité étant faible (~5 valeurs), ce simple B-tree est
    suffisant ; on évolue vers un index plus fin si besoin.

──────────────────────────────────────────────────────────────────────
Migration purement additive : aucune colonne supprimée, aucun renommage,
aucune contrainte FK touchée. Tous les messages existants sont
considérés comme `message_type='text'` (default) avec
`agent_used=NULL` (équivalent agent `default` côté code) et
`message_payload=NULL` — rétrocompatibles.

Revision ID: 147
Revises: 146
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "147"
down_revision = "146"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistance_messages",
        sa.Column(
            "agent_used",
            sa.String(length=32),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "assistance_messages",
        sa.Column(
            "message_type",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'text'"),
        ),
        schema="public",
    )
    op.add_column(
        "assistance_messages",
        sa.Column(
            "message_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="public",
    )
    op.create_index(
        "ix_assistance_messages_agent_used",
        "assistance_messages",
        ["agent_used"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistance_messages_agent_used",
        table_name="assistance_messages",
        schema="public",
    )
    op.drop_column(
        "assistance_messages",
        "message_payload",
        schema="public",
    )
    op.drop_column(
        "assistance_messages",
        "message_type",
        schema="public",
    )
    op.drop_column(
        "assistance_messages",
        "agent_used",
        schema="public",
    )
