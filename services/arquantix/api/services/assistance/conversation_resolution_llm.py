"""Pont LLM ⇄ backend — résolution conversationnelle structurée (Phase 6).

* Parse / valide ``LLMConversationResolutionSignal`` ;
* ``build_resolution_result_from_llm_signal`` dérive les drapeaux **uniquement** côté backend ;
* ``run_structured_resolution_llm_optional`` peut invoquer OpenAI (**opt-in ENV**) puis
  ``maybe_apply_llm_resolution`` (**aucune mutation** si JSON invalide ou confiance trop basse).

Aucune transition lifecycle depuis le texte brut de l’assistant — seulement depuis un
signal JSON validé.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.assistance.agents.tools.shared import audit as assistance_audit
from services.assistance.config import OPENAI_MODEL
from services.assistance.conversation_resolution import (
    ConversationResolutionApplyOutcome,
    ConversationResolutionResult,
    apply_conversation_resolution,
    build_resolution_result,
)
from services.assistance.llm_resolution_schema import (
    LLMConversationResolutionSignal,
    parse_llm_resolution_json_string,
)
from services.assistance.agents.openai_client import chat_completion
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent / "prompts" / "conversation_resolution_system.md"
)

_TOOL_INVALID: str = "conversation_resolution_llm_invalid"


def _load_system_prompt() -> str:
    try:
        txt = _PROMPT_PATH.read_text(encoding="utf-8")
        if txt.strip():
            return txt.strip()
    except OSError:
        logger.warning("conversation_resolution_llm.prompt_read_failed path=%s", _PROMPT_PATH)
    return (
        "You output ONLY a JSON object with keys "
        "resolution_type, confidence, target_action_type, "
        "reason, extracted_entities. No prose."
    )


def build_resolution_result_from_llm_signal(
    sig: LLMConversationResolutionSignal,
) -> ConversationResolutionResult:
    """Transforme un signal strict LLM vers la décision backend (flags dérivés)."""
    return build_resolution_result(
        sig.resolution_type,
        confidence=sig.confidence,
        target_action_type=sig.target_action_type,
        reason=sig.reason.strip()[:768] if sig.reason else "llm_structured_resolution",
        extracted_entities=dict(sig.extracted_entities),
    )


class StructuredResolutionMetrics:
    """Métriques Phase 6 (process-local, thread-safe minimal)."""

    _lock = threading.Lock()
    _success: int = 0
    _validation_failure: int = 0
    _fallback_low_confidence: int = 0
    _buckets_lock = threading.Lock()
    _confidence_buckets: dict[str, int] = {
        "0.00-0.25": 0,
        "0.25-0.50": 0,
        "0.50-0.75": 0,
        "0.75-1.00": 0,
    }
    _conf_sum_success: float = 0.0
    _conf_n_success: int = 0

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._success = cls._validation_failure = cls._fallback_low_confidence = 0
        with cls._buckets_lock:
            for k in cls._confidence_buckets:
                cls._confidence_buckets[k] = 0
            cls._conf_sum_success = 0.0
            cls._conf_n_success = 0

    @classmethod
    def record_success(cls, confidence: float) -> None:
        with cls._lock:
            cls._success += 1
        c = float(confidence)
        with cls._buckets_lock:
            cls._conf_sum_success += c
            cls._conf_n_success += 1
            bucket = cls._confidence_bucket_label(c)
            cls._confidence_buckets[bucket] = cls._confidence_buckets.get(bucket, 0) + 1

    @classmethod
    def record_validation_failure(cls) -> None:
        with cls._lock:
            cls._validation_failure += 1

    @classmethod
    def record_fallback_confidence(cls) -> None:
        with cls._lock:
            cls._fallback_low_confidence += 1

    @classmethod
    def _confidence_bucket_label(cls, c: float) -> str:
        if c < 0.25:
            return "0.00-0.25"
        if c < 0.5:
            return "0.25-0.50"
        if c < 0.75:
            return "0.50-0.75"
        return "0.75-1.00"

    @classmethod
    def snapshot(cls) -> dict[str, Any]:
        with cls._lock:
            s, vf, fl = cls._success, cls._validation_failure, cls._fallback_low_confidence
        total_ok = max(1, s + vf + fl)
        with cls._buckets_lock:
            buckets = dict(cls._confidence_buckets)
            mean_c = (
                cls._conf_sum_success / cls._conf_n_success
                if cls._conf_n_success
                else None
            )
        return {
            "structured_resolution_success_count": s,
            "structured_resolution_validation_failure_count": vf,
            "structured_resolution_fallback_low_confidence_count": fl,
            "structured_resolution_success_rate": s / total_ok,
            "structured_resolution_validation_failure_rate": vf / total_ok,
            "structured_resolution_fallback_rate": fl / total_ok,
            "structured_resolution_confidence_distribution": buckets,
            "structured_resolution_mean_confidence_on_success": mean_c,
        }


def _log_llm_resolution_outcome(
    *,
    conversation_id: UUID,
    validated: bool,
    signal_dict: Optional[dict[str, Any]],
    applied_lifecycle: Optional[str],
    extra: dict[str, Any],
) -> None:
    payload = {
        "conversation_resolution_signal": signal_dict,
        "validated": validated,
        "applied_resolution": extra.get("applied_resolution"),
        "lifecycle_transition": applied_lifecycle,
        **{k: v for k, v in extra.items() if k != "applied_resolution"},
    }
    logger.info(
        "conversation_resolution_llm.structured %s",
        json.dumps(payload, default=str, ensure_ascii=False)[:8000],
    )


def persist_invalid_llm_resolution_audit(
    db: Session,
    *,
    conversation_id: UUID,
    raw_output: str,
    validation_errors: list[str],
) -> Optional[str]:
    """Trace un échec de validation — **aucune** transition lifecycle."""
    arguments = {
        "reason": "invalid_llm_resolution_signal",
        "raw_output": (raw_output or "")[:4000],
        "validation_errors": list(validation_errors)[:64],
    }
    return assistance_audit.persist_decision(
        db,
        conversation_id=str(conversation_id),
        agent_id="action",
        iteration=0,
        tool_name=_TOOL_INVALID,
        autonomy_level="L0",
        arguments=arguments,
        result_summary={"validated": False},
        error_code="invalid_llm_resolution_signal",
    )


@dataclass(frozen=True)
class StructuredResolutionTurnResult:
    validated: bool
    applied: bool
    low_confidence_fallback: bool
    validation_errors: tuple[str, ...]
    raw_output_excerpt: str
    outcome: Optional[ConversationResolutionApplyOutcome] = None
    resolution: Optional[ConversationResolutionResult] = None

    def to_memory_dict(self) -> dict[str, Any]:
        return {
            "validated": self.validated,
            "applied": self.applied,
            "low_confidence_fallback": self.low_confidence_fallback,
            "validation_errors": list(self.validation_errors),
            "lifecycle_decision": self.outcome.lifecycle_decision
            if self.outcome
            else None,
            "resolution_type": self.resolution.resolution_type
            if self.resolution
            else None,
        }


def _min_confidence_threshold() -> float:
    raw = os.getenv("ASSISTANCE_RESOLUTION_MIN_CONFIDENCE", "0.0").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.0


def maybe_apply_llm_resolution(
    db: Session,
    *,
    conversation_id: UUID,
    raw_llm_output: str,
    active_action_snapshot: Optional[dict[str, Any]] = None,
    stale_continuation_without_draft: bool = False,
    min_confidence: Optional[float] = None,
) -> StructuredResolutionTurnResult:
    """Valide le JSON LLM ; éventuellement applique le lifecycle. Jamais de mutation si invalide."""
    mc = _min_confidence_threshold() if min_confidence is None else min_confidence
    sig, errs = parse_llm_resolution_json_string(raw_llm_output)

    if sig is None:
        StructuredResolutionMetrics.record_validation_failure()
        logger.warning(
            "conversation_resolution_llm.invalid_signal conv=%s errors=%s raw=%r",
            conversation_id,
            errs,
            (raw_llm_output or "")[:500],
        )
        persist_invalid_llm_resolution_audit(
            db,
            conversation_id=conversation_id,
            raw_output=raw_llm_output or "",
            validation_errors=errs,
        )
        _log_llm_resolution_outcome(
            conversation_id=conversation_id,
            validated=False,
            signal_dict=None,
            applied_lifecycle=None,
            extra={
                "validation_errors": errs,
                "applied_resolution": None,
            },
        )
        return StructuredResolutionTurnResult(
            validated=False,
            applied=False,
            low_confidence_fallback=False,
            validation_errors=tuple(errs),
            raw_output_excerpt=(raw_llm_output or "")[:2000],
        )

    if float(sig.confidence) < mc:
        StructuredResolutionMetrics.record_fallback_confidence()
        logger.info(
            "conversation_resolution_llm.low_confidence conv=%s conf=%s min=%s",
            conversation_id,
            sig.confidence,
            mc,
        )
        persist_invalid_llm_resolution_audit(
            db,
            conversation_id=conversation_id,
            raw_output=raw_llm_output or "",
            validation_errors=[f"confidence_below_threshold:{sig.confidence}<{mc}"],
        )
        _log_llm_resolution_outcome(
            conversation_id=conversation_id,
            validated=True,
            signal_dict=sig.model_dump(mode="json"),
            applied_lifecycle=None,
            extra={
                "applied_resolution": None,
                "note": "low_confidence_fallback",
            },
        )
        return StructuredResolutionTurnResult(
            validated=True,
            applied=False,
            low_confidence_fallback=True,
            validation_errors=(f"confidence_below_threshold:{sig.confidence}<{mc}",),
            raw_output_excerpt=(raw_llm_output or "")[:2000],
        )

    res = build_resolution_result_from_llm_signal(sig)
    StructuredResolutionMetrics.record_success(sig.confidence)
    outcome = apply_conversation_resolution(
        db,
        conversation_id=conversation_id,
        resolution=res,
        trigger_source="llm_classifier",
        active_action_snapshot=active_action_snapshot,
        stale_continuation_without_draft=stale_continuation_without_draft,
    )
    _log_llm_resolution_outcome(
        conversation_id=conversation_id,
        validated=True,
        signal_dict=sig.model_dump(mode="json"),
        applied_lifecycle=outcome.lifecycle_decision,
        extra={"applied_resolution": res.resolution_type},
    )
    return StructuredResolutionTurnResult(
        validated=True,
        applied=True,
        low_confidence_fallback=False,
        validation_errors=(),
        raw_output_excerpt=(raw_llm_output or "")[:2000],
        outcome=outcome,
        resolution=res,
    )


def _structured_resolution_llm_enabled() -> bool:
    raw = (os.getenv("ASSISTANCE_STRUCTURED_RESOLUTION_LLM") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def classify_user_message_via_openai(
    *,
    user_message: str,
    pending_action: Optional[dict[str, Any]] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
) -> str:
    """Appel synchrone chat.completions en ``json_object`` — lève LLMError si échec."""
    sys_prompt = _load_system_prompt()
    ctx_payload = json.dumps(
        {
            "user_message": (user_message or "").strip(),
            "pending_action": pending_action if pending_action else None,
        },
        ensure_ascii=False,
        default=str,
    )
    msgs = [
        {"role": "system", "content": sys_prompt},
        {
            "role": "user",
            "content": (
                "Classe selon les règles. Réponds uniquement avec l’objet JSON.\n\n"
                f"{ctx_payload}"
            ),
        },
    ]
    m = model or os.getenv("ASSISTANCE_RESOLUTION_LLM_MODEL", OPENAI_MODEL)
    content = chat_completion(
        msgs,
        model=m,
        temperature=max(0.0, temperature),
        response_format={"type": "json_object"},
    )
    return content.strip()


def run_structured_resolution_llm_turn_if_enabled(
    db: Session,
    *,
    conversation_id: UUID,
    user_message: str,
    pending_action_snapshot: Optional[dict[str, Any]],
) -> Optional[StructuredResolutionTurnResult]:
    """Si ``ASSISTANCE_STRUCTURED_RESOLUTION_LLM`` actif : classify + validate + optional apply."""
    if not _structured_resolution_llm_enabled():
        return None
    try:
        raw = classify_user_message_via_openai(
            user_message=user_message,
            pending_action=pending_action_snapshot,
        )
    except LLMError as exc:
        StructuredResolutionMetrics.record_validation_failure()
        logger.warning(
            "conversation_resolution_llm.openai_failed conv=%s err=%s",
            conversation_id,
            exc,
        )
        persist_invalid_llm_resolution_audit(
            db,
            conversation_id=conversation_id,
            raw_output="",
            validation_errors=[f"llm_error:{exc}"],
        )
        return StructuredResolutionTurnResult(
            validated=False,
            applied=False,
            low_confidence_fallback=False,
            validation_errors=(f"llm_error:{exc}",),
            raw_output_excerpt="",
        )

    return maybe_apply_llm_resolution(
        db,
        conversation_id=conversation_id,
        raw_llm_output=raw,
        active_action_snapshot=pending_action_snapshot,
    )


__all__ = [
    "StructuredResolutionMetrics",
    "StructuredResolutionTurnResult",
    "build_resolution_result_from_llm_signal",
    "classify_user_message_via_openai",
    "maybe_apply_llm_resolution",
    "persist_invalid_llm_resolution_audit",
    "run_structured_resolution_llm_turn_if_enabled",
]
