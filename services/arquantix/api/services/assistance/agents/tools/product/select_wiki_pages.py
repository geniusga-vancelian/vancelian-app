"""Tool ``select_wiki_pages`` — **shared**, autonomy **L0**.

Pré-filtre Karpathy (option C, cf. ``docs/arquantix/PRODUCT_AGENT.md``
§9.1 et discussion design Phase 2). Lit le wiki MD on-disk
(``services/assistance/data/wiki/``, 243 fiches) et retourne les
``top_k`` fiches dont le frontmatter ``questions:`` matche le mieux
la question utilisateur.

──────────────────────────────────────────────────────────────────────
Lot 1 « Wiki shared » (2026-05-06)
──────────────────────────────────────────────────────────────────────

Historiquement réservé à l'agent ``product``, ce tool est désormais
exposé à **tous** les sub-agents (``compliance.*``, ``advisor``,
``market``) via ``tools/registry.py`` pour qu'ils puissent **lire**
le wiki et fonder leurs réponses sur les FAQ canoniques (au lieu
d'inventer/halluciner). Cf. brainstorming Wiki commun 2026-05-06.

Garde-fou audience :
  * ``ctx.agent_id == "product"`` → toutes les fiches (``client`` +
    ``internal``).
  * ``ctx.agent_id != "product"`` → seules les fiches
    ``audience: client`` sont retournées (les fiches ``internal``
    contiennent souvent des notes éditoriales ou opérationnelles
    qu'on ne veut **pas** voir paraphrasées par les autres agents).

──────────────────────────────────────────────────────────────────────
Convention de retour
──────────────────────────────────────────────────────────────────────

Si match :

::

    {
      "matches": [
        {
          "category":                 str,        # ex. "savings"
          "slug":                     str,        # ex. "what-is-the-flexible-vault"
          "title":                    str,
          "status":                   str,        # draft | verified | stale
          "matched_questions_preview": [str, ...],  # 3 phrasings max
          "tags":                     [str, ...],  # 5 tags max
          "score":                    float,
          "matched_terms":            [str, ...],  # tokens qui ont matché
        },
        ...
      ],
      "total_returned":  int,
      "filtered_by_category": str | None,
      "wiki_total_pages":     int,        # taille du wiki en cache
    }

Si rien (question vide ou aucun match au-dessus du seuil) :

::

    {
      "matches": [],
      "total_returned": 0,
      "filtered_by_category": str | None,
      "wiki_total_pages": int,
    }

──────────────────────────────────────────────────────────────────────
Étape suivante attendue
──────────────────────────────────────────────────────────────────────

Le LLM choisit la fiche la plus pertinente parmi ``matches`` puis
appelle ``read_wiki_page(category, slug)`` pour récupérer le contenu
complet (sections ``Short answer`` + ``Details``).

──────────────────────────────────────────────────────────────────────
Sécurité
──────────────────────────────────────────────────────────────────────

  * **L0 read-only** : aucun side-effect, aucune mutation DB ni FS.
  * **Pas de PII** : le wiki est par construction client-facing
    (validé éditorial). Aucun risque de tipping-off.
  * **Pas de path traversal** : la résolution des chemins se fait
    exclusivement via ``wiki_repo`` qui ne parcourt que les
    catégories whitelistées.
  * **Pas de débordement de payload** : on ne dump jamais le ``body``
    ici (réservé à ``read_wiki_page``). Seuls les méta + 3 question
    phrasings de preview voyagent jusqu'au LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.repositories import wiki_repo, wiki_llm_retriever
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "select_wiki_pages",
        "description": (
            "Cherche dans le wiki produit Vancelian (243 fiches "
            "markdown couvrant savings, exclusive-offers, crypto, "
            "aktio, memberships, account, transfers-cards, "
            "legal-compliance, company, business, affiliate-partner, "
            "b2b-agent, concepts, entities, policies) les pages dont "
            "le frontmatter `questions:` matche le mieux la question "
            "utilisateur. Retourne au max 10 fiches (slug, title, "
            "category, score, extraits). NE LIT PAS le contenu — "
            "appelle ensuite `read_wiki_page(category, slug)` pour "
            "récupérer la fiche choisie. À utiliser pour les "
            "questions client larges (FAQ, mécaniques produit, "
            "exclusive offers, crypto, account, transfers, etc.). "
            "Pour les délais standards courts (SEPA, KYC) ou les "
            "définitions canoniques (Vault, SCPI, Livret), préfère "
            "`read_product_knowledge` (table SQL canonique). "
            "Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "Reformulation concise de la question client "
                        "(FR ou EN), 3 à 200 caractères. Inclus les "
                        "noms de produits ou concepts cités."
                    ),
                    "minLength": 3,
                    "maxLength": 500,
                },
                "top_k": {
                    "type": "integer",
                    "description": (
                        "Nombre maximum de fiches à retourner "
                        "(1..10, défaut 5)."
                    ),
                    "minimum": 1,
                    "maximum": 10,
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Filtre optionnel par catégorie. Valeurs : "
                        "savings, exclusive-offers, crypto, aktio, "
                        "memberships, account, transfers-cards, "
                        "legal-compliance, company, business, "
                        "affiliate-partner, b2b-agent, other, "
                        "concepts, entities, policies. Vide = toutes."
                    ),
                    "maxLength": 40,
                },
            },
            "required": ["question"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


# ─────────────────────────────────────────────────────────────────────
# Lot 1 « Wiki shared » — filtre audience cross-agent
# ─────────────────────────────────────────────────────────────────────

_AUDIENCE_PRIVILEGED_AGENT: str = "product"
"""Seul l'agent ``product`` voit les fiches ``audience: internal``.

Tous les autres agents (compliance.*, advisor, market) sont restreints
aux fiches ``audience: client`` pour éviter de paraphraser des notes
internes éditoriales (souvent non-publiables ou trop techniques).
"""


def _filter_matches_by_audience(
    matches: list[dict[str, Any]],
    *,
    agent_id: str,
) -> tuple[list[dict[str, Any]], int]:
    """Retire les fiches ``audience: internal`` si l'agent appelant
    n'est pas ``product``.

    Tolérant : si ``audience`` est absent du dict (cas legacy ou page
    mal indexée), on suppose ``client`` (par défaut éditorial).

    Returns:
        Tuple ``(filtered_matches, dropped_count)`` — utile pour le
        log diagnostic (combien de fiches internes on a écartées).
    """
    if agent_id == _AUDIENCE_PRIVILEGED_AGENT:
        return matches, 0
    kept: list[dict[str, Any]] = []
    dropped = 0
    for m in matches:
        audience = str(m.get("audience") or "client").strip().lower()
        if audience == "internal":
            dropped += 1
            continue
        kept.append(m)
    return kept, dropped


def execute(
    ctx: ToolContext,
    *,
    question: str,
    top_k: Optional[int] = None,
    category: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    """Implémentation du tool — wraps ``wiki_repo.select_pages``.

    Comportement défensif :
      * Question vide / blanche → ``matches: []`` (pas d'erreur).
      * Catégorie inconnue → ``matches: []`` + log warning.
      * Erreur de cache → log + retour vide (best-effort).

    Garde-fou audience (Lot 1) :
      * Si ``ctx.agent_id != "product"`` → les fiches ``internal``
        sont retirées du résultat. Le compteur des fiches retirées
        est exposé dans la clé ``audience_filtered_out`` (pour
        diagnostic / observabilité).
    """
    safe_question = (question or "").strip()
    safe_top_k = top_k if isinstance(top_k, int) and top_k > 0 else 5
    safe_category = (category or "").strip().lower() or None

    if safe_category and safe_category not in wiki_repo.ALL_CATEGORIES:
        logger.info(
            "select_wiki_pages.unknown_category agent=%s conv=%s "
            "category=%s",
            ctx.agent_id,
            ctx.conversation_id,
            safe_category,
        )
        return {
            "matches": [],
            "total_returned": 0,
            "filtered_by_category": safe_category,
            "wiki_total_pages": wiki_repo.total_pages_loaded(),
            "error": "unknown_category",
        }

    # ── Phase 2 wiki v1.4 patch 3 — Karpathy LLM-as-retriever ──
    # On essaie d'abord le retriever LLM (gère mieux FR↔EN et la
    # sémantique "vue d'ensemble"). Si désactivé via env var, ou s'il
    # échoue, ou s'il retourne 0 slug exploitable, on retombe sur le
    # scoring keyword historique. Le retour du LLM peut aussi inclure
    # un sentinel `__use_sql_catalog__` qui hint le caller vers la
    # fiche SQL `vancelian_product_catalog`.
    llm_result = wiki_llm_retriever.select_pages_via_llm(
        question=safe_question,
        top_k=safe_top_k,
        category=safe_category,
    )
    if llm_result is not None:
        # Cas spécial : sentinel SQL catalog hint.
        if llm_result.get("via") == "llm_sql_hint":
            logger.info(
                "select_wiki_pages.via_sql_catalog_hint agent=%s conv=%s "
                "q_len=%d",
                ctx.agent_id,
                ctx.conversation_id,
                len(safe_question),
            )
            return {
                "matches": [],
                "total_returned": 0,
                "filtered_by_category": safe_category,
                "wiki_total_pages": llm_result.get("wiki_total_pages")
                or wiki_repo.total_pages_loaded(),
                "use_sql_catalog": True,
                "use_sql_catalog_slug": llm_result.get("use_sql_catalog_slug"),
                "selection_reason": llm_result.get("selection_reason"),
                "hint": (
                    "Pour cette question type 'gamme / catalogue / "
                    "produits Vancelian', appelle "
                    "`read_product_knowledge('vancelian_product_catalog')`"
                    " — c'est la fiche SQL canonique qui fait autorité."
                ),
                "via": "llm_sql_hint",
            }
        # Cas nominal LLM avec slugs résolus.
        logger.info(
            "select_wiki_pages.via_llm agent=%s conv=%s q_len=%d "
            "top_k=%d category=%s returned=%d",
            ctx.agent_id,
            ctx.conversation_id,
            len(safe_question),
            safe_top_k,
            safe_category,
            llm_result.get("total_returned", 0),
        )
        # On respecte top_k côté caller : le retriever a son propre cap
        # mais peut renvoyer plus que `safe_top_k` si l'env override.
        matches = (llm_result.get("matches") or [])[:safe_top_k]
        matches, dropped = _filter_matches_by_audience(
            matches, agent_id=ctx.agent_id
        )
        if dropped:
            logger.info(
                "select_wiki_pages.audience_filtered agent=%s conv=%s "
                "dropped=%d via=llm",
                ctx.agent_id,
                ctx.conversation_id,
                dropped,
            )
        return {
            "matches": matches,
            "total_returned": len(matches),
            "filtered_by_category": safe_category,
            "wiki_total_pages": llm_result.get("wiki_total_pages")
            or wiki_repo.total_pages_loaded(),
            "selection_reason": llm_result.get("selection_reason"),
            "via": "llm",
            "audience_filtered_out": dropped,
        }

    # Fallback keyword scoring (legacy ou LLM disable / failed).
    try:
        scored = wiki_repo.select_pages(
            question=safe_question,
            top_k=safe_top_k,
            category=safe_category,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "select_wiki_pages.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {
            "matches": [],
            "total_returned": 0,
            "filtered_by_category": safe_category,
            "wiki_total_pages": 0,
            "error": "repo_error",
        }

    matches = [
        page.to_select_dict(score=score, matched_terms=matched_terms)
        for page, score, matched_terms in scored
    ]
    matches, dropped = _filter_matches_by_audience(
        matches, agent_id=ctx.agent_id
    )
    if dropped:
        logger.info(
            "select_wiki_pages.audience_filtered agent=%s conv=%s "
            "dropped=%d via=keyword",
            ctx.agent_id,
            ctx.conversation_id,
            dropped,
        )
    logger.info(
        "select_wiki_pages.via_keyword agent=%s conv=%s q_len=%d top_k=%d "
        "category=%s returned=%d",
        ctx.agent_id,
        ctx.conversation_id,
        len(safe_question),
        safe_top_k,
        safe_category,
        len(matches),
    )
    return {
        "matches": matches,
        "total_returned": len(matches),
        "filtered_by_category": safe_category,
        "wiki_total_pages": wiki_repo.total_pages_loaded(),
        "via": "keyword",
        "audience_filtered_out": dropped,
    }
