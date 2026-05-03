"""Tools V1 pour l'agent `market` — stubs.

Phase 6 substituera par :
  - connecteur news live (RSS / API Bloomberg / Refinitiv)
  - base d'analyses internes (équipe Vancelian)

**Aucune mutation.** Lecture seule.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Topics canoniques que le router peut reconnaître à partir du message.
_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "equities": ["bourse", "action", "actions", "indice", "indices", "cac", "s&p", "sp500", "sp 500", "msci"],
    "rates": ["taux", "obligation", "obligations", "bce", "fed", "inflation"],
    "real_estate": ["immobilier", "immo", "scpi", "pierre"],
    "crypto": ["crypto", "bitcoin", "btc", "ethereum", "eth"],
    "macro": ["récession", "recession", "croissance", "macro", "économie", "economie"],
}


def guess_topic(message: str) -> str:
    """Heuristique V1 : retourne le topic dominant ou `"general"` à défaut."""
    if not message:
        return "general"
    msg_l = message.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in msg_l for kw in keywords):
            return topic
    return "general"


def get_recent_news(topic: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Stub V1 : retourne 0 item.

    On préfère 0 item plutôt que des news fictives — l'agent dira *« pas
    d'analyses récentes dans mon contexte, je peux te commenter à
    titre général »*. Phase 6 remplira avec de vraies données.
    """
    if not topic or limit <= 0:
        return []
    return []


# Helper utilisé en tests intégration pour simuler des items concrets.
def _stub_news_dataset(topic: str) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "title": f"Stub analyse {topic} — équipe Vancelian",
            "date": now,
            "source": "interne",
            "excerpt": f"Synthèse stub V1 pour le topic « {topic} »…",
        }
    ]
