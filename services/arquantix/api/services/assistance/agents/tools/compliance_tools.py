"""Tools V1 pour l'agent `compliance` — stubs.

Renvoient des données minimales et déterministes pour la V1, le temps de
livrer le pipeline multi-agents. La Phase 2 substituera ces fonctions
par de vraies requêtes sur :

  - tables KYC (`kyc_*`)
  - tables transactions Vancelian (`pe_transactions`, etc.)

**Aucune mutation DB.** Lecture seule.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def get_account_status(client_id: str) -> Optional[dict[str, Any]]:
    """Stub V1 : statut compte neutre (KYC validé, compte actif).

    Args:
        client_id: UUID du client courant.

    Returns:
        Dict `{kyc_state, account_active}` ou None si client introuvable.
    """
    if not client_id:
        return None
    # V1 : valeurs neutres positives — l'objectif Phase 1 est uniquement
    # de prouver que le pipeline d'injection de contexte fonctionne.
    return {
        "kyc_state": "validated",
        "account_active": True,
        "stub": True,
    }


def get_recent_transactions(
    client_id: str, *, limit: int = 10
) -> list[dict[str, Any]]:
    """Stub V1 : 0 transaction par défaut.

    Renvoyer une liste vide est intentionnel : ça force l'agent à dire
    *« pas de transaction récente dans le contexte »* plutôt que
    d'inventer. La Phase 2 remplira cette liste avec de vraies données.
    """
    if not client_id or limit <= 0:
        return []
    # On retourne une liste vide en V1 — le stub ne fabrique pas de
    # transactions fictives pour ne pas brouiller les tests humains.
    return []


# Helper utilisé en tests pour simuler des cas concrets sans toucher au
# vrai DB. Non utilisé en prod V1.
def _stub_transactions_dataset(client_id: str) -> list[dict[str, Any]]:
    """Fixture interne pour les tests intégration (non appelée en prod)."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": f"tx_{client_id[:6]}_001",
            "type": "deposit",
            "amount": 5000,
            "status": "completed",
            "created_at": (now - timedelta(days=2)).isoformat(),
        },
        {
            "id": f"tx_{client_id[:6]}_002",
            "type": "withdrawal",
            "amount": 1200,
            "status": "pending",
            "created_at": (now - timedelta(hours=5)).isoformat(),
        },
    ]
