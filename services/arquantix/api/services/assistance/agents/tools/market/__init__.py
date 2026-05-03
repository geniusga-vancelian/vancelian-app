"""Tools de l'agent **market** — Phase 2c.7.

Le vrai agent `market` (réveillé en Phase 2c.7) reçoit son propre
toolset L0 read-only :

  - `show_featured_articles(kind, query?, limit?)` — affiche un embed
    ``featured_articles_list`` listant 1 à 5 articles publiés (NEWS,
    ANALYSIS, RESEARCH) avec deep-link vers le lecteur d'article.
  - `show_top_movers(direction, limit?)` — affiche un embed
    ``top_movers_crypto`` avec les top hausses / baisses / volumes
    24h, chaque ligne étant cliquable pour ouvrir la fiche
    instrument.

Ces tools sont aussi exposés à `advisor` (mention crypto / contexte
marché en complément du conseil) et partiellement à `product` /
`compliance.general` (filet de sécurité quand le router envoie une
question marché là-bas par erreur de classification).

Cf. ``docs/arquantix/CHAT_EMBEDS_CATALOG.md`` § 2.4 et § 2.5.
"""

from __future__ import annotations

from services.assistance.agents.tools.market import (
    show_featured_articles,
    show_top_movers,
)

__all__ = [
    "show_featured_articles",
    "show_top_movers",
]
