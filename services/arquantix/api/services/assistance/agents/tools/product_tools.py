"""Tools V1 pour l'agent `product` — stubs **mode legacy** (path
``ASSISTANCE_RUNTIME_LOOP_AGENTS`` ne contient pas ``product``).

Ce module n'est utilisé QUE par le legacy ``ProductAgent`` Phase 1
(``services/assistance/agents/product.py::_collect_tool_context``).
Quand l'agent `product` est exécuté via le runtime loop Phase 2c
(le mode prod actuel), il utilise les **tools registry** dans
``tools/product/`` (incluant ``select_wiki_pages`` + ``read_wiki_page``
ajoutés en Phase 2).

Phase 5 substituera ce module par un RAG vectoriel sur le wiki MD.
En attendant, l'heuristique mots-clés survit pour le mode legacy.

**Aucune mutation DB.** Lecture seule.
"""

from __future__ import annotations

from typing import Optional

# Mots-clés → slugs produits Vancelian (à enrichir manuellement en
# attendant le RAG). La V1 vise juste à prouver le pipeline.
_KEYWORD_TO_SLUG: dict[str, str] = {
    "livret": "livret-vancelian",
    "épargne": "epargne",
    "epargne": "epargne",
    "immobilier": "immobilier",
    "immo": "immobilier",
    "scpi": "scpi",
    "assurance vie": "assurance-vie",
    "assurance-vie": "assurance-vie",
    "pea": "pea",
    "vault": "vault",
}


def guess_product_slugs(message_lower: str) -> list[str]:
    """Heuristique V1 : retourne les slugs détectés dans le message (en minuscules).

    Args:
        message_lower: message utilisateur déjà passé en `.lower()`.

    Returns:
        Liste dédupliquée de slugs candidats, ordre d'apparition préservé.
    """
    if not message_lower:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for kw, slug in _KEYWORD_TO_SLUG.items():
        if kw in message_lower and slug not in seen:
            found.append(slug)
            seen.add(slug)
    return found


def get_product_summary(slug: str) -> Optional[str]:
    """Stub V1 : pas de lookup CMS encore.

    En V1, retourne None : l'agent répondra avec ses connaissances
    génériques + un disclaimer de prudence. Phase 5 remplira ça.
    """
    if not slug:
        return None
    return None
