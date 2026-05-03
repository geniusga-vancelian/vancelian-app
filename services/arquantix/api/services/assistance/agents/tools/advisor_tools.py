"""Tools V1 pour l'agent `advisor` — stubs.

Phase 3 substituera ces stubs par :
  - lecture du portefeuille réel du client (positions, valuation)
  - règles d'allocation cible vs réelle
  - simulateur de scenarios

**Aucune mutation DB.** Lecture seule.
"""

from __future__ import annotations

from typing import Any, Optional


def get_portfolio_snapshot(client_id: str) -> Optional[dict[str, Any]]:
    """Stub V1 : snapshot vide / neutre.

    Retourner None est intentionnel en V1 — l'agent répondra alors en
    s'appuyant uniquement sur la mémoire long-terme (objectifs, horizon)
    qui est déjà très utile pour personnaliser une réponse pédagogique
    sur l'allocation. La Phase 3 ramènera des positions réelles.
    """
    if not client_id:
        return None
    return None
