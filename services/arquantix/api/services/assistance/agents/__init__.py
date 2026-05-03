"""Système multi-agents assistance Vancelian.

Ce package est le coeur du dispatch agentique documenté dans
`docs/arquantix/MULTI_AGENTS.md`. Il expose :

  - `base.AgentBase`         : interface implémentée par chaque agent.
  - `base.AgentInput` / `AgentEvent` / `RouterDecision` : types I/O communs.
  - `router.classify(...)`   : orchestrateur d'intention.
  - `registry.get_agent(id)` : factory qui retourne l'instance d'agent.

Les agents concrets (`assistant_default`, `compliance`, `advisor`,
`product`, `market`) sont enregistrés via `registry.AGENT_REGISTRY`.

L'invariant produit est : **un tour assistant = un agent dispatché par le
router (ou via `agent_hint` côté client)**, jamais plus, jamais de chaînage
en V1 (cf. § 9 du doc d'archi).
"""

from __future__ import annotations

from services.assistance.agents.base import (
    AGENT_DEFAULT_ID,
    AgentBase,
    AgentEvent,
    AgentEventType,
    AgentInput,
    AgentLabel,
    ChoiceOption,
    RouterDecision,
)

__all__ = [
    "AGENT_DEFAULT_ID",
    "AgentBase",
    "AgentEvent",
    "AgentEventType",
    "AgentInput",
    "AgentLabel",
    "ChoiceOption",
    "RouterDecision",
]
