"""Tools partagés entre agents (cf. `MULTI_AGENTS_RUNTIME.md` § 7).

Contient les primitives transversales :
  - `classify_actor`     : détecte le type d'acteur (CUSTOMER / ONBOARDING /
                           ADMIN_BO / SUSPENDED) avant tout dispatch agent.
  - `ask_user_question`  : tool d'interaction client (interrupt-based).
  - `audit`              : sanitizer tipping-off + persistance
                           `assistance_agent_decisions`.
  - `action_cta_catalog` : whitelist canonique des deep-links Phase 2b
                           (cf. `COMPLIANCE_TOPICS.md` § 4 et § 8ter).
  - `consult_purposes`   : whitelist des purposes pour `consult_specialist`
                           (Phase 2c, anti-tipping-off cross-agent).
  - `consult_specialist` : tool d'orchestration cross-agent
                           (interrupt-based, Phase 2c).
  - `handoff_to_agent`   : tool de transfert de tour entre sub-agents
                           (interrupt-based, Phase 2c).
"""

from __future__ import annotations

from services.assistance.agents.tools.shared import (
    action_cta_catalog,
    ask_user_question,
    audit,
    consult_purposes,
    consult_specialist,
    handoff_to_agent,
)
from services.assistance.agents.tools.shared.audit import (
    TIPPING_OFF_BLACKLIST,
    persist_decision,
    result_summary,
    sanitize_reasoning,
)
from services.assistance.agents.tools.shared.classify_actor import (
    ActorKind,
    classify_actor,
)

__all__ = [
    "ActorKind",
    "classify_actor",
    "action_cta_catalog",
    "ask_user_question",
    "audit",
    "consult_purposes",
    "consult_specialist",
    "handoff_to_agent",
    "persist_decision",
    "result_summary",
    "sanitize_reasoning",
    "TIPPING_OFF_BLACKLIST",
]
