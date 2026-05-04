"""Tools de l'agent **product** — Phase 2c + Phase 2 wiki.

Le vrai agent `product` (Phase 2c) reçoit son propre toolset L0
read-only :

  - `read_product_knowledge(slug)` — lit la table SQL `product_knowledge`
    (cf. migration 149) et retourne le contenu factuel d'une fiche
    canonique courte (10 fiches : délais SEPA/KYC, définitions
    Vault/SCPI/Livret).
  - `list_product_knowledge_topics(topic?)` — liste les slugs SQL
    disponibles pour aider l'agent à cibler.
  - `show_instrument_card(symbol)` — Phase 2c.6, déclenche une carte
    chat ``instrument_detail_card`` (logo + prix + perf 24h + sparkline
    + boutons Acheter/Vendre). Complémentaire à un message texte.
  - `select_wiki_pages(question)` — **Phase 2 wiki** : pré-filtre
    Karpathy sur les 243 fiches markdown du wiki produit (couverture
    large : FAQ, exclusive offers, crypto, account, transfers, etc.).
    Retourne les top_k fiches matchant les `questions:` frontmatter.
  - `read_wiki_page(category, slug)` — **Phase 2 wiki** : lit une
    fiche wiki MD complète (short_answer + details + sources).

Cohabitation SQL ↔ MD :
  * SQL pour les fiches courtes citables (délais, définitions).
  * MD pour la couverture large (FAQ, transverses, mécaniques produit).
  * Le prompt `product_system.md` cadre la décision pour le LLM.

Cf. `docs/arquantix/PRODUCT_AGENT.md` §9.1.
"""

from __future__ import annotations

from services.assistance.agents.tools.product import (
    list_product_knowledge_topics,
    read_product_knowledge,
    read_wiki_page,
    select_wiki_pages,
    show_instrument_card,
)

__all__ = [
    "list_product_knowledge_topics",
    "read_product_knowledge",
    "read_wiki_page",
    "select_wiki_pages",
    "show_instrument_card",
]
