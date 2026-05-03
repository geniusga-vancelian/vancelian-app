"""Tool ``read_transactions`` — agent **compliance**, autonomy **L0**.

Résumé transactionnel agrégé du client. Phase 2a : minimal (pas de
montants bruts, pas de détails contrepartie). Sera enrichi en Phase 2b
(dépôts/retraits/crypto) sans casser le contrat de retour.

Cf. `MULTI_AGENTS_RUNTIME.md` § 2.2.
"""

from __future__ import annotations

import logging
from typing import Any

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "read_transactions",
        "description": (
            "Retourne un résumé agrégé des dernières transactions du "
            "client (compteurs par statut, dernière transaction, IDs "
            "opaques des N dernières). Pour le détail d'une transaction "
            "précise, le client doit consulter son espace personnel. "
            "Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de transactions à inclure (1..50).",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance",
}


def execute(ctx: ToolContext, *, limit: int = 25, **_kwargs: Any) -> dict[str, Any]:
    if not ctx.client_id:
        return {
            "orders_count": 0,
            "by_status": {},
            "last_order_at": None,
            "recent_order_ids": [],
        }
    try:
        return compliance_repo.fetch_transactions_summary(
            ctx.db, client_id=ctx.client_id, limit=int(limit) if limit else 25
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "read_transactions.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {"error": "repo_unavailable"}
