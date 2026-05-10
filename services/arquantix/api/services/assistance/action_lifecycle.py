"""Machine d'état — cycle de vie ``AssistanceActionDraft`` (Phase 4).

* Colonne SQL ``status`` **macro** (compat Flutter) :
  ``draft`` = action non terminée ;
  terminaux : ``superseded``, ``cancelled``, ``expired``, ``confirmed``, ``failed``.
* Granularité détaillée dans ``payload["_lifecycle"]`` (``cal_contract`` inchangé).

Le LLM ne fait pas évoluer la machine ; seuls des appels backend déterministes
appliquent des transitions valides.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final, Literal, Mapping, Optional, Union

logger = logging.getLogger(__name__)

AUDIT_AGENT_ID: Final[str] = "action"

LIFECYCLE_PAYLOAD_KEY: Final[str] = "_lifecycle"

MESSAGE_ACTION_DRAFT_EXPIRED_FR: Final[str] = (
    "Cette préparation d'action a expiré. Je vais en créer une nouvelle."
)

ActionDraftLifecycleState = Literal[
    "draft",
    "collecting",
    "awaiting_user_choice",
    "awaiting_confirmation",
    "confirmed",
    "cancelled",
    "superseded",
    "expired",
    "failed",
]

ActionDraftTransitionReason = Literal[
    "user_cancelled",
    "user_changed_topic",
    "ttl_expired",
    "invalidated",
    "confirmed_by_user",
    "superseded_by_new_action",
    "system_failure",
    "completed",
]

TriggerSource = Literal["system", "user", "llm_classifier", "runtime_tool"]

TerminalMacroStatus = Literal[
    "superseded", "cancelled", "expired", "confirmed", "failed"
]

_TERMINAL_MACRO_STATUSES: frozenset[str] = frozenset(
    {"superseded", "cancelled", "expired", "confirmed", "failed"}
)

_MACRO_ACTIVE_DRAFT: Final[str] = "draft"


_ALLOWED_LIFECYCLE_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("draft", "collecting"),
        ("draft", "awaiting_user_choice"),
        ("draft", "awaiting_confirmation"),
        ("draft", "cancelled"),
        ("draft", "superseded"),
        ("draft", "expired"),
        ("draft", "failed"),
        ("collecting", "awaiting_user_choice"),
        ("collecting", "awaiting_confirmation"),
        ("collecting", "cancelled"),
        ("collecting", "superseded"),
        ("collecting", "expired"),
        ("collecting", "failed"),
        ("awaiting_user_choice", "awaiting_confirmation"),
        ("awaiting_user_choice", "collecting"),
        ("awaiting_user_choice", "cancelled"),
        ("awaiting_user_choice", "superseded"),
        ("awaiting_user_choice", "expired"),
        ("awaiting_user_choice", "failed"),
        ("awaiting_confirmation", "confirmed"),
        ("awaiting_confirmation", "cancelled"),
        ("awaiting_confirmation", "superseded"),
        ("awaiting_confirmation", "expired"),
        ("awaiting_confirmation", "failed"),
    }
)


class InvalidLifecycleTransition(ValueError):
    def __init__(self, frm: str, to: str, detail: str = "") -> None:
        self.frm = frm
        self.to = to
        super().__init__(f"transition_interdite:{frm!r}->{to!r}:{detail}")


def is_terminal_macro_status(column_status: str) -> bool:
    return column_status.strip().lower() in _TERMINAL_MACRO_STATUSES


def lifecycle_state_terminal(ls: str) -> bool:
    return ls.strip().lower() in {
        "confirmed",
        "cancelled",
        "superseded",
        "expired",
        "failed",
    }


def is_active_lifecycle_state(ls: str) -> bool:
    return not lifecycle_state_terminal(ls)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_cal_expires_at(payload: Mapping[str, Any]) -> Optional[datetime]:
    if not isinstance(payload, dict):
        return None
    cc = payload.get("cal_contract")
    if not isinstance(cc, dict):
        return None
    raw = cc.get("expires_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def is_action_draft_expired(
    *,
    payload: Mapping[str, Any],
    at: Optional[datetime] = None,
) -> bool:
    exp = parse_cal_expires_at(payload)
    if exp is None:
        return False
    return (at or _now_utc()) > exp


def infer_initial_lifecycle_state(
    *,
    action_type: str,
    business_payload: Mapping[str, Any],
) -> ActionDraftLifecycleState:
    pl = dict(business_payload)
    if pl.get("stage") is not None:
        sk = str(pl.get("stage") or "").strip().lower()
        if sk in {
            "draft_pending_slots",
            "draft_ready_for_backend_validation",
        }:
            return "collecting"
        if sk in {
            "draft_backend_validated",
            "draft_pending_user_confirmation",
        }:
            return "awaiting_confirmation"
        if sk == "source_list":
            return "collecting"
        if sk == "awaiting_launch_confirm":
            return "awaiting_user_choice"
        if sk == "confirmation":
            return "awaiting_confirmation"
    if pl.get("widget_kind"):
        return "collecting"
    _ = action_type
    return "draft"


def get_lifecycle_block(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    lc = payload.get(LIFECYCLE_PAYLOAD_KEY)
    return dict(lc) if isinstance(lc, dict) else {}


def infer_derived_fallback_from_stage(payload: Mapping[str, Any]) -> str:
    return infer_initial_lifecycle_state(
        action_type="",
        business_payload=payload,
    )


def effective_lifecycle_state(
    *,
    column_status: str,
    payload: Mapping[str, Any],
) -> str:
    if column_status.strip().lower() != _MACRO_ACTIVE_DRAFT:
        return column_status.strip().lower()
    lc = get_lifecycle_block(payload).get("state")
    if isinstance(lc, str) and lc.strip():
        return lc.strip().lower()
    return infer_derived_fallback_from_stage(payload)


def merge_lifecycle_block(
    payload: dict[str, Any],
    *,
    state: ActionDraftLifecycleState,
    reason: Union[ActionDraftTransitionReason, str, None],
    trigger: TriggerSource = "system",
    execution_reference: Optional[str] = None,
    execution_status: Optional[str] = None,
) -> None:
    prev = dict(get_lifecycle_block(payload))
    prev.update(
        {
            "state": state,
            "last_transition_reason": reason,
            "last_transition_at": _iso(_now_utc()),
            "trigger_source": trigger,
            "execution_reference": execution_reference
            if execution_reference is not None
            else prev.get("execution_reference"),
            "execution_status": execution_status
            if execution_status is not None
            else prev.get("execution_status"),
        },
    )
    payload[LIFECYCLE_PAYLOAD_KEY] = prev


def seed_initial_lifecycle(
    payload: dict[str, Any],
    *,
    action_type: str,
    trigger: TriggerSource = "runtime_tool",
) -> None:
    """Positionne ``_lifecycle`` à la création (sans entrée ``audit.persist_decision``)."""
    st = infer_initial_lifecycle_state(
        action_type=action_type,
        business_payload=payload,
    )
    prev = dict(get_lifecycle_block(payload))
    payload[LIFECYCLE_PAYLOAD_KEY] = {
        **prev,
        "state": st,
        "trigger_source": trigger,
        "lifecycle_seeded_at": _iso(_now_utc()),
        "execution_reference": prev.get("execution_reference"),
        "execution_status": prev.get("execution_status"),
    }


def macro_status_for_terminal_lifecycle(ls: ActionDraftLifecycleState) -> Optional[str]:
    if not lifecycle_state_terminal(ls):
        return None
    return ls.strip().lower()


def log_lifecycle_transition_structured(evt: "LifecycleTransitionAudit") -> None:
    logger.info(
        "action_draft.lifecycle_transition draft_id=%s conv=%s transition=%s->%s "
        "reason=%s action_type=%s trigger=%s",
        evt.draft_id,
        evt.conversation_id,
        evt.previous_state,
        evt.new_state,
        evt.reason,
        evt.action_type,
        evt.trigger_source,
    )


def can_transition_lifecycle(fr: str, to: str) -> bool:
    a, b = fr.strip().lower(), to.strip().lower()
    if lifecycle_state_terminal(a):
        return False
    forbidden = {
        ("confirmed", "collecting"),
        ("expired", "confirmed"),
        ("cancelled", "confirmed"),
        ("superseded", "confirmed"),
        ("confirmed", "draft"),
        ("confirmed", "awaiting_confirmation"),
    }
    if (a, b) in forbidden:
        return False
    return (a, b) in _ALLOWED_LIFECYCLE_TRANSITIONS


def assert_can_transition(fr: str, to: str) -> None:
    if not can_transition_lifecycle(fr, to):
        raise InvalidLifecycleTransition(fr, to)


@dataclass(frozen=True)
class LifecycleTransitionAudit:
    draft_id: str
    previous_state: str
    new_state: str
    reason: str
    action_type: str
    conversation_id: str
    trigger_source: TriggerSource


def persist_lifecycle_transition_audit(
    db: Any,
    *,
    evt: LifecycleTransitionAudit,
    agent_id: str = AUDIT_AGENT_ID,
    iteration: int = 0,
) -> Optional[str]:
    """Best-effort ``audit.persist_decision`` — sans lever si la DB rejette."""
    from services.assistance.agents.tools.shared import audit as assistance_audit

    arguments = {
        "draft_id": evt.draft_id,
        "previous_state": evt.previous_state,
        "new_state": evt.new_state,
        "reason": evt.reason,
        "action_type": evt.action_type,
        "conversation_id": evt.conversation_id,
        "trigger_source": evt.trigger_source,
    }
    return assistance_audit.persist_decision(
        db,
        conversation_id=evt.conversation_id,
        agent_id=agent_id,
        iteration=iteration,
        tool_name="action_draft_lifecycle",
        autonomy_level="L0",
        arguments=arguments,
        result_summary={"transition": True},
        error_code=None,
    )


def persist_lifecycle_transition_audit_with_log(
    db: Any,
    *,
    evt: LifecycleTransitionAudit,
    agent_id: str = AUDIT_AGENT_ID,
    iteration: int = 0,
) -> Optional[str]:
    log_lifecycle_transition_structured(evt)
    return persist_lifecycle_transition_audit(
        db, evt=evt, agent_id=agent_id, iteration=iteration
    )


def apply_transition_to_sql_row(
    row: Any,
    *,
    to_lifecycle: ActionDraftLifecycleState,
    reason: ActionDraftTransitionReason,
    trigger: TriggerSource,
    payload_overlay: Optional[dict[str, Any]] = None,
    execution_reference: Optional[str] = None,
    execution_status: Optional[str] = None,
) -> LifecycleTransitionAudit:
    """Met à jour ``row.status`` macro et ``row.payload["_lifecycle"]``."""
    merged_base = dict(row.payload if isinstance(row.payload, dict) else {})
    prev = effective_lifecycle_state(column_status=row.status, payload=merged_base)
    assert_can_transition(prev, to_lifecycle)
    merged = dict(merged_base)
    if payload_overlay:
        merged.update(payload_overlay)
    merge_lifecycle_block(
        merged,
        state=to_lifecycle,
        reason=reason,
        trigger=trigger,
        execution_reference=execution_reference,
        execution_status=execution_status,
    )
    macro = macro_status_for_terminal_lifecycle(to_lifecycle)
    if macro is None:
        row.status = _MACRO_ACTIVE_DRAFT
    else:
        row.status = macro
    row.payload = merged
    cid = str(row.conversation_id)
    aid = str(row.action_type)
    return LifecycleTransitionAudit(
        draft_id=str(row.id),
        previous_state=prev,
        new_state=to_lifecycle,
        reason=reason,
        action_type=aid,
        conversation_id=cid,
        trigger_source=trigger,
    )


def ensure_payload_mutable_for_confirmed(payload: Mapping[str, Any]) -> None:
    """Un brouillon ``confirmed`` ne doit pas recevoir de mutation métier."""
    cs = ""
    lc = get_lifecycle_block(payload).get("state")
    if isinstance(lc, str) and lc.strip():
        cs = lc.strip().lower()
    elif isinstance(payload.get("stage"), str):
        # legacy sans _lifecycle
        pass
    if cs == "confirmed":
        raise ValueError("action_draft_confirmed_immutable")


def classify_interruption_resolution(
    signal: Literal[
        "same_action_continuation",
        "new_action_detected",
        "off_topic",
        "cancel_requested",
        "ambiguous",
        "no_active_action",
    ],
) -> Literal[
    "preserve_active_draft", "supersede", "cancel", "noop", "clarification"
]:
    """Décision locale à partir d'un signal structuré (classificateur hors LLM direct).

    Aucune écriture BDD — utiliser ``conversation_resolution.apply_conversation_resolution``
    pour lifecycle.
    """
    if signal == "same_action_continuation":
        return "noop"
    if signal == "new_action_detected":
        return "supersede"
    if signal == "cancel_requested":
        return "cancel"
    if signal == "ambiguous":
        return "clarification"
    if signal == "no_active_action":
        return "noop"
    return "preserve_active_draft"


__all__ = [
    "AUDIT_AGENT_ID",
    "ActionDraftLifecycleState",
    "ActionDraftTransitionReason",
    "InvalidLifecycleTransition",
    "LIFECYCLE_PAYLOAD_KEY",
    "LifecycleTransitionAudit",
    "MESSAGE_ACTION_DRAFT_EXPIRED_FR",
    "TriggerSource",
    "apply_transition_to_sql_row",
    "assert_can_transition",
    "can_transition_lifecycle",
    "classify_interruption_resolution",
    "effective_lifecycle_state",
    "ensure_payload_mutable_for_confirmed",
    "infer_initial_lifecycle_state",
    "is_action_draft_expired",
    "is_active_lifecycle_state",
    "lifecycle_state_terminal",
    "macro_status_for_terminal_lifecycle",
    "merge_lifecycle_block",
    "parse_cal_expires_at",
    "persist_lifecycle_transition_audit",
    "persist_lifecycle_transition_audit_with_log",
    "seed_initial_lifecycle",
    "log_lifecycle_transition_structured",
]

