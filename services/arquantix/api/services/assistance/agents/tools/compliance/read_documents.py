"""Tool ``read_documents`` — agent **compliance**, autonomy **L0**.

Résumé documents par type/statut. Aucun lien `storage_*` ni
`metadata_json` n'est jamais retourné (anti-tipping-off + sécurité ops).

Cf. `MULTI_AGENTS_RUNTIME.md` § 2.2 et § 5.
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
        "name": "read_documents",
        "description": (
            "Retourne un résumé agrégé des documents fournis par le "
            "client (compteurs par type et par statut, dernière mise à "
            "jour). Utile pour identifier ce qui manque ou est en "
            "attente de revue. Idempotent. Aucun argument requis."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance",
}


def execute(ctx: ToolContext, **_kwargs: Any) -> dict[str, Any]:
    if not ctx.person_id:
        return {
            "total_count": 0,
            "by_type": {},
            "by_status": {},
            "latest_uploaded_at": None,
        }
    try:
        return compliance_repo.fetch_documents_summary(
            ctx.db, person_id=ctx.person_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "read_documents.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {"error": "repo_unavailable"}
