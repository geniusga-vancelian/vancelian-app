"""Construction d'un bloc Markdown « Catalogue Vancelian » injectable dans les prompts.

Objectif
--------
Donner aux agents LLM (router, compliance.transactional, compliance.general,
advisor, product, market) une **vue à jour** des types de transactions et
produits actuellement supportés par la plateforme, **sans rebuild** ni
modification des prompts ``.md``.

Le bloc est ré-évalué à chaque tour (cache TTL 60 s) à partir de la table
``product_knowledge`` (source de vérité éditoriale) :

- ``topic = 'transaction_kind'`` → liste des types de transactions
  (deposit_sepa, buy_crypto, subscribe_bundle, …) avec mapping vers la
  fiche knowledge canonique.
- ``topic = 'definition'``       → liste des produits documentés
  (vault, SCPI, livret, bundle crypto, …).

Garanties
---------
- **Lecture seule.** Aucun side-effect.
- **Best-effort.** Toute erreur DB / I/O retombe sur une chaîne vide
  (les agents continuent à tourner, juste sans le bloc-catalogue).
- **Kill-switch.** ``ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED=1`` désactive
  l'injection partout (utile si la table est en cours de migration).
- **Pas de PII.** La table ``product_knowledge`` ne contient que du contenu
  pédagogique générique.

Notes d'archi
-------------
On évite volontairement d'ajouter une nouvelle table : ``product_knowledge``
est suffisamment souple (``metadata_json`` porte le mapping technique) et
c'est aussi la table lue pour construire ce bloc d'injection prompt.
Les agents **ne** doivent **plus** appeler d'outil SQL sur ces slugs :
passer par le wiki (`select_wiki_pages` / `read_wiki_page`).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from database import ProductKnowledge

logger = logging.getLogger(__name__)


# Whitelist d'agents pour lesquels on injecte le bloc-catalogue. Voir aussi
# ``prompt_builder.build_agent_messages`` qui consomme cette constante.
AGENTS_WITH_CATALOG_CONTEXT: frozenset[str] = frozenset({
    "router",
    "compliance.transactional",
    "compliance.general",
    "advisor",
    "product",
    "market",
})


_TOPIC_TRANSACTION_KIND = "transaction_kind"
_TOPIC_PRODUCT_DEFINITION = "definition"

# Cache mémoire — TTL court pour répercuter rapidement les ajouts de rows
# (admin CMS, seed) sans cogner la DB à chaque tour.
_CACHE_TTL_SECONDS = 60.0
_cache_lock = threading.Lock()
_cached_block: Optional[str] = None
_cached_at: float = 0.0


def _is_disabled() -> bool:
    raw = (os.getenv("ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def invalidate_cache() -> None:
    """Force la régénération du bloc au prochain appel.

    Utile dans les tests, ou après un seed manuel via psql / admin CMS.
    """
    global _cached_block, _cached_at
    with _cache_lock:
        _cached_block = None
        _cached_at = 0.0


def _row_metadata(row: ProductKnowledge) -> dict[str, Any]:
    md = row.metadata_json or {}
    return md if isinstance(md, dict) else {}


def _format_transaction_kinds_section(rows: list[ProductKnowledge]) -> Optional[str]:
    """Produit une table Markdown des types de transactions, triée par display_order.

    Colonnes : Code | Libellé | Direction | Slug knowledge.

    Les rows dont ``metadata.code`` est manquant sont ignorées (best-effort).
    """
    items: list[tuple[int, str, str, str, str]] = []
    for row in rows:
        md = _row_metadata(row)
        code = (md.get("code") or "").strip()
        if not code:
            continue
        label_fr = (md.get("label_fr") or row.title or code).strip()
        direction = (md.get("direction") or "?").strip()
        linked_slug = (md.get("linked_knowledge_slug") or row.slug).strip()
        try:
            order = int(md.get("display_order") or 9999)
        except (TypeError, ValueError):
            order = 9999
        items.append((order, code, label_fr, direction, linked_slug))

    if not items:
        return None

    items.sort(key=lambda x: (x[0], x[1]))

    lines = [
        "### Types de transactions supportées",
        "",
        "| Code | Libellé | Direction | Fiche knowledge |",
        "|---|---|---|---|",
    ]
    for _, code, label, direction, slug in items:
        lines.append(f"| `{code}` | {label} | {direction} | `{slug}` |")
    return "\n".join(lines)


def _format_products_section(rows: list[ProductKnowledge]) -> Optional[str]:
    """Produit une table Markdown des produits documentés.

    On exclut les rows dont ``metadata.exclude_from_catalog = true`` pour les
    fiches purement pédagogiques qui ne sont pas des produits commercialisables.
    Colonnes : Code (slug) | Libellé | Fiche knowledge.
    """
    items: list[tuple[str, str, str]] = []
    for row in rows:
        md = _row_metadata(row)
        if md.get("exclude_from_catalog") is True:
            continue
        slug = (row.slug or "").strip()
        if not slug.startswith("product_basics_"):
            # On limite la section produits aux fiches "product_basics_*" pour ne pas
            # polluer avec d'éventuelles rows topic=definition utilisées ailleurs.
            continue
        title = (row.title or slug).strip()
        items.append((slug, title, slug))

    if not items:
        return None

    items.sort(key=lambda x: x[0])
    lines = [
        "### Produits documentés",
        "",
        "| Code | Libellé | Fiche knowledge |",
        "|---|---|---|",
    ]
    for slug, title, knowledge_slug in items:
        # Pour les produits, le code = slug (pas de mapping séparé en V1).
        code = slug.removeprefix("product_basics_")
        lines.append(f"| `{code}` | {title} | `{knowledge_slug}` |")
    return "\n".join(lines)


def _format_block(
    transaction_kinds_md: Optional[str],
    products_md: Optional[str],
) -> Optional[str]:
    """Assemble le bloc complet avec en-tête et règle d'usage.

    Retourne ``None`` si les deux sections sont vides (rien à dire).
    """
    if not transaction_kinds_md and not products_md:
        return None

    parts: list[str] = [
        "## Catalogue Vancelian (vue dynamique — n'invente rien hors de cette liste)",
        "",
        (
            "Cette liste est générée à partir de la base `product_knowledge` "
            "(mise à jour à chaud sans rebuild). Si un type de transaction ou "
            "un produit n'apparaît pas ici, il n'est **pas supporté** dans "
            "cet environnement et tu dois le dire au client."
        ),
        "",
    ]
    if transaction_kinds_md:
        parts.append(transaction_kinds_md)
        parts.append("")
    if products_md:
        parts.append(products_md)
        parts.append("")
    parts.extend([
        "### Règle d'usage stricte",
        "",
        (
            "1. Pour répondre sur un **type de transaction** ou une **question "
            "produit**, appelle `select_wiki_pages(question, category?)` puis "
            "`read_wiki_page(category, slug)` sur la fiche wiki indiquée dans "
            "cette table (colonne *Fiche knowledge* = slug SQL historique — "
            "cherche l'équivalent wiki si besoin)."
        ),
        (
            "2. Si tu es un agent non-spécialiste, tu peux aussi déléguer via "
            "`consult_specialist(target=product, ...)`."
        ),
        (
            "3. Si le client mentionne un type / produit absent du catalogue, "
            "réponds factuellement *« cette opération n'est pas disponible "
            "actuellement chez Vancelian »* — n'invente pas de slug."
        ),
    ])
    return "\n".join(parts).rstrip() + "\n"


def _query_knowledge_rows(db: Session, topic: str) -> list[ProductKnowledge]:
    """Lecture seule, best-effort. Toute exception est attrapée et logguée."""
    try:
        return (
            db.query(ProductKnowledge)
            .filter(ProductKnowledge.topic == topic)
            .filter(ProductKnowledge.is_active.is_(True))
            .all()
        )
    except Exception:  # noqa: BLE001 — best-effort
        logger.exception(
            "catalog_context_builder._query_knowledge_rows failed topic=%s", topic
        )
        return []


def build_catalog_context_block(db: Session) -> Optional[str]:
    """Compose le bloc Markdown courant. Retourne ``None`` si rien à injecter.

    - Cache TTL 60 s pour éviter de cogner la DB à chaque tour LLM.
    - Pour bypasser le cache (tests / seed), appelle ``invalidate_cache()`` avant.
    - Kill-switch via ``ASSISTANCE_AGENT_CATALOG_CONTEXT_DISABLED=1``.
    """
    if _is_disabled():
        return None

    global _cached_block, _cached_at
    now = time.monotonic()
    with _cache_lock:
        if _cached_block is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
            return _cached_block

    transaction_rows = _query_knowledge_rows(db, _TOPIC_TRANSACTION_KIND)
    product_rows = _query_knowledge_rows(db, _TOPIC_PRODUCT_DEFINITION)

    block = _format_block(
        transaction_kinds_md=_format_transaction_kinds_section(transaction_rows),
        products_md=_format_products_section(product_rows),
    )

    with _cache_lock:
        _cached_block = block
        _cached_at = now
    return block


def should_inject_catalog_for_agent(agent_id: str) -> bool:
    """Helper consommé par ``prompt_builder``."""
    if _is_disabled():
        return False
    return (agent_id or "").strip() in AGENTS_WITH_CATALOG_CONTEXT
