"""Tool ``list_product_knowledge_topics`` — agent **product**, autonomy **L0**.

Liste les `slug` disponibles dans la table `product_knowledge`
(cf. migration 149). Permet à l'agent product de **découvrir** les
fiches existantes quand il n'a pas le slug exact.

──────────────────────────────────────────────────────────────────────
Convention de retour
──────────────────────────────────────────────────────────────────────

```
{
  "topics": [
    {"slug": "deposit_delay_sepa_in",       "topic": "delay",       "title": "..."},
    {"slug": "withdrawal_delay_sepa_out",   "topic": "delay",       "title": "..."},
    ...
  ],
  "filtered_by_topic": str | None,
  "total": int,
}
```

──────────────────────────────────────────────────────────────────────
Sécurité

Aucun risque : la liste est figée par migration, contenu déjà revu.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.repositories import product_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "list_product_knowledge_topics",
        "description": (
            "Liste les fiches de connaissance produit disponibles "
            "(slug + titre + catégorie). Optionnellement filtrable "
            "par catégorie (`delay`, `definition`, `comparison`). "
            "À utiliser quand tu n'as pas le slug exact pour "
            "`read_product_knowledge`. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": (
                        "Filtre optionnel par catégorie : 'delay' "
                        "pour les délais, 'definition' pour les "
                        "fiches produit, etc. Vide = tout."
                    ),
                    "maxLength": 40,
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


def execute(
    ctx: ToolContext, *, topic: Optional[str] = None, **_kwargs: Any
) -> dict[str, Any]:
    safe_topic = (topic or "").strip().lower() or None
    rows = product_repo.list_known_slugs(
        ctx.db, topic=safe_topic, limit=100
    )
    return {
        "topics": rows,
        "filtered_by_topic": safe_topic,
        "total": len(rows),
    }
