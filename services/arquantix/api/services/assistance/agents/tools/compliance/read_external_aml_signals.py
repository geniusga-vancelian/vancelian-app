"""Tool ``read_external_aml_signals`` — agent **compliance**, autonomy **L0**.

Wrapper sur le provider externe AML (KYC + watchlist). Phase 2a : mock
statique safe (jamais de match watchlist explicite — voir
`MULTI_AGENTS_RUNTIME.md` § 6).

Cf. § 5 (frontière de filtrage matérielle) et § 6 (pattern adapter).
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
        "name": "read_external_aml_signals",
        "description": (
            "Retourne les signaux d'un provider AML externe (mock en "
            "Phase 2a). Le payload contient uniquement des étiquettes "
            "neutres (status, flags génériques, message client-facing). "
            "JAMAIS de match watchlist explicite ni de niveau de risque "
            "interne. Idempotent."
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
    try:
        return compliance_repo.fetch_external_aml_signals(
            ctx.db, person_id=ctx.person_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "read_external_aml_signals.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {"error": "repo_unavailable"}
