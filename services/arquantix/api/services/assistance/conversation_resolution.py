"""Résolution d'intention structurée — Phase 5 (agent Action).

Sépare explicitement :
  1) signal / classification (souvent LLM, tests, ou heuristique dev) ;
  2) décision produit ``ConversationResolutionResult`` ;
  3) application lifecycle via ``apply_conversation_resolution`` (seule couche mutative BDD).

Le LLM ne doit **jamais** appeler directement les transitions lifecycle : il produit
un résultat structuré (ou un signal mappé), le backend applique.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Final, Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.assistance.action_drafts_repo import (
    cancel_active_action_drafts,
    supersede_previous_drafts,
)
from services.assistance.action_lifecycle import (
    MESSAGE_ACTION_DRAFT_EXPIRED_FR,
    classify_interruption_resolution,
)
from services.assistance.agents.tools.shared import audit as assistance_audit

logger = logging.getLogger(__name__)

ConversationResolutionType = Literal[
    "same_action_continuation",
    "new_action_detected",
    "cancel_requested",
    "off_topic",
    "ambiguous",
    "no_active_action",
]

LifecycleDecision = Literal[
    "noop_continuation",
    "noop_off_topic",
    "noop_clarification",
    "noop_no_active_action",
    "cancelled",
    "superseded",
    "restart_flow_suggested",
]

TriggerSource = Literal["system", "user", "llm_classifier", "runtime_tool"]

_TOOL_NAME: Final[str] = "conversation_resolution"


@dataclass
class ConversationResolutionResult:
    """Décision backend avant application lifecycle."""

    resolution_type: ConversationResolutionType
    confidence: float = 1.0
    target_action_type: Optional[str] = None
    reason: str = ""
    should_keep_active_draft: bool = False
    should_cancel_active_draft: bool = False
    should_supersede_active_draft: bool = False
    should_route_to_new_action: bool = False
    extracted_entities: dict[str, Any] = field(default_factory=dict)

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "resolution_type": self.resolution_type,
            "confidence": self.confidence,
            "target_action_type": self.target_action_type,
            "reason": self.reason,
            "should_keep_active_draft": self.should_keep_active_draft,
            "should_cancel_active_draft": self.should_cancel_active_draft,
            "should_supersede_active_draft": self.should_supersede_active_draft,
            "should_route_to_new_action": self.should_route_to_new_action,
            "extracted_entities": dict(self.extracted_entities),
        }


def _policy_flags_for_type(
    rtype: ConversationResolutionType,
) -> tuple[bool, bool, bool, bool]:
    """(keep, cancel, supersede, route_new)"""
    if rtype == "same_action_continuation":
        return True, False, False, False
    if rtype == "off_topic":
        return True, False, False, False
    if rtype == "ambiguous":
        return True, False, False, False
    if rtype == "cancel_requested":
        return False, True, False, False
    if rtype == "new_action_detected":
        return False, False, True, True
    # no_active_action
    return False, False, False, False


def build_resolution_result(
    resolution_type: ConversationResolutionType,
    *,
    confidence: float = 1.0,
    target_action_type: Optional[str] = None,
    reason: str = "",
    extracted_entities: Optional[dict[str, Any]] = None,
) -> ConversationResolutionResult:
    keep, cancel, sup, route = _policy_flags_for_type(resolution_type)
    return ConversationResolutionResult(
        resolution_type=resolution_type,
        confidence=float(confidence),
        target_action_type=target_action_type,
        reason=reason,
        should_keep_active_draft=keep,
        should_cancel_active_draft=cancel,
        should_supersede_active_draft=sup,
        should_route_to_new_action=route,
        extracted_entities=dict(extracted_entities or {}),
    )


def resolution_from_classifier_signal(
    signal: Literal[
        "same_action_continuation",
        "new_action_detected",
        "off_topic",
        "cancel_requested",
        "ambiguous",
        "no_active_action",
    ],
    *,
    confidence: float = 1.0,
    target_action_type: Optional[str] = None,
    reason: str = "",
    extracted_entities: Optional[dict[str, Any]] = None,
) -> tuple[ConversationResolutionResult, str]:
    """Relie ``classify_interruption_resolution`` au résultat structuré complet.

    Retourne ``(ConversationResolutionResult, local_decision)``.
    """
    local = classify_interruption_resolution(signal)
    rtype: ConversationResolutionType
    if signal == "same_action_continuation":
        rtype = "same_action_continuation"
    elif signal == "new_action_detected":
        rtype = "new_action_detected"
    elif signal == "cancel_requested":
        rtype = "cancel_requested"
    elif signal == "off_topic":
        rtype = "off_topic"
    elif signal == "ambiguous":
        rtype = "ambiguous"
    else:
        rtype = "no_active_action"
    res = build_resolution_result(
        rtype,
        confidence=confidence,
        target_action_type=target_action_type,
        reason=reason or f"classifier:{signal}",
        extracted_entities=extracted_entities,
    )
    return res, local


@dataclass(frozen=True)
class ConversationResolutionApplyOutcome:
    lifecycle_decision: LifecycleDecision
    cancelled_count: int
    superseded_count: int
    user_guidance_hint_fr: Optional[str]
    resolution_type: ConversationResolutionType
    active_action_type: Optional[str]
    new_action_type: Optional[str]


class ResolutionMetrics:
    """Compteurs process-wide (observabilité légère, sans dépendance métrique externe)."""

    _lock = threading.Lock()
    _counters: dict[str, int] = {
        "cancel": 0,
        "supersede": 0,
        "ambiguity": 0,
        "off_topic": 0,
        "continuation": 0,
        "no_active": 0,
        "restart_after_expiry": 0,
    }

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            for k in cls._counters:
                cls._counters[k] = 0

    @classmethod
    def snapshot(cls) -> dict[str, int]:
        with cls._lock:
            return dict(cls._counters)

    @classmethod
    def _bump(cls, key: str) -> None:
        with cls._lock:
            cls._counters[key] = cls._counters.get(key, 0) + 1


def persist_conversation_resolution_audit(
    db: Session,
    *,
    conversation_id: UUID,
    resolution: ConversationResolutionResult,
    outcome: ConversationResolutionApplyOutcome,
    trigger_source: TriggerSource,
    iteration: int = 0,
) -> Optional[str]:
    """``audit.persist_decision`` — best-effort."""
    arguments = {
        "resolution_type": resolution.resolution_type,
        "confidence": resolution.confidence,
        "active_action_type": outcome.active_action_type,
        "new_action_type": outcome.new_action_type,
        "lifecycle_decision": outcome.lifecycle_decision,
        "trigger_source": trigger_source,
        **resolution.to_audit_dict(),
    }
    return assistance_audit.persist_decision(
        db,
        conversation_id=str(conversation_id),
        agent_id="action",
        iteration=iteration,
        tool_name=_TOOL_NAME,
        autonomy_level="L0",
        arguments=arguments,
        result_summary={
            "cancelled_count": outcome.cancelled_count,
            "superseded_count": outcome.superseded_count,
            "lifecycle_decision": outcome.lifecycle_decision,
        },
        error_code=None,
    )


def log_resolution_structured(
    *,
    conversation_id: UUID,
    resolution: ConversationResolutionResult,
    outcome: ConversationResolutionApplyOutcome,
    trigger_source: TriggerSource,
) -> None:
    logger.info(
        "conversation_resolution.apply conv=%s type=%s lifecycle=%s "
        "conf=%.2f active=%s new=%s trigger=%s cancel_n=%s supersede_n=%s",
        conversation_id,
        resolution.resolution_type,
        outcome.lifecycle_decision,
        resolution.confidence,
        outcome.active_action_type,
        outcome.new_action_type,
        trigger_source,
        outcome.cancelled_count,
        outcome.superseded_count,
    )


def apply_conversation_resolution(
    db: Session,
    *,
    conversation_id: UUID,
    resolution: ConversationResolutionResult,
    trigger_source: TriggerSource = "llm_classifier",
    active_action_snapshot: Optional[dict[str, Any]] = None,
    stale_continuation_without_draft: bool = False,
) -> ConversationResolutionApplyOutcome:
    """Applique la politique lifecycle à partir d'un résultat structuré.

    * ``stale_continuation_without_draft`` — cas TTL / client désaligné : l'utilisateur
      confirme alors qu'aucun draft actif n'est présent (détecté par l'orchestrateur).
    """
    active_type = (
        str(active_action_snapshot["action_type"]).strip()
        if isinstance(active_action_snapshot, dict)
        and isinstance(active_action_snapshot.get("action_type"), str)
        else None
    )
    new_type = resolution.target_action_type

    if (
        stale_continuation_without_draft
        and resolution.resolution_type == "same_action_continuation"
    ):
        ResolutionMetrics._bump("restart_after_expiry")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="restart_flow_suggested",
            cancelled_count=0,
            superseded_count=0,
            user_guidance_hint_fr=MESSAGE_ACTION_DRAFT_EXPIRED_FR,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        log_resolution_structured(
            conversation_id=conversation_id,
            resolution=resolution,
            outcome=out,
            trigger_source=trigger_source,
        )
        persist_conversation_resolution_audit(
            db,
            conversation_id=conversation_id,
            resolution=resolution,
            outcome=out,
            trigger_source=trigger_source,
        )
        return out

    if resolution.resolution_type == "ambiguous":
        ResolutionMetrics._bump("ambiguity")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="noop_clarification",
            cancelled_count=0,
            superseded_count=0,
            user_guidance_hint_fr=None,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
        return out

    if resolution.resolution_type == "off_topic":
        ResolutionMetrics._bump("off_topic")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="noop_off_topic",
            cancelled_count=0,
            superseded_count=0,
            user_guidance_hint_fr=None,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
        return out

    if resolution.resolution_type == "no_active_action":
        ResolutionMetrics._bump("no_active")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="noop_no_active_action",
            cancelled_count=0,
            superseded_count=0,
            user_guidance_hint_fr=None,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
        return out

    if resolution.resolution_type == "same_action_continuation":
        ResolutionMetrics._bump("continuation")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="noop_continuation",
            cancelled_count=0,
            superseded_count=0,
            user_guidance_hint_fr=None,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
        return out

    cancelled = 0
    superseded_n = 0

    if resolution.should_cancel_active_draft:
        cancelled = cancel_active_action_drafts(
            db,
            conversation_id=conversation_id,
            trigger_source="user",
        )
        ResolutionMetrics._bump("cancel")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="cancelled",
            cancelled_count=cancelled,
            superseded_count=0,
            user_guidance_hint_fr=None,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
        return out

    if resolution.should_supersede_active_draft:
        superseded_n = supersede_previous_drafts(
            db,
            conversation_id=conversation_id,
            trigger_source="llm_classifier",
        )
        ResolutionMetrics._bump("supersede")
        out = ConversationResolutionApplyOutcome(
            lifecycle_decision="superseded",
            cancelled_count=0,
            superseded_count=superseded_n,
            user_guidance_hint_fr=None,
            resolution_type=resolution.resolution_type,
            active_action_type=active_type,
            new_action_type=new_type,
        )
        _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
        return out

    out = ConversationResolutionApplyOutcome(
        lifecycle_decision="noop_no_active_action",
        cancelled_count=0,
        superseded_count=0,
        user_guidance_hint_fr=None,
        resolution_type=resolution.resolution_type,
        active_action_type=active_type,
        new_action_type=new_type,
    )
    _finalize_audit_log(db, conversation_id, resolution, out, trigger_source)
    return out


def _finalize_audit_log(
    db: Session,
    conversation_id: UUID,
    resolution: ConversationResolutionResult,
    outcome: ConversationResolutionApplyOutcome,
    trigger_source: TriggerSource,
) -> None:
    log_resolution_structured(
        conversation_id=conversation_id,
        resolution=resolution,
        outcome=outcome,
        trigger_source=trigger_source,
    )
    persist_conversation_resolution_audit(
        db,
        conversation_id=conversation_id,
        resolution=resolution,
        outcome=outcome,
        trigger_source=trigger_source,
    )


_WS_RE = re.compile(r"\s+")


def _norm_msg(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip().lower())


def heuristic_resolution_development_only(
    user_message: str,
    pending_action: Optional[dict[str, Any]],
) -> ConversationResolutionResult:
    """Classificateur lexical **minimal** pour tests / dev (PAS production par défaut).

    Activé côté service uniquement si ``ASSISTANCE_ACTION_RESOLUTION_HEURISTIC`` truthy.
    """
    txt = _norm_msg(user_message)
    has_pending = isinstance(pending_action, dict) and bool(
        pending_action.get("action_draft_id")
    )

    # Abandon / stop
    if any(
        p in txt
        for p in (
            "laisse tomber",
            "laisser tomber",
            "annule",
            "annuler",
            "plus tard",
            "stop",
            "oublie",
        )
    ):
        return build_resolution_result(
            "cancel_requested",
            confidence=0.85,
            reason="heuristic:cancel_lexicon",
        )

    # Hors sujet info (finance produit générique hors flux action en cours)
    if any(
        p in txt
        for p in (
            "c'est quoi le rendement",
            "quel est le rendement",
            "explique-moi le coffre",
            "explique moi le coffre",
            "comment fonctionne le dcp",
            "comment fonctionne le coffre",
        )
    ):
        return build_resolution_result(
            "off_topic",
            confidence=0.72,
            reason="heuristic:informational_lexicon",
        )

    # Nouvelle intention transactionnelle
    if any(
        p in txt
        for p in (
            "finalement",
            "je préfère vendre",
            "je prefere vendre",
            "non je veux investir",
            "investir dans un coffre",
        )
    ) or (
        "eth" in txt
        and isinstance(pending_action, dict)
        and str(pending_action.get("target_id") or "").strip().upper() == "BTC"
    ):
        return build_resolution_result(
            "new_action_detected",
            confidence=0.78,
            target_action_type="crypto_buy",
            reason="heuristic:new_intent_lexicon",
            extracted_entities={"mentioned_asset": "ETH"} if "eth" in txt else {},
        )

    # Ambigu
    if txt in {"hmm", "euuh", "euh"} or any(
        p in txt for p in ("je ne sais pas", "oui mais pas vraiment", "pas vraiment")
    ):
        return build_resolution_result(
            "ambiguous",
            confidence=0.55,
            reason="heuristic:ambiguous_lexicon",
        )

    # Continuation simple
    if has_pending:
        if txt in {"oui", "ok", "d'accord", "oui confirme", "oui je confirme"}:
            return build_resolution_result(
                "same_action_continuation",
                confidence=0.88,
                reason="heuristic:affirm_short",
            )
        if re.search(r"\d", txt) and any(
            u in txt for u in ("euro", "eur", "€")
        ):
            return build_resolution_result(
                "same_action_continuation",
                confidence=0.8,
                reason="heuristic:amount_followup",
                extracted_entities={"amount_text": txt},
            )
        if "premier compte" in txt or txt == "btc":
            return build_resolution_result(
                "same_action_continuation",
                confidence=0.75,
                reason="heuristic:slot_answer",
            )

    if not has_pending:
        return build_resolution_result(
            "no_active_action",
            confidence=0.5,
            reason="heuristic:no_pending_default",
        )

    return build_resolution_result(
        "same_action_continuation",
        confidence=0.62,
        reason="heuristic:fallback_continue_with_pending",
    )


def infer_resolution_heuristic_development(
    user_message: str,
    pending_action: Optional[dict[str, Any]],
) -> ConversationResolutionResult:
    """Entrée service : vérifie l'ENV avant d'appeler l'heuristique."""
    flag = os.getenv("ASSISTANCE_ACTION_RESOLUTION_HEURISTIC", "").strip().lower()
    if flag not in {"1", "true", "yes", "on"}:
        return build_resolution_result(
            "no_active_action",
            confidence=0.0,
            reason="heuristic_disabled",
        )
    return heuristic_resolution_development_only(user_message, pending_action)


__all__ = [
    "ConversationResolutionApplyOutcome",
    "ConversationResolutionResult",
    "ConversationResolutionType",
    "LifecycleDecision",
    "ResolutionMetrics",
    "TriggerSource",
    "apply_conversation_resolution",
    "build_resolution_result",
    "heuristic_resolution_development_only",
    "infer_resolution_heuristic_development",
    "persist_conversation_resolution_audit",
    "resolution_from_classifier_signal",
]
