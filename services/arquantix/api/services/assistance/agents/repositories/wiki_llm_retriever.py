"""Phase 2 wiki v1.4 patch 3 — Karpathy LLM-as-retriever pour le wiki.

Pattern « LLM-as-retriever » (cf. Karpathy 2024) : au lieu d'un scoring
keyword fragile (`wiki_repo._score_page`), on demande à un LLM de
choisir 3-5 fiches à partir d'un **catalogue compact** (titre +
catégorie + tags + 1ʳᵉ phrasing question) couvrant les 222 fiches FAQ.

──────────────────────────────────────────────────────────────────────
Pourquoi

Empiriquement (cf. analyse conv `534d545b` 2026-05-04) :

  * 66 % de nos fiches wiki ont un **titre anglais**, et 100 % de
    leurs `questions:` sont en anglais. Les utilisateurs tapent en
    français → notre `_score_page` (overlap tokens lower-cased, sans
    lemmatisation, sans traduction) **rate** des matches évidents :

        select_wiki_pages("parle moi des offres exclusives",
                          category="exclusive-offers")
            → 0 matches ALORS QUE 34 fiches existent dans cette
              catégorie.

  * Le scoring **sur-pondère** les fiches qui répètent des tokens
    génériques. Exemple : « quels sont les produits Vancelian ? » →
    top score 13.8 sur `what-happens-if-vancelian-does-not-obtain-mica`
    (fiche réglementaire MiCA totalement hors-sujet) parce que
    « Vancelian » apparaît dans 6+ phrasings de la fiche.

Le bot du copain (cf. `data/wiki/chatbot-spec.md`, Jean Guillou) qui
utilise ce wiki en production sur Slack passe par exactement ce
pattern : un LLM Haiku lit `index.md` entier et choisit 3-5 fiches.

──────────────────────────────────────────────────────────────────────
Architecture

  1. Lazy-build d'un **catalogue compact** des 222 fiches FAQ +
     concepts/entities/policies en cache mémoire (TTL = celui de
     `wiki_repo._cache_ttl_seconds()`).
  2. Au call : un appel LLM unique avec prompt système ciblé +
     `tool_choice="required"` sur un function `return_selected_slugs`.
  3. Le LLM retourne 1-5 slugs ordonnés par pertinence + raison courte.
  4. On résout chaque slug via `wiki_repo.fetch_page` → on rebuilt la
     même structure qu'attendue par `select_wiki_pages.execute`.
  5. **Fallback transparent** sur le scoring keyword si l'appel LLM
     échoue, retourne 0 slug, ou que les slugs retournés sont
     introuvables.

──────────────────────────────────────────────────────────────────────
Coût et latence

  * Catalogue compact ≈ 6 000 tokens (1 ligne / fiche × 222 fiches).
  * Réponse ≤ 5 slugs + reasoning court → ≈ 300 tokens.
  * Un appel par tour produit où le LLM décide d'utiliser
    `select_wiki_pages` → ≈ +400 ms / +$0.0001 sur gpt-4o-mini.

──────────────────────────────────────────────────────────────────────
Désactivation

Env var `ASSISTANCE_WIKI_LLM_RETRIEVER_ENABLED=false` → bypass total
(le tool retombe sur le keyword scoring d'origine).

Cf. `services/assistance/agents/config.py::assistance_wiki_llm_retriever_enabled`.

Tests : `tests/test_assistance_wiki_llm_retriever_unit.py`.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Optional

from services.assistance.agents.config import (
    assistance_wiki_llm_retriever_enabled,
    assistance_wiki_llm_retriever_max_slugs,
    assistance_wiki_llm_retriever_model,
)
from services.assistance.agents.openai_client import chat_completion_with_tools
from services.assistance.agents.repositories import wiki_repo
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Cache du catalogue compact
# ─────────────────────────────────────────────────────────────────────


_CATALOG_LOCK = threading.Lock()
_CATALOG_CACHE: dict[str, Any] = {
    "lines": [],
    "by_slug": {},
    "built_at": 0.0,
    "wiki_pages_count": 0,
}

# Ordre d'apparition dans le catalogue compact pour `exclusive-offers` :
# se rapproche de `wiki/index.md` (grandes offres visibles avant le bloc
# alphabétique `cloud-mining-*`) pour réduire le biais retriever vers une
# seule famille — cf. `data/wiki/chatbot-spec.md` §1 (Slack : index structuré
# puis 3–5 pages).
_EXCLUSIVE_OFFERS_CATALOG_PRIORITY: tuple[str, ...] = (
    "what-is-the-exclusive-offer-cloud-mining-by-hearst-infrastru",
    "what-is-the-exclusive-offer-dubai-villa-al-barari",
    "what-is-the-7-luxury-villas-in-bali-exclusive-offer",
    "how-does-the-exclusive-offer-cloud-mining-by-hearst-infrastr",
    "how-does-the-dubai-villa-al-barari-exclusive-offer-work",
    "how-does-the-7-luxury-villas-in-bali-exclusive-offer-work",
    "how-do-project-exit-windows-work",
    "how-exclusive-offer-btc-lending-works",
)


def _ordered_pages_for_catalog(
    category: str, pages: list[wiki_repo.WikiPage]
) -> list[wiki_repo.WikiPage]:
    """Réordonne les pages d'une catégorie pour le catalogue retriever."""
    if category != "exclusive-offers" or not pages:
        return sorted(pages, key=lambda p: p.slug)
    rank = {s: i for i, s in enumerate(_EXCLUSIVE_OFFERS_CATALOG_PRIORITY)}

    def sort_key(p: wiki_repo.WikiPage) -> tuple[int, str]:
        idx = rank.get(p.slug)
        if idx is not None:
            return (0, f"{idx:04d}")
        return (1, p.slug)

    return sorted(pages, key=sort_key)


def _build_catalog_lines(
    *,
    pages_by_category: dict[str, list[wiki_repo.WikiPage]],
    category_filter: Optional[str] = None,
) -> tuple[list[str], dict[str, tuple[str, str]]]:
    """Construit la version compacte du catalogue : 1 ligne par fiche.

    Format ligne :
        - [<category>/<slug>] <title> | tags: tag1, tag2 | q: <1ʳᵉ phrasing>

    Retourne ``(lines, by_slug)`` où ``by_slug`` mappe ``slug``
    (kebab-case unique sur les 222 fiches FAQ) à ``(category, slug)``
    pour résolution rapide des choix LLM.
    """
    lines: list[str] = []
    by_slug: dict[str, tuple[str, str]] = {}

    categories = (
        [category_filter]
        if category_filter and category_filter in pages_by_category
        else sorted(pages_by_category.keys())
    )

    for category in categories:
        pages = pages_by_category.get(category) or []
        for page in _ordered_pages_for_catalog(category, pages):
            tags_str = ", ".join((page.tags or [])[:4]) or "-"
            first_q = ""
            if page.questions:
                first_q = page.questions[0][:120]
            line = (
                f"- [{page.category}/{page.slug}] {page.title}"
                f" | tags: {tags_str}"
                f" | q: {first_q}"
            )
            lines.append(line)
            by_slug[page.slug] = (page.category, page.slug)

    return lines, by_slug


def _ensure_catalog_fresh() -> dict[str, Any]:
    """Rafraîchit le catalogue si le wiki a été rechargé ou si c'est
    le 1ᵉʳ appel. Hot path (dans le tour LLM produit) → on minimise
    le coût quand le cache est valide."""
    cache_ttl = wiki_repo._cache_ttl_seconds()  # noqa: SLF001 — partagé
    now = time.monotonic()
    if (
        _CATALOG_CACHE["lines"]
        and now - _CATALOG_CACHE["built_at"] < cache_ttl
    ):
        return _CATALOG_CACHE

    with _CATALOG_LOCK:
        # Re-check sous lock (autre thread a pu rebuilder).
        if (
            _CATALOG_CACHE["lines"]
            and time.monotonic() - _CATALOG_CACHE["built_at"] < cache_ttl
        ):
            return _CATALOG_CACHE

        all_pages = wiki_repo.all_pages()
        pages_by_category: dict[str, list[wiki_repo.WikiPage]] = {}
        for page in all_pages:
            pages_by_category.setdefault(page.category, []).append(page)
        for cat in pages_by_category:
            pages_by_category[cat].sort(key=lambda p: p.slug)

        lines, by_slug = _build_catalog_lines(
            pages_by_category=pages_by_category,
            category_filter=None,
        )
        _CATALOG_CACHE["lines"] = lines
        _CATALOG_CACHE["by_slug"] = by_slug
        _CATALOG_CACHE["pages_by_category"] = pages_by_category
        _CATALOG_CACHE["built_at"] = time.monotonic()
        _CATALOG_CACHE["wiki_pages_count"] = len(all_pages)
        logger.info(
            "wiki_llm_retriever.catalog_rebuilt pages=%d categories=%d",
            len(all_pages),
            len(pages_by_category),
        )
    return _CATALOG_CACHE


# ─────────────────────────────────────────────────────────────────────
# Prompt + tool spec du retriever
# ─────────────────────────────────────────────────────────────────────


_RETRIEVER_TOOL_SPEC: dict = {
    "type": "function",
    "function": {
        "name": "return_selected_slugs",
        "description": (
            "Retourne 1 à 5 slugs de fiches wiki Vancelian pertinentes "
            "pour la question utilisateur, ordonnés par pertinence "
            "décroissante. Inclus une `reason` courte expliquant le "
            "choix global."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "slugs": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 120,
                        "description": (
                            "Slug exact (kebab-case) tiré du catalogue "
                            "fourni. NE PAS inventer de slug."
                        ),
                    },
                },
                "reason": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 300,
                    "description": (
                        "Justification courte (1-2 phrases) du choix "
                        "global. Pas de citation littérale du contenu."
                    ),
                },
            },
            "required": ["slugs", "reason"],
            "additionalProperties": False,
        },
    },
}


_RETRIEVER_SYSTEM_PROMPT = """\
Tu es un retriever de fiches wiki produit Vancelian. Tu reçois :

1. Une **question utilisateur** en français ou anglais.
2. Optionnellement les **derniers tours** de la conversation pour le \
contexte.
3. Le **catalogue** complet de toutes les fiches disponibles, sous \
forme de lignes compactes :

    - [category/slug] Title | tags: t1, t2 | q: 1ʳᵉ phrasing client

Ton **unique** rôle est de choisir entre 1 et 5 slugs **strictement** \
tirés du catalogue, ordonnés par pertinence décroissante.

Règles **absolues** :
* NE JAMAIS inventer un slug. Recopie EXACTEMENT depuis le catalogue.
* Si la question est en français mais le wiki en anglais, traduis \
mentalement (ex. « offres exclusives » → "exclusive offers", \
« coffre flexible » → "flexible vault", « bundle crypto » → \
"crypto basket").
* Préfère les fiches `status: verified` (= validées éditorial) à \
qualité égale.
* Sur une demande de **vue d'ensemble produits Vancelian** (« quels \
produits ? », « la gamme »), il existe une fiche SQL canonique \
`vancelian_product_catalog` qui répond mieux que n'importe quelle \
fiche wiki. Dans ce cas, retourne 1 slug fictif spécial : \
`__use_sql_catalog__` (le caller saura).
* **Panorama des Offres Exclusives** (liste, découverte, « parlez-moi \
des offres exclusives », « quelles offres », comparaison entre offres \
sans cibler une seule) : tu dois **diversifier** les slugs choisis — \
inclure au moins **une** fiche **Hearst Cloud Mining**, **une** \
**Dubai Villa Al Barari**, **une** **Bali / The Heights (7 villas)** \
(prioriser les titres « What is the … » / « How does … work » visibles \
en tête de bloc `exclusive-offers` dans le catalogue). Ne retourne \
**pas** 4 ou 5 slugs tous du même sous-thème (ex. uniquement \
`cloud-mining-*`) sauf si la question porte **exclusivement** sur ce \
sous-thème (halving, CGUPM, risques mining, etc.).
* Tu ne réponds JAMAIS au client directement — tu sélectionnes seulement \
des fiches. Le tool `return_selected_slugs` est l'unique sortie autorisée.
"""


def _build_retriever_messages(
    *,
    question: str,
    recent_turns: Optional[list[dict]],
    category_hint: Optional[str],
    catalog_lines: list[str],
) -> list[dict]:
    """Compose les messages OpenAI envoyés au retriever LLM."""
    user_block_parts: list[str] = []
    user_block_parts.append(f"Question utilisateur : {question}")

    if category_hint:
        user_block_parts.append(
            f"Indice catégorie (du LLM appelant, peut être ignoré si "
            f"pertinent) : {category_hint}"
        )

    if recent_turns:
        # Limiter à 4 derniers tours (économie tokens) + tronquer chaque
        # message à 240 chars pour ne pas exploser le prompt.
        tail = recent_turns[-4:]
        joined: list[str] = []
        for t in tail:
            role = (t.get("role") or "").strip()
            content = (t.get("content") or "").strip().replace("\n", " ")
            if not role or not content:
                continue
            joined.append(f"  [{role}] {content[:240]}")
        if joined:
            user_block_parts.append(
                "Contexte conversation (derniers tours) :\n" + "\n".join(joined)
            )

    user_block_parts.append(
        "\nCatalogue (1 ligne par fiche, format `- [cat/slug] title | "
        "tags | q`) :"
    )
    user_block_parts.append("\n".join(catalog_lines))

    return [
        {"role": "system", "content": _RETRIEVER_SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_block_parts)},
    ]


# ─────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────


# Sentinel renvoyé par le LLM retriever pour signaler que la question
# correspond mieux à la fiche SQL `vancelian_product_catalog` qu'à
# n'importe quelle fiche wiki MD. Le caller (select_wiki_pages) doit
# alors retourner un retour spécial qui hint l'agent caller vers
# `read_product_knowledge('vancelian_product_catalog')`.
SQL_CATALOG_HINT_SLUG = "__use_sql_catalog__"


def select_pages_via_llm(
    *,
    question: str,
    top_k: int = 5,
    category: Optional[str] = None,
    recent_turns: Optional[list[dict]] = None,
    chat_completion_fn: Optional[Any] = None,
) -> Optional[dict[str, Any]]:
    """Appelle le retriever LLM. Retourne :

    * ``{"matches": [...], "selection_reason": str, "via": "llm"}``
      si le LLM a répondu et que les slugs retournés existent.
    * ``{"matches": [], "use_sql_catalog": True, "via": "llm_sql_hint"}``
      si le LLM a retourné le sentinel ``__use_sql_catalog__``.
    * ``None`` si bypass demandé (env var disable), si l'appel LLM
      échoue, ou si la réponse est inexploitable. Le caller doit
      fallback sur le scoring keyword.
    """
    if not assistance_wiki_llm_retriever_enabled():
        return None

    safe_question = (question or "").strip()
    if not safe_question:
        return None

    cap_top_k = max(1, min(top_k, assistance_wiki_llm_retriever_max_slugs()))
    cache = _ensure_catalog_fresh()
    catalog_lines: list[str] = list(cache.get("lines") or [])
    by_slug: dict[str, tuple[str, str]] = dict(cache.get("by_slug") or {})

    if not catalog_lines:
        logger.warning(
            "wiki_llm_retriever.empty_catalog — fallback keyword"
        )
        return None

    messages = _build_retriever_messages(
        question=safe_question,
        recent_turns=recent_turns,
        category_hint=category,
        catalog_lines=catalog_lines,
    )

    completion_fn = chat_completion_fn or chat_completion_with_tools
    model = assistance_wiki_llm_retriever_model()

    try:
        response = completion_fn(
            messages,
            model=model,
            tools=[_RETRIEVER_TOOL_SPEC],
            tool_choice={
                "type": "function",
                "function": {"name": "return_selected_slugs"},
            },
            temperature=0.1,
        )
    except LLMError as exc:
        logger.warning(
            "wiki_llm_retriever.llm_failed exc=%s — fallback keyword",
            exc,
        )
        return None
    except Exception:  # noqa: BLE001 — defensive, ne jamais crash le tour
        logger.exception(
            "wiki_llm_retriever.llm_unexpected — fallback keyword"
        )
        return None

    tool_calls = (response or {}).get("tool_calls") or []
    if not tool_calls:
        logger.warning(
            "wiki_llm_retriever.no_tool_call resp=%s — fallback",
            (response or {}).get("content", "")[:160],
        )
        return None

    raw_args = (tool_calls[0].get("function") or {}).get("arguments") or "{}"
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except json.JSONDecodeError:
        logger.warning(
            "wiki_llm_retriever.invalid_args raw=%s — fallback",
            str(raw_args)[:160],
        )
        return None

    raw_slugs = args.get("slugs") or []
    reason = (args.get("reason") or "").strip()[:300]
    if not isinstance(raw_slugs, list):
        return None

    cleaned_slugs: list[str] = []
    for s in raw_slugs:
        if isinstance(s, str) and s.strip():
            cleaned_slugs.append(s.strip())
    cleaned_slugs = cleaned_slugs[:cap_top_k]

    # Sentinel SQL catalog hint.
    if SQL_CATALOG_HINT_SLUG in cleaned_slugs:
        logger.info(
            "wiki_llm_retriever.sql_catalog_hint reason=%s", reason[:120]
        )
        return {
            "matches": [],
            "total_returned": 0,
            "wiki_total_pages": cache.get("wiki_pages_count", 0),
            "via": "llm_sql_hint",
            "selection_reason": reason
            or "Question catalogue — utilise la fiche SQL canonique.",
            "use_sql_catalog_slug": "vancelian_product_catalog",
        }

    # Résolution : on garde uniquement les slugs effectivement présents
    # dans le wiki (le LLM peut halluciner malgré l'instruction).
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for slug in cleaned_slugs:
        if slug in seen:
            continue
        seen.add(slug)
        resolved = by_slug.get(slug)
        if not resolved:
            logger.info(
                "wiki_llm_retriever.unknown_slug slug=%s — skipped", slug
            )
            continue
        cat, real_slug = resolved
        page = wiki_repo.fetch_page(category=cat, slug=real_slug)
        if page is None:
            continue
        # On filtre par catégorie demandée si l'argument est explicite
        # — le LLM a pu ignorer l'indice. On reste tolérant : si tous
        # les slugs sont hors catégorie, on les garde quand même
        # (mieux qu'un retour vide).
        matches.append(
            page.to_select_dict(
                score=1.0 - 0.05 * len(matches),  # ranking préservé
                matched_terms=[],
            )
        )

    if not matches:
        logger.warning(
            "wiki_llm_retriever.empty_resolution slugs=%s — fallback",
            cleaned_slugs,
        )
        return None

    if category and category in (cache.get("pages_by_category") or {}):
        # Si l'utilisateur a contraint la catégorie, on filtre — mais
        # uniquement si au moins 1 match reste. Sinon on conserve tout
        # (le LLM a pu faire un meilleur choix transverse).
        filtered = [m for m in matches if m.get("category") == category]
        if filtered:
            matches = filtered

    logger.info(
        "wiki_llm_retriever.ok q_len=%d returned=%d category=%s reason=%s",
        len(safe_question),
        len(matches),
        category,
        reason[:120],
    )
    return {
        "matches": matches,
        "total_returned": len(matches),
        "filtered_by_category": category,
        "wiki_total_pages": cache.get("wiki_pages_count", 0),
        "via": "llm",
        "selection_reason": reason,
    }


def reset_catalog_cache_for_tests() -> None:
    """Helper exposé aux tests pour rebuilder le catalogue à chaque test."""
    with _CATALOG_LOCK:
        _CATALOG_CACHE["lines"] = []
        _CATALOG_CACHE["by_slug"] = {}
        _CATALOG_CACHE["pages_by_category"] = {}
        _CATALOG_CACHE["built_at"] = 0.0
        _CATALOG_CACHE["wiki_pages_count"] = 0


__all__ = [
    "SQL_CATALOG_HINT_SLUG",
    "select_pages_via_llm",
    "reset_catalog_cache_for_tests",
]
