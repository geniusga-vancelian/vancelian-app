"""Garde-fou Phase 1 — intentions transactionnelles sans runtime CAL Action.

Empêche le fallback ``ActionAgent.stream`` (texte LLM sans tools) lorsque
l'environnement d'exécution ``run_agent_loop`` pour l'agent ``action``
n'est pas réuni (loop désactivée, identité incomplète, catalogue tools vide).

Cf. décision sécurité produit « action_runtime_unavailable ».
"""

from __future__ import annotations

import logging
from typing import Optional

from services.assistance.agents.base import AGENT_ACTION_ID, RouterDecision
from services.assistance.agents.config import (
    assistance_runtime_loop_agents,
    assistance_runtime_loop_enabled,
)
from services.assistance.agents.orchestration_context import TRANSACTION_KINDS
from services.assistance.agents.tools import registry as tools_registry
from services.assistance.agents.tools.shared.classify_actor import ActorKind

logger = logging.getLogger(__name__)

ACTION_RUNTIME_UNAVAILABLE_USER_FR = (
    "Je peux vous accompagner, mais le module d’actions sécurisées "
    "n’est pas disponible pour le moment. "
    "Veuillez utiliser les parcours prévus dans l’application "
    "(achat, vente, dépôt ou investissement)."
)


def _norm_transaction_kind(orch: dict) -> Optional[str]:
    raw = orch.get("transaction_kind")
    if raw is None:
        return None
    s = str(raw).strip().lower()
    return s if s in TRANSACTION_KINDS else None


def is_transactional_assistance_intent(decision: RouterDecision) -> bool:
    """Signal métier explicitement transactionnel OU routage vers Action."""
    agent_top = decision.agent_id.split(".", 1)[0].strip().lower()
    if agent_top == AGENT_ACTION_ID:
        return True

    orch = decision.orchestration if isinstance(decision.orchestration, dict) else None
    if not orch:
        return False
    bi = str(orch.get("business_intent") or "").strip().lower()
    if bi == "action_request":
        return True
    return _norm_transaction_kind(orch) is not None


def is_action_cal_runtime_environment_ready(
    *,
    actor_kind: Optional[ActorKind],
    user_id: Optional[int],
) -> bool:
    """Prérequis minimaux pour exécuter ``run_agent_loop`` côté agent ``action``."""
    if not assistance_runtime_loop_enabled():
        return False
    agents = assistance_runtime_loop_agents()
    if AGENT_ACTION_ID not in agents:
        return False
    if actor_kind is None or user_id is None:
        return False
    if not bool(tools_registry.tools_for(AGENT_ACTION_ID)):
        return False
    return True


def should_refuse_transactional_without_action_runtime(
    decision: RouterDecision,
    *,
    actor_kind: Optional[ActorKind],
    user_id: Optional[int],
) -> bool:
    """True ⇒ ne pas invoquer un LLM en Phase 1 sur ce tour."""
    if not is_transactional_assistance_intent(decision):
        return False
    return not is_action_cal_runtime_environment_ready(
        actor_kind=actor_kind, user_id=user_id
    )


def log_action_runtime_blocked(
    *,
    conversation_id: object,
    decision: RouterDecision,
    actor_kind: Optional[ActorKind],
    user_id: Optional[int],
) -> dict:
    """Construit payload structuré log + résulté pour ``arguments_json`` audit."""
    orch = decision.orchestration if isinstance(decision.orchestration, dict) else {}
    runtime_agents_sorted = sorted(assistance_runtime_loop_agents())
    payload = {
        "reason": "action_runtime_unavailable",
        "agent_id": decision.agent_id,
        "business_intent": orch.get("business_intent"),
        "transaction_kind": orch.get("transaction_kind"),
        "runtime_loop_enabled": assistance_runtime_loop_enabled(),
        "runtime_loop_agents": runtime_agents_sorted,
        "action_in_runtime_agents": AGENT_ACTION_ID in assistance_runtime_loop_agents(),
        "has_actor_kind": actor_kind is not None,
        "has_user_id": user_id is not None,
    }
    logger.warning(
        "assistance.action_runtime_unavailable conv=%s agent_id=%s "
        "business_intent=%r transaction_kind=%r runtime_loop_enabled=%s "
        "runtime_agents=%s",
        conversation_id,
        payload["agent_id"],
        payload["business_intent"],
        payload["transaction_kind"],
        payload["runtime_loop_enabled"],
        runtime_agents_sorted,
    )
    return payload


__all__ = [
    "ACTION_RUNTIME_UNAVAILABLE_USER_FR",
    "is_action_cal_runtime_environment_ready",
    "is_transactional_assistance_intent",
    "log_action_runtime_blocked",
    "should_refuse_transactional_without_action_runtime",
]
