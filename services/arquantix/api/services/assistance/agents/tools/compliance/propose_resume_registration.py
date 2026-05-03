"""Tool ``propose_resume_registration`` — agent **compliance.registration**, autonomy **L0**.

Lit la session registration active du client et propose le deep-link
de reprise (`vancelian://app/registration_resume`) si pertinent.

Phase 2b : pas d'introspection de l'étape précise — Flutter sait
réouvrir la `RegistrationFlowScreen` qui se positionne automatiquement
sur l'étape courante via `current_step_id` côté backend.

Cf. `docs/arquantix/COMPLIANCE_TOPICS.md` § 3.1.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared import action_cta_catalog

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "propose_resume_registration",
        "description": (
            "Vérifie si le client a une session d'inscription active à "
            "reprendre, et retourne l'action CTA `resume_registration` "
            "avec son deep-link mobile. Si aucune session active n'est "
            "trouvée, retourne `available=false`. À utiliser quand "
            "`diagnose_compliance_topic` retourne "
            "`dominant_topic=registration`. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance.registration",
}


_ACTIVE_SESSION_STATUSES: frozenset[str] = frozenset(
    {"in_progress", "started", "active", "open"}
)


def execute(ctx: ToolContext, **_kwargs: Any) -> dict[str, Any]:
    """Vérifie session active + propose CTA via le catalogue."""
    if not ctx.person_id:
        return {
            "available": False,
            "reason": "no_person_id",
        }
    try:
        registration = compliance_repo.fetch_registration_progress(
            ctx.db, person_id=ctx.person_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "propose_resume_registration.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {
            "available": False,
            "reason": "repo_unavailable",
        }

    session_status = registration.get("session_status")
    has_active = (
        session_status in _ACTIVE_SESSION_STATUSES
        or registration.get("current_step_id") is not None
    )

    if not has_active:
        return {
            "available": False,
            "reason": "no_active_session",
            "session_status": session_status,
        }

    action: Optional[dict[str, str]] = action_cta_catalog.build_action(
        "resume_registration"
    )
    if action is None:
        # Cas pratiquement impossible (kind hardcodé), mais on garde
        # la défense.
        return {
            "available": False,
            "reason": "kind_unavailable_in_catalog",
        }

    return {
        "available": True,
        "session_status": session_status,
        "completed_steps": registration.get("completed_steps") or 0,
        "total_steps_recorded": registration.get("total_steps_recorded") or 0,
        "action": action,
    }
