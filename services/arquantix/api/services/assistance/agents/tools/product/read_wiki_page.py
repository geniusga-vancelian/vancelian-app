"""Tool ``read_wiki_page`` — agent **product**, autonomy **L0**.

Lit une fiche markdown du wiki produit (``services/assistance/data/wiki/``)
et retourne les sections structurées (frontmatter + ``Short answer`` +
``Details``) prêtes à être citées/paraphrasées par le LLM.

S'utilise après ``select_wiki_pages`` qui a retourné les candidats.

──────────────────────────────────────────────────────────────────────
Convention de retour
──────────────────────────────────────────────────────────────────────

Si trouvée :

::

    {
      "category":     str,
      "slug":         str,
      "title":        str,
      "status":       str,        # draft | verified | stale
      "audience":     str,        # client | internal
      "last_reviewed": str,       # YYYY-MM-DD ou ""
      "short_answer": str | None, # 2–4 phrases auto-portantes
      "details":      str | None, # markdown plein
      "questions":    [str, ...], # phrasings client (5–8)
      "tags":         [str, ...],
      "related":      [str, ...], # slugs ou paths relatifs
      "sources":      [str, ...], # raw/<filename> ou URL
    }

Si introuvable :

::

    {"error": "not_found", "category": str, "slug": str}

Si arguments manquants :

::

    {"error": "missing_args"}

──────────────────────────────────────────────────────────────────────
Sécurité
──────────────────────────────────────────────────────────────────────

  * **L0 read-only** : lecture filesystem + parsing en mémoire.
  * **Pas de path traversal** : ``category`` validé contre la
    whitelist ``wiki_repo.ALL_CATEGORIES`` ; ``slug`` ne sert pas à
    construire un chemin (lookup dans un dict en cache).
  * **Pas de PII** — par construction (validé éditorial).
  * **Pas d'erreur métier remontée en exception** — toujours
    ``{"error": "<code>"}`` (convention runtime).
"""

from __future__ import annotations

import logging
from typing import Any

from services.assistance.agents.repositories import wiki_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "read_wiki_page",
        "description": (
            "Récupère le contenu structuré d'une fiche du wiki "
            "produit Vancelian par sa catégorie + son slug. À "
            "appeler APRÈS `select_wiki_pages` qui retourne les "
            "candidats. Renvoie title, status, short_answer (≤ 4 "
            "phrases citables), details (markdown plein), tags, "
            "related, sources. Si la fiche est introuvable, "
            "retourne {error: 'not_found'}. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Catégorie de la fiche. Valeurs valides : "
                        "savings, exclusive-offers, crypto, aktio, "
                        "memberships, account, transfers-cards, "
                        "legal-compliance, company, business, "
                        "affiliate-partner, b2b-agent, other, "
                        "concepts, entities, policies."
                    ),
                    "maxLength": 40,
                },
                "slug": {
                    "type": "string",
                    "description": (
                        "Identifiant kebab-case de la fiche (nom "
                        "du fichier sans .md), ex. "
                        "'how-does-the-future-vault-work'."
                    ),
                    "minLength": 1,
                    "maxLength": 120,
                },
            },
            "required": ["category", "slug"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


def execute(
    ctx: ToolContext,
    *,
    category: str,
    slug: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    safe_category = (category or "").strip().lower()
    safe_slug = (slug or "").strip().lower()

    if not safe_category or not safe_slug:
        return {"error": "missing_args"}

    if safe_category not in wiki_repo.ALL_CATEGORIES:
        logger.info(
            "read_wiki_page.unknown_category agent=%s conv=%s "
            "category=%s slug=%s",
            ctx.agent_id,
            ctx.conversation_id,
            safe_category,
            safe_slug,
        )
        return {
            "error": "unknown_category",
            "category": safe_category,
            "slug": safe_slug,
        }

    try:
        page = wiki_repo.fetch_page(category=safe_category, slug=safe_slug)
    except Exception:  # noqa: BLE001
        logger.exception(
            "read_wiki_page.repo_error agent=%s conv=%s "
            "category=%s slug=%s",
            ctx.agent_id,
            ctx.conversation_id,
            safe_category,
            safe_slug,
        )
        return {
            "error": "repo_error",
            "category": safe_category,
            "slug": safe_slug,
        }

    if page is None:
        logger.info(
            "read_wiki_page.not_found agent=%s conv=%s "
            "category=%s slug=%s",
            ctx.agent_id,
            ctx.conversation_id,
            safe_category,
            safe_slug,
        )
        return {
            "error": "not_found",
            "category": safe_category,
            "slug": safe_slug,
        }

    return page.to_read_dict()
