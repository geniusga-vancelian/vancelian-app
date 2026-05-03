"""Tool ``read_product_knowledge`` — agent **product**, autonomy **L0**.

Récupère une fiche `product_knowledge` par `slug` canonique. Le LLM
de l'agent product s'appuie dessus pour produire des réponses
**factuelles et citables** sur les délais standards (dépôt SEPA,
retrait, KYC) et les bases produit (livret, SCPI, vault).

──────────────────────────────────────────────────────────────────────
Convention de retour
──────────────────────────────────────────────────────────────────────

Si trouvé :

```
{
  "slug":  str,
  "topic": str,
  "title": str,
  "body":  str,            # markdown court (200-500 mots)
  "metadata": dict,
  "updated_at": ISO8601 str | None,
}
```

Sinon : ``{"error": "not_found", "slug": <input>}`` — le LLM peut
répondre sans fiche (il est instruit de rester prudent dans ce cas).

──────────────────────────────────────────────────────────────────────
Sécurité
──────────────────────────────────────────────────────────────────────

Le contenu est par construction **client-facing** (relu, validé,
seedé en migration). Aucun risque tipping-off : pas de PII, pas de
seuils internes, pas de logique compliance.
"""

from __future__ import annotations

import logging
from typing import Any

from services.assistance.agents.repositories import product_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "read_product_knowledge",
        "description": (
            "Récupère le contenu factuel d'une fiche de connaissance "
            "produit par identifiant `slug` canonique (ex. "
            "'deposit_delay_sepa_in', 'withdrawal_delay_sepa_out', "
            "'kyc_review_typical_delay'). À utiliser pour répondre "
            "précisément à une question sur un délai standard ou un "
            "produit Vancelian. Si le slug est inconnu, retourne "
            "{error: 'not_found'} : tu peux alors lister les slugs "
            "disponibles via `list_product_knowledge_topics`. "
            "Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": (
                        "Identifiant canonique de la fiche. "
                        "Utilise `list_product_knowledge_topics` "
                        "si tu ne connais pas le slug exact."
                    ),
                    "minLength": 1,
                    "maxLength": 80,
                },
            },
            "required": ["slug"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


def execute(ctx: ToolContext, *, slug: str, **_kwargs: Any) -> dict[str, Any]:
    safe_slug = (slug or "").strip().lower()
    if not safe_slug:
        return {"error": "missing_slug"}

    knowledge = product_repo.fetch_knowledge_by_slug(ctx.db, slug=safe_slug)
    if knowledge is None:
        logger.info(
            "read_product_knowledge.not_found agent=%s conv=%s slug=%s",
            ctx.agent_id,
            ctx.conversation_id,
            safe_slug,
        )
        return {"error": "not_found", "slug": safe_slug}

    return knowledge
