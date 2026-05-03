"""Tool ``read_registration_progress`` — agent **compliance**, autonomy **L0**.

Snapshot du parcours d'inscription du `person_id` courant.
Cf. `MULTI_AGENTS_RUNTIME.md` § 2.2.

Anti-tipping-off : aucun détail sur les valeurs saisies (la table
`registration_session_data.value_json` n'est pas exposée).
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
        "name": "read_registration_progress",
        "description": (
            "Retourne l'état d'avancement du parcours d'inscription du "
            "client (statut session, nombre d'étapes complétées, dernière "
            "activité). Utile en mode ONBOARDING pour comprendre où le "
            "client est bloqué. Idempotent. Aucun argument requis."
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
            "session_status": None,
            "current_step_id": None,
            "completed_steps": 0,
            "total_steps_recorded": 0,
            "last_activity_at": None,
        }
    try:
        return compliance_repo.fetch_registration_progress(
            ctx.db, person_id=ctx.person_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "read_registration_progress.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {"error": "repo_unavailable"}
