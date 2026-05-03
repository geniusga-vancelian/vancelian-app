"""Palier 2 D.2 — Mémoire long-terme de l'assistance (résumé + faits).

Ajoute les colonnes nécessaires au mécanisme de « rolling summary » et
d'extraction de faits structurés cross-conversations (cf. plan
docs/arquantix/MEMORY.md, généré dans la même série de PR).

──────────────────────────────────────────────────────────────────────
1) `assistance_conversations` — mémoire **par conversation** (D.2.1 + D.2.2)

   - `conversation_summary    TEXT NULL` :
       résumé narratif 2-6 lignes maintenu par un agent LLM dédié, mis à
       jour de manière incrémentale (rolling summary) dès que le total
       tokens du contexte dépasse `ASSISTANCE_SUMMARY_THRESHOLD_TOKENS`
       (défaut 6_000). Sert à compresser les anciens tours pour ne pas
       gonfler le payload OpenAI sur les conversations longues, tout en
       conservant la mémoire.

   - `conversation_facts      JSONB NOT NULL DEFAULT '[]'` :
       liste de faits structurés extraits de la conversation au format
       `[{"type": "...", "value": ..., "confidence": 0..1, "source_turn": int}]`.
       Réinjecté dans le system prompt à chaque tour. Permet une mémoire
       sémantique (vs. narrative) actionnable par d'autres agents
       (orchestrateur futur).

   - `summarized_until_turn   INTEGER NULL` :
       index du dernier `turn_index` déjà absorbé par
       `conversation_summary`. Évite de re-compresser ce qui l'a déjà
       été : on ne passe au LLM que les nouveaux tours depuis cet index.
       Économie significative côté tokens d'input du summarizer.

   - `summary_updated_at      TIMESTAMPTZ NULL` :
       horodatage de la dernière consolidation. Diagnostic / debug.

──────────────────────────────────────────────────────────────────────
2) `pe_clients` — mémoire **cross-conversations** (D.2.3 niveau client)

   - `assistance_long_memory  JSONB NOT NULL DEFAULT '{}'` :
       agrégat des faits structurés issus de toutes les
       `assistance_conversations` d'un même client. Format :
           {
             "facts": [
               {"type": "...", "value": ...,
                "confidence": float,
                "source_conversation_id": uuid,
                "first_seen_at": "...",
                "last_seen_at": "..."},
               ...
             ],
             "updated_at": "..."
           }
       Fusion best-effort dédupliquée par `(type, value)` à chaque
       consolidation de conv. Sert à reconnaître un client connu dès le
       1er message d'une nouvelle conversation (continuité d'expérience).

──────────────────────────────────────────────────────────────────────
Migration purement additive : aucune colonne supprimée, aucun renommage,
aucune contrainte FK touchée. Les conversations et clients existants
resteront fonctionnels avec les valeurs par défaut (`[]`, `{}`, NULL) :
aucun backfill nécessaire — la consolidation s'amorcera naturellement
au prochain tour de chaque conversation active.

Revision ID: 146
Revises: 145
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "146"
down_revision = "145"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1) assistance_conversations — mémoire par conversation ────────
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "conversation_summary",
            sa.Text(),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "conversation_facts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema="public",
    )
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "summarized_until_turn",
            sa.Integer(),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "summary_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="public",
    )

    # ── 2) pe_clients — mémoire long-terme cross-conversations ────────
    op.add_column(
        "pe_clients",
        sa.Column(
            "assistance_long_memory",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column(
        "pe_clients",
        "assistance_long_memory",
        schema="public",
    )
    op.drop_column(
        "assistance_conversations",
        "summary_updated_at",
        schema="public",
    )
    op.drop_column(
        "assistance_conversations",
        "summarized_until_turn",
        schema="public",
    )
    op.drop_column(
        "assistance_conversations",
        "conversation_facts",
        schema="public",
    )
    op.drop_column(
        "assistance_conversations",
        "conversation_summary",
        schema="public",
    )
