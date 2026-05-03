"""Tools V1 pour l'agent `product` — stubs.

Phase 5 substituera par un **RAG vectoriel** (pgvector ou Qdrant) sur
les fiches produit indexées (PDF/MD côté CMS). En V1, on se contente
d'une heuristique simple par mots-clés + lookup sur la table `pages`
quand le slug est explicite — mais le lookup réel CMS arrive en Phase 5.

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
