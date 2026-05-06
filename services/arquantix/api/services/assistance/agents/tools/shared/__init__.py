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
    cognitive_context,
    consult_purposes,
    consult_specialist,
    handoff_to_agent,
    topic_context,
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
from services.assistance.agents.tools.shared.cognitive_context import (
    URGENT_EMOTIONS,
    cognitive_snapshot,
    get_conversation_stage,
    get_emotional_intent,
    get_knowledge_level,
    get_next_best_action,
    get_primary_goal,
    get_strategy_hint,
    get_trust_level,
    should_stop_pushing,
)
from services.assistance.agents.tools.shared.topic_context import (
    KNOWN_TOPIC_KINDS,
    get_current_topic_agent_owner,
    get_current_topic_instrument_symbol,
    get_current_topic_kind,
    get_current_topic_label,
    get_current_topic_product_code,
    has_current_topic,
    topic_matches_instrument_symbol,
    topic_matches_product_code,
    topic_snapshot,
)

__all__ = [
    "ActorKind",
    "classify_actor",
    "action_cta_catalog",
    "ask_user_question",
    "audit",
    "cognitive_context",
    "cognitive_snapshot",
    "consult_purposes",
    "consult_specialist",
    "get_conversation_stage",
    "get_current_topic_agent_owner",
    "get_current_topic_instrument_symbol",
    "get_current_topic_kind",
    "get_current_topic_label",
    "get_current_topic_product_code",
    "get_emotional_intent",
    "get_knowledge_level",
    "get_next_best_action",
    "get_primary_goal",
    "get_strategy_hint",
    "get_trust_level",
    "handoff_to_agent",
    "has_current_topic",
    "KNOWN_TOPIC_KINDS",
    "persist_decision",
    "result_summary",
    "sanitize_reasoning",
    "should_stop_pushing",
    "TIPPING_OFF_BLACKLIST",
    "topic_context",
    "topic_matches_instrument_symbol",
    "topic_matches_product_code",
    "topic_snapshot",
    "URGENT_EMOTIONS",
]
