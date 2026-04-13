"""
Moteur d’auth continue — décision par requête à partir de la session + intelligence.
S’appuie sur [session_intelligence_service] et [sensitive_action_map].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, TYPE_CHECKING

from fastapi import Request

from services.security.sensitive_action_map import (
    AuthLevel,
    SensitiveActionPolicy,
    auth_level_to_tier,
    policy_for_action,
)
from services.security.session_intelligence_service import (
    is_session_intelligence_enabled,
    should_force_reauth,
    should_require_step_up,
    should_relock_local,
)
from services.security.risk_engine import (
    BehavioralRiskContext,
    RiskEvaluation,
    UserSegmentationInput,
    derive_user_segment,
    evaluate_request_risk,
    extract_behavioral_context,
    extract_segmentation_inputs,
    log_risk_outcome_event,
    resolve_low_risk_recent_auth_seconds_for_segment,
    resolve_low_risk_transfer_amount_eur_for_segment,
)
from services.security.security_env import (
    is_adaptive_friction_enabled,
    is_adaptive_intelligence_enabled,
    is_behavioral_risk_enabled,
    is_continuous_auth_enabled,
    is_risk_engine_enabled,
    low_risk_recent_auth_seconds,
    low_risk_transfer_amount_eur,
    risk_critical_threshold,
    risk_high_threshold,
)

if TYPE_CHECKING:
    from database import AuthSession

logger = __import__("logging").getLogger("arquantix.security.continuous_auth")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _recent_auth_satisfied(intel: Any, max_age_seconds: Optional[int]) -> bool:
    if max_age_seconds is None or max_age_seconds <= 0:
        return True
    t = getattr(intel, "last_step_up_at", None)
    if t is None:
        return False
    if getattr(t, "tzinfo", None) is None:
        t = t.replace(tzinfo=timezone.utc)
    return (_utcnow() - t).total_seconds() <= float(max_age_seconds)


def _device_trusted_enough(intel: Any) -> bool:
    dt = str(getattr(intel, "device_trust_level", "") or "").upper()
    return dt in ("HIGH", "TRUSTED")


_STRIP_REASONS_ADAPTIVE = frozenset(
    {
        "recent_auth_required",
        "policy_requires_step_up",
        "device_not_trusted",
        "step_up_required",
        "biometric_recommended",
    }
)


def _reasons_after_adaptive(reasons: List[str]) -> List[str]:
    out = [r for r in reasons if r not in _STRIP_REASONS_ADAPTIVE]
    return out if out else []


def _adaptive_friction_wallet_transfer(
    intel: Any,
    tier: str,
    transfer_amount_eur: Optional[float],
    *,
    user_segment: str = "normal_user",
) -> bool:
    """Transfert « bas risque » : montant + device + récence ; ne contourne pas le step-up SI risque."""
    if transfer_amount_eur is None:
        return False
    amt_limit = (
        resolve_low_risk_transfer_amount_eur_for_segment(user_segment)
        if is_adaptive_intelligence_enabled()
        else low_risk_transfer_amount_eur()
    )
    sec_limit = (
        resolve_low_risk_recent_auth_seconds_for_segment(user_segment)
        if is_adaptive_intelligence_enabled()
        else low_risk_recent_auth_seconds()
    )
    if transfer_amount_eur >= amt_limit:
        return False
    if not _device_trusted_enough(intel):
        return False
    if not _recent_auth_satisfied(intel, sec_limit):
        return False
    if should_require_step_up(intel, tier):
        return False
    return True


def _adaptive_friction_view_sensitive(
    intel: Any,
    tier: str,
    *,
    user_segment: str = "normal_user",
) -> bool:
    """Données sensibles (MEDIUM) : device trusted + récence ; ne downgrade pas si SI impose step-up."""
    if not _device_trusted_enough(intel):
        return False
    sec_limit = (
        resolve_low_risk_recent_auth_seconds_for_segment(user_segment)
        if is_adaptive_intelligence_enabled()
        else low_risk_recent_auth_seconds()
    )
    if not _recent_auth_satisfied(intel, sec_limit):
        return False
    if should_require_step_up(intel, tier):
        return False
    return True


@dataclass
class ContinuousAuthDecision:
    allow: bool
    require_step_up: bool
    require_reauth: bool
    require_biometric: bool
    reason_codes: List[str] = field(default_factory=list)
    policy: Optional[SensitiveActionPolicy] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_factors: List[dict] = field(default_factory=list)
    final_action_key: Optional[str] = None
    recommended_outcome: Optional[str] = None
    user_segment: Optional[str] = None
    dynamic_thresholds_used: Optional[dict] = None
    experiment_id: Optional[str] = None
    variant: Optional[str] = None
    calibration_version: Optional[str] = None

    def to_dict(self) -> dict:
        out = {
            "allow": self.allow,
            "require_step_up": self.require_step_up,
            "require_reauth": self.require_reauth,
            "require_biometric": self.require_biometric,
            "reason_codes": list(self.reason_codes),
        }
        if self.risk_score is not None:
            out["risk_score"] = self.risk_score
        if self.risk_level is not None:
            out["risk_level"] = self.risk_level
        if self.risk_factors:
            out["risk_factors"] = list(self.risk_factors)
        if self.final_action_key is not None:
            out["final_action_key"] = self.final_action_key
        if self.recommended_outcome is not None:
            out["recommended_outcome"] = self.recommended_outcome
        if self.user_segment is not None:
            out["user_segment"] = self.user_segment
        if self.dynamic_thresholds_used is not None:
            out["dynamic_thresholds_used"] = dict(self.dynamic_thresholds_used)
        if self.experiment_id is not None:
            out["experiment_id"] = self.experiment_id
        if self.variant is not None:
            out["variant"] = self.variant
        if self.calibration_version is not None:
            out["calibration_version"] = self.calibration_version
        return out


def _adaptive_friction_applied(reasons: List[str]) -> bool:
    return any(str(r).startswith("adaptive_low_friction") for r in reasons)


def _merge_risk_into_decision(
    dec: ContinuousAuthDecision,
    risk: RiskEvaluation,
    *,
    sensitive_action: Optional[str],
    policy: SensitiveActionPolicy,
    session_intelligence: Any,
    tier: str,
) -> None:
    dec.risk_score = risk.risk_score
    dec.risk_level = risk.risk_level
    dec.risk_factors = [f.model_dump() for f in risk.factors]
    dec.final_action_key = risk.final_action_key
    dec.recommended_outcome = risk.recommended_outcome
    dec.user_segment = getattr(risk, "user_segment", None)
    dec.dynamic_thresholds_used = getattr(risk, "dynamic_thresholds_used", None)
    dec.experiment_id = getattr(risk, "experiment_id", None)
    dec.variant = getattr(risk, "variant", None)
    dec.calibration_version = getattr(risk, "calibration_version", None)

    ov = getattr(risk, "override_reason", None)
    if ov == "behavioral_force_reauth" and "behavioral_force_reauth" not in dec.reason_codes:
        dec.reason_codes.append("behavioral_force_reauth")
    elif ov == "behavioral_force_step_up" and "behavioral_force_step_up" not in dec.reason_codes:
        dec.reason_codes.append("behavioral_force_step_up")

    if dec.require_reauth:
        return

    if risk.recommended_outcome == "reauth":
        dec.require_reauth = True
        dec.require_step_up = False
        dec.allow = False
        dec.require_biometric = False
        rc = list(dec.reason_codes)
        if "risk_engine_reauth" not in rc:
            rc.append("risk_engine_reauth")
        dec.reason_codes = rc
        log_risk_outcome_event(
            "continuous_auth.risk_escalation_applied",
            {
                "action_key": sensitive_action,
                "final_action_key": risk.final_action_key,
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "factor_codes": [f.code for f in risk.factors],
                "recommended_outcome": risk.recommended_outcome,
            },
        )
        return

    if risk.recommended_outcome == "step_up" and dec.allow:
        dec.require_step_up = True
        dec.allow = False
        auth_s = str(getattr(session_intelligence, "auth_strength", "") or "").lower()
        relock = should_relock_local(session_intelligence)
        dec.require_biometric = bool(sensitive_action) and (
            policy.requires_biometric
            or (tier == "high" and "passkey" not in auth_s and relock)
        )
        rc = list(dec.reason_codes)
        if "risk_engine_step_up" not in rc:
            rc.append("risk_engine_step_up")
        dec.reason_codes = rc
        log_risk_outcome_event(
            "continuous_auth.risk_escalation_applied",
            {
                "action_key": sensitive_action,
                "final_action_key": risk.final_action_key,
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "factor_codes": [f.code for f in risk.factors],
                "recommended_outcome": risk.recommended_outcome,
            },
        )


def next_step_hint(dec: ContinuousAuthDecision) -> str:
    """Indicateur machine pour le client (source de vérité côté API)."""
    if dec.require_reauth:
        return "full_reauth"
    if dec.require_step_up and dec.require_biometric:
        return "otp_or_passkey_then_biometric"
    if dec.require_biometric:
        return "biometric_or_passcode"
    if dec.require_step_up:
        return "otp_or_passkey"
    return "none"


def evaluate_request_security_context(
    session: "AuthSession",
    request: Request,
    session_intelligence: Optional[Any],
    *,
    sensitive_action: Optional[str] = None,
    transfer_amount_eur: Optional[float] = None,
    same_owner: Optional[bool] = None,
    similar_actions_recent_count: Optional[int] = None,
    current_user: Optional[Any] = None,
    behavioral_context: Optional[BehavioralRiskContext] = None,
) -> ContinuousAuthDecision:
    """
    Décision pour une requête. Si pas d’intelligence (feature off ou legacy), tout autoriser.
    """
    if not is_continuous_auth_enabled() or not is_session_intelligence_enabled():
        return ContinuousAuthDecision(
            allow=True,
            require_step_up=False,
            require_reauth=False,
            require_biometric=False,
            reason_codes=["continuous_auth_disabled"],
        )

    if session_intelligence is None:
        return ContinuousAuthDecision(
            allow=True,
            require_step_up=False,
            require_reauth=False,
            require_biometric=False,
            reason_codes=["no_session_intelligence"],
        )

    policy = policy_for_action(sensitive_action or "")
    tier = auth_level_to_tier(policy.required_auth_level)
    reasons: List[str] = []

    require_reauth = bool(sensitive_action) and should_force_reauth(session_intelligence, tier)

    require_step_up = bool(sensitive_action) and should_require_step_up(session_intelligence, tier)
    # Step-up « policy » : si une fenêtre ``requires_recent_auth_seconds`` est définie, c’est elle qui
    # porte l’exigence (step-up récent), pas un refus permanent. Sinon, ``requires_step_up`` seul force
    # la friction à chaque requête (actions sans fenêtre explicite).
    if bool(sensitive_action) and policy.requires_recent_auth_seconds is not None:
        if not _recent_auth_satisfied(session_intelligence, policy.requires_recent_auth_seconds):
            require_step_up = True
            reasons.append("recent_auth_required")
    elif bool(sensitive_action) and policy.requires_step_up:
        require_step_up = True
        reasons.append("policy_requires_step_up")
    if bool(sensitive_action) and policy.allowed_if_device_trusted_only:
        if not _device_trusted_enough(session_intelligence):
            require_step_up = True
            reasons.append("device_not_trusted")

    relock = should_relock_local(session_intelligence)
    auth_s = str(getattr(session_intelligence, "auth_strength", "") or "").lower()
    require_biometric = bool(sensitive_action) and (
        policy.requires_biometric
        or (tier == "high" and "passkey" not in auth_s and relock)
    )

    if require_reauth:
        reasons.append("reauth_required")
    if require_step_up:
        reasons.append("step_up_required")
    if require_biometric:
        reasons.append("biometric_recommended")

    seg_inputs: Optional[UserSegmentationInput] = None
    user_segment: str = "normal_user"
    if is_adaptive_intelligence_enabled():
        seg_inputs = extract_segmentation_inputs(request, current_user, session_intelligence)
        user_segment = derive_user_segment(seg_inputs)

    if is_adaptive_friction_enabled() and not require_reauth:
        if (
            sensitive_action == "wallet_transfer"
            and require_step_up
            and _adaptive_friction_wallet_transfer(
                session_intelligence,
                tier,
                transfer_amount_eur,
                user_segment=user_segment,
            )
        ):
            require_step_up = False
            require_biometric = False
            reasons = _reasons_after_adaptive(reasons)
            reasons.append("adaptive_low_friction_transfer")
        elif (
            sensitive_action == "view_sensitive_data"
            and policy.required_auth_level == AuthLevel.MEDIUM
            and require_step_up
            and _adaptive_friction_view_sensitive(
                session_intelligence,
                tier,
                user_segment=user_segment,
            )
        ):
            require_step_up = False
            require_biometric = False
            reasons = _reasons_after_adaptive(reasons)
            reasons.append("adaptive_low_friction_view_sensitive")

    allow = not (require_reauth or require_step_up)

    reason_codes_final: List[str] = list(reasons or ["ok"])

    dec = ContinuousAuthDecision(
        allow=allow,
        require_step_up=require_step_up,
        require_reauth=require_reauth,
        require_biometric=require_biometric,
        reason_codes=reason_codes_final,
        policy=policy,
        final_action_key=sensitive_action or None,
    )

    if (
        is_risk_engine_enabled()
        and bool(sensitive_action)
        and session_intelligence is not None
    ):
        behavioral_ctx = behavioral_context
        if behavioral_ctx is None and is_behavioral_risk_enabled():
            behavioral_ctx = extract_behavioral_context(
                request, current_user, session_intelligence, session
            )
        risk = evaluate_request_risk(
            action_key=sensitive_action or "",
            policy=policy,
            request=request,
            current_user=current_user,
            intelligence=session_intelligence,
            device_trust_level=str(getattr(session_intelligence, "device_trust_level", "") or "") or None,
            last_step_up_at=getattr(session_intelligence, "last_step_up_at", None),
            amount_eur=transfer_amount_eur,
            same_owner=same_owner,
            strict_decision_context={
                "require_reauth": require_reauth,
                "require_step_up": require_step_up,
                "allow": allow,
                "reason_codes": list(reason_codes_final),
                "adaptive_friction_applied": _adaptive_friction_applied(reason_codes_final),
            },
            high_threshold=risk_high_threshold(),
            critical_threshold=risk_critical_threshold(),
            burst_recent_count_override=similar_actions_recent_count,
            behavioral_context=behavioral_ctx,
            session=session,
            segmentation_inputs=seg_inputs if is_adaptive_intelligence_enabled() else None,
        )
        _merge_risk_into_decision(
            dec,
            risk,
            sensitive_action=sensitive_action,
            policy=policy,
            session_intelligence=session_intelligence,
            tier=tier,
        )

    return dec
