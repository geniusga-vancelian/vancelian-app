"""Tools de l'agent **product** — Phase 2c.

Le vrai agent `product` (Phase 2c) reçoit son propre toolset L0
read-only :

  - `read_product_knowledge(slug)` — lit la table `product_knowledge`
    (cf. migration 149) et retourne le contenu factuel d'une fiche.
  - `list_product_knowledge_topics(topic?)` — liste les slugs
    disponibles pour aider l'agent à cibler.
  - `show_instrument_card(symbol)` — Phase 2c.6, déclenche une carte
    chat ``instrument_detail_card`` (logo + prix + perf 24h + sparkline
    + boutons Acheter/Vendre). Complémentaire à un message texte.

Cf. `docs/arquantix/PRODUCT_AGENT.md` (Phase 2c).
"""

from __future__ import annotations

from services.assistance.agents.tools.product import (
    list_product_knowledge_topics,
    read_product_knowledge,
    show_instrument_card,
)

__all__ = [
    "list_product_knowledge_topics",
    "read_product_knowledge",
    "show_instrument_card",
]
