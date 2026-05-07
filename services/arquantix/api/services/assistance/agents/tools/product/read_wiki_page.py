"""Tool ``read_wiki_page`` — **shared**, autonomy **L0**.

Lit une fiche markdown du wiki produit (``services/assistance/data/wiki/``)
et retourne les sections structurées (frontmatter + ``Short answer`` +
``Details``) prêtes à être citées/paraphrasées par le LLM.

S'utilise après ``select_wiki_pages`` qui a retourné les candidats.

──────────────────────────────────────────────────────────────────────
Lot 1 « Wiki shared » (2026-05-06)
──────────────────────────────────────────────────────────────────────

Historiquement réservé à l'agent ``product``, ce tool est désormais
exposé à **tous** les sub-agents (``compliance.*``, ``advisor``,
``market``) via ``tools/registry.py`` (cf. brainstorming Wiki commun).

Garde-fou audience :
  * ``ctx.agent_id == "product"`` → toutes les fiches sont lisibles.
  * ``ctx.agent_id != "product"`` → les fiches ``audience: internal``
    sont **bloquées** (retour ``{"error": "audience_restricted"}``).
    Cohérent avec le filtre appliqué côté ``select_wiki_pages``.

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


# ─────────────────────────────────────────────────────────────────────
# Phase 2 wiki v1.4 patch 3 — Garde-fou cross-référentiel SQL ↔ wiki MD
# ─────────────────────────────────────────────────────────────────────
#
# Empiriquement (cf. analyse conv `534d545b` 2026-05-04), le LLM peut
# passer des slugs **SQL** (table `product_knowledge`) à `read_wiki_page`
# qui s'attend à des slugs **wiki MD**. Exemple observé :
#
#     read_wiki_page(slug="product_basics_exclusive_offer")  → not_found
#     read_wiki_page(slug="product_basics_vault")            → not_found
#     read_wiki_page(slug="product_basics_livret_vancelian") → not_found
#
# Ces slugs existent **uniquement** dans la table SQL. Le `not_found`
# générique ne dit pas au LLM où chercher → il boucle, parfois jusqu'à
# MAX_ITER. On retourne maintenant une erreur typée `wrong_repo` avec
# un hint actionnable.
#
# Préfixes SQL canoniques (cf. seed migrations 149 + 151) :

SQL_KNOWLEDGE_SLUG_PREFIXES: tuple[str, ...] = (
    "product_basics_",
    "deposit_delay_",
    "withdrawal_delay_",
    "kyc_",
    "swap_",
    "kind_",
)


# ─────────────────────────────────────────────────────────────────────
# Lot 1 « Wiki shared » — agent privilégié pour audience: internal
# ─────────────────────────────────────────────────────────────────────

_AUDIENCE_PRIVILEGED_AGENT: str = "product"
"""Seul l'agent ``product`` peut lire les fiches ``audience: internal``."""

# Slugs SQL exacts (sans préfixe régulier) — extension future à mettre
# ici si on ajoute d'autres slugs canoniques.
SQL_KNOWLEDGE_SLUGS_EXACT: frozenset[str] = frozenset({
    "vancelian_product_catalog",
})


def _is_sql_knowledge_slug(slug: str) -> bool:
    """`True` si le slug fourni est un slug SQL `product_knowledge`,
    pas un slug wiki MD. Heuristique sur préfixes + whitelist exacte."""
    if not slug:
        return False
    s = slug.strip().lower()
    if s in SQL_KNOWLEDGE_SLUGS_EXACT:
        return True
    return any(s.startswith(p) for p in SQL_KNOWLEDGE_SLUG_PREFIXES)


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

    # Phase 2 wiki v1.4 patch 3 — garde-fou cross-référentiel.
    # Un slug `product_basics_*` (ou autre préfixe SQL) est dans la
    # table `product_knowledge`, pas dans le wiki MD. On retourne une
    # erreur typée + un hint actionnable au lieu de `not_found`.
    if _is_sql_knowledge_slug(safe_slug):
        logger.info(
            "read_wiki_page.wrong_repo agent=%s conv=%s "
            "category=%s slug=%s — slug looks SQL, hinting redirect",
            ctx.agent_id,
            ctx.conversation_id,
            safe_category,
            safe_slug,
        )
        return {
            "error": "wrong_repo",
            "category": safe_category,
            "slug": safe_slug,
            "hint": (
                f"Le slug `{safe_slug}` est réservé à l'ancienne table SQL "
                "`product_knowledge` (non exposée aux tools dans cette "
                "configuration). Pour obtenir le contenu, utilise "
                "`select_wiki_pages(question, category?)` puis "
                "`read_wiki_page(category, slug)` afin de trouver la fiche "
                "équivalente dans le wiki Markdown."
            ),
        }

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

    # Lot 1 « Wiki shared » — garde-fou audience cross-agent.
    page_audience = (page.audience or "client").strip().lower()
    if (
        page_audience == "internal"
        and ctx.agent_id != _AUDIENCE_PRIVILEGED_AGENT
    ):
        logger.info(
            "read_wiki_page.audience_restricted agent=%s conv=%s "
            "category=%s slug=%s audience=%s",
            ctx.agent_id,
            ctx.conversation_id,
            safe_category,
            safe_slug,
            page_audience,
        )
        return {
            "error": "audience_restricted",
            "category": safe_category,
            "slug": safe_slug,
            "audience": page_audience,
            "hint": (
                "Cette fiche est réservée à un usage interne / éditorial "
                "(audience: internal). Cherche une fiche équivalente "
                "audience: client via select_wiki_pages, ou bien "
                "consulte l'agent product via consult_specialist si la "
                "réponse est sensible."
            ),
        }

    return page.to_read_dict()
