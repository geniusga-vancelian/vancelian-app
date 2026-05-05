"""Cognitive Bot v4 — Lot 6 — colonnes dédiées cognitives sur ``assistance_agent_decisions``.

Cette migration ajoute **6 colonnes nullable** dénormalisées qui
matérialisent l'état cognitif (Lots 1+2 du Cognitive Bot v4) en
colonnes natives de la table d'audit. Ces colonnes sont déjà persistées
sous forme JSONB dans ``arguments_json->'cognitive_state'`` et
``arguments_json->'objective'`` depuis le Lot 1 — la migration ne fait
qu'**extraire** ces valeurs en colonnes pour permettre :

  1. **Index natifs** sur ``(conversation_stage, created_at)`` et
     ``(emotional_intent, created_at)`` → analytics funnel par
     période sans scan JSONB.
  2. **Lecture directe** depuis l'admin (cf. `admin_cognitive_router`)
     → simplification SQL et pré-calcul possible.
  3. **Compat outils tiers** (Metabase / Retool / Superset) qui ne
     supportent pas toujours élégamment le path JSONB.

──────────────────────────────────────────────────────────────────────
Stratégie 100 % additive
──────────────────────────────────────────────────────────────────────

Aucune contrainte NOT NULL, aucun CHECK : on évite d'imposer un schéma
qui pourrait évoluer (de nouveaux ``emotional_intent`` peuvent
apparaître en V2 avec un classifieur ML, cf. ``COGNITIVE_BOT.md``
§ 11). Toutes les colonnes restent nullable :

  * ``emotional_intent``    VARCHAR(32)  NULL
  * ``conversation_stage``  VARCHAR(16)  NULL
  * ``knowledge_level``     VARCHAR(8)   NULL
  * ``trust_level``         REAL         NULL  (0..1, pas de CHECK)
  * ``primary_goal``        VARCHAR(16)  NULL
  * ``next_best_action``    VARCHAR(20)  NULL

Le runtime (`service._persist_router_decision`) sera mis à jour pour
**double-écrire** dans le JSONB et ces colonnes, mais la JSONB reste
la source de vérité (preserved pour audit complet).

──────────────────────────────────────────────────────────────────────
Backfill non destructif (SQL UPDATE in-place)
──────────────────────────────────────────────────────────────────────

Pour les lignes existantes ``tool_name='router_classify'`` ayant déjà
un ``arguments_json->'cognitive_state'`` (= décisions persistées
depuis le Lot 1, 2026-04-30), on copie les valeurs JSONB vers les
colonnes via un seul ``UPDATE`` SQL idempotent. Les lignes legacy
sans ``cognitive_state`` restent à NULL.

Aucune destruction. Aucune ré-écriture du JSONB. Aucun side-effect
sur les autres lignes (decisions des sub-agents avec
``tool_name != 'router_classify'``).

──────────────────────────────────────────────────────────────────────
Index
──────────────────────────────────────────────────────────────────────

Deux index composites couvrent les principaux usages funnel :

  * ``ix_aad_cognitive_stage_created`` (conversation_stage, created_at)
  * ``ix_aad_emotional_intent_created`` (emotional_intent, created_at)

Tous deux **partial** sur ``WHERE cognitive_*  IS NOT NULL`` pour
n'indexer que les décisions cognitives (économise le stockage et
améliore la sélectivité face aux NULL post-migration).

──────────────────────────────────────────────────────────────────────
Downgrade
──────────────────────────────────────────────────────────────────────

Drop des index puis des colonnes — réversible sans perte tant que la
JSONB reste la source de vérité (le runtime continue à écrire dans
``arguments_json``).

Revision ID: 152
Revises: 151
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "152"
down_revision = "151"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────
# Constantes (longueurs alignées sur les enums applicatifs)
# ─────────────────────────────────────────────────────────────────────


_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    # Cognitive State (Lot 1)
    ("emotional_intent", sa.String(length=32)),
    ("conversation_stage", sa.String(length=16)),
    ("knowledge_level", sa.String(length=8)),
    ("trust_level", sa.Float()),
    # Conversation Objective (Lot 2)
    ("primary_goal", sa.String(length=16)),
    ("next_best_action", sa.String(length=20)),
)


def upgrade() -> None:
    # ─── 1. Add columns (all nullable, no default, no constraint) ────
    for name, col_type in _COLUMNS:
        op.add_column(
            "assistance_agent_decisions",
            sa.Column(name, col_type, nullable=True),
            schema="public",
        )

    # ─── 2. Backfill from JSONB (Lot 1 already-persisted decisions) ──
    # Idempotent : safe to re-run, no destruction, only NULL→value.
    op.execute(
        """
        UPDATE public.assistance_agent_decisions
        SET emotional_intent =
                arguments_json #>> '{cognitive_state,emotional_intent}',
            conversation_stage =
                arguments_json #>> '{cognitive_state,conversation_stage}',
            knowledge_level =
                arguments_json #>> '{cognitive_state,knowledge_level}',
            trust_level = NULLIF(
                arguments_json #>> '{cognitive_state,trust_level}', ''
            )::real,
            primary_goal =
                arguments_json #>> '{objective,primary_goal}',
            next_best_action =
                arguments_json #>> '{objective,next_best_action}'
        WHERE tool_name = 'router_classify'
          AND arguments_json ? 'cognitive_state'
          AND emotional_intent IS NULL
          AND conversation_stage IS NULL;
        """
    )

    # ─── 3. Partial composite indexes for funnel queries ─────────────
    op.create_index(
        "ix_aad_cognitive_stage_created",
        "assistance_agent_decisions",
        ["conversation_stage", "created_at"],
        schema="public",
        postgresql_where=sa.text("conversation_stage IS NOT NULL"),
    )
    op.create_index(
        "ix_aad_emotional_intent_created",
        "assistance_agent_decisions",
        ["emotional_intent", "created_at"],
        schema="public",
        postgresql_where=sa.text("emotional_intent IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_aad_emotional_intent_created",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_index(
        "ix_aad_cognitive_stage_created",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    for name, _col_type in reversed(_COLUMNS):
        op.drop_column(
            "assistance_agent_decisions",
            name,
            schema="public",
        )
