"""Phase 2 wiki v1.4 patch — slot mémoire `current_topic` par conversation.

Ajoute une colonne JSONB **nullable** `current_topic` sur
``assistance_conversations`` qui matérialise le **sujet actif** d'une
conversation à l'instant t (vs. `recent_turns` qui sont juste les
N derniers messages bruts, et `conversation_summary` qui est une
narration rolling).

──────────────────────────────────────────────────────────────────────
Pourquoi ce slot

Empiriquement (cf. analyse conv `5bef01e9` turn 3, 2026-05-04), le
router LLM peut se laisser tromper par un mot-clé isolé (« perf »,
« cours ») et basculer sur un agent **différent** alors que le
client poursuit le **même** sujet (un produit Vancelian nommé). Le
prompt seul atténue mais ne supprime pas le risque.

Ce slot rend la décision **observable et déterministe** :

  - Quand l'agent `product` appelle `show_bundle_detail(TOP_5)`, on
    set `current_topic = {"kind": "vancelian_product", "product_code":
    "TOP_5", "agent_owner": "product", ...}`.
  - Au tour suivant, le router lit ce slot **avant** de classifier.
    Si le user message contient un déictique (« ce bundle », « il/
    elle »), il garde `agent_owner` sans demander au LLM.
  - Hors déictique / changement de sujet, le LLM reste autoritaire
    (le slot est un **input contextuel**, pas une règle dure).

──────────────────────────────────────────────────────────────────────
Format du slot

Schéma libre (JSONB) — l'enforcement est applicatif (cf.
``services.assistance.conversation_topic``) :

    {
      "kind": "vancelian_product" | "instrument" | "topic_other",
      "product_code": "TOP_5",      # si kind=vancelian_product
      "instrument_symbol": "BTC",   # si kind=instrument
      "agent_owner": "product",     # agent qui a établi le sujet
      "set_at_turn": 4,             # turn_index quand set
      "set_by_tool": "show_bundle_detail",
      "confidence": 0.95,           # 0..1
      "set_at": "2026-05-04T18:14:55Z"
    }

NULL = pas de sujet établi (start of conversation, ou sujet réinitialisé
par un `redirect_off_topic`, ou sujet expiré côté applicatif).

──────────────────────────────────────────────────────────────────────
Migration purement additive : aucun backfill nécessaire — le slot
s'amorce naturellement à partir du prochain tool call qualifié.

Revision ID: 150
Revises: 149
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "150"
down_revision = "149"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "current_topic",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column(
        "assistance_conversations",
        "current_topic",
        schema="public",
    )
