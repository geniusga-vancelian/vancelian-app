"""
Orchestrateur unique d’authentification adaptative — compose device trust, risque, fraude ML,
passkeys, attestation, sans dupliquer les services existants.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy.orm import Session

from database import AdminUser, AuthSecurityDecision
from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event
from services.security.login_auth_strategy_service import (
    build_login_evaluation_context,
    is_login_auth_strategy_enabled,
)
from services.security.login_device_trust_service import session_device_trust_from_profile_level
from services.security.security_env import (
    is_adaptive_auth_enabled,
    is_adaptive_block_high_risk_enabled,
    is_adaptive_email_fallback_enabled,
    is_adaptive_passkey_auto_enabled,
)

logger = logging.getLogger("arquantix.auth.adaptive_orchestrator")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AdaptiveAuthDecision:
    primary_method: str  # passkey | otp_sms | otp_email | password | blocked
    fallback_methods: List[str] = field(default_factory=list)
    auto_trigger_passkey: bool = False
    step_up_required: bool = False
    local_biometric_recommended: bool = False
    blocked: bool = False
    reason_codes: List[str] = field(default_factory=list)
    device_trust_level: str = "LOW"
    login_risk_score: int = 0
    fraud_score: Optional[float] = None  # hybrid login fraud / ML
    auth_strength_target: str = "otp"
    session_trust_target: str = "UNKNOWN"
    ui_variant: str = "standard"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def build_user_login_context(user: AdminUser) -> Dict[str, Any]:
    mob = getattr(user, "mobile_e164", None)
    em = getattr(user, "email", None)
    return {
        "has_mobile": bool(mob and str(mob).strip()),
        "has_email": bool(em and str(em).strip()),
        "mobile_e164": (str(mob).strip() if mob else None),
        "email": (str(em).strip().lower() if em else None),
    }


def build_device_context_from_eval_ctx(eval_ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "device_id": eval_ctx.get("device_id"),
        "device_hash": eval_ctx.get("device_hash"),
        "fingerprint_hash": eval_ctx.get("fingerprint_hash"),
        "ip": eval_ctx.get("ip"),
        "country": eval_ctx.get("country"),
        "attestation_trusted": bool(eval_ctx.get("attestation_trusted")),
    }


def build_risk_context_from_eval_ctx(eval_ctx: Dict[str, Any]) -> Dict[str, Any]:
    r = eval_ctx.get("risk") or {}
    return dict(r) if isinstance(r, dict) else {}


def build_fraud_context(
    db: Session,
    user_id: int,
    *,
    device_hash: Optional[str],
    ip: Optional[str],
) -> Dict[str, Any]:
    try:
        from services.security.ml.login_fraud_evaluator import (
            evaluate_login_fraud_risk,
            is_login_fraud_evaluation_enabled,
        )

        if not is_login_fraud_evaluation_enabled() or not device_hash:
            return {"skipped": True, "reason": "disabled_or_no_hash"}
        ev = evaluate_login_fraud_risk(db, user_id, device_hash=device_hash, ip=ip, session_id=None)
        return {
            "hybrid_score": ev.get("hybrid_score"),
            "ml_score": ev.get("ml_score"),
            "recommendation": ev.get("recommendation"),
            "pattern_signals": ev.get("pattern_signals") or [],
            "deterministic_block_eligible": ev.get("deterministic_block_eligible"),
            "heuristic_score": ev.get("heuristic_score"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("build_fraud_context failed user=%s: %s", user_id, exc)
        return {"skipped": True, "reason": "error"}


def build_passkey_context(
    db: Session,
    user: AdminUser,
    *,
    device_ctx: Dict[str, Any],
    risk_ctx: Dict[str, Any],
    step_up_required: bool,
) -> Dict[str, Any]:
    from services.auth.passkey_login_eligibility import evaluate_passkey_login_eligibility

    elig = evaluate_passkey_login_eligibility(
        db,
        user,
        device_context=device_ctx,
        risk_context=risk_ctx,
        step_up_required=step_up_required,
    )
    return {
        **elig.to_dict(),
        "device_id": device_ctx.get("device_id"),
        "device_hash": device_ctx.get("device_hash"),
    }


def build_attestation_context(*, attestation_trusted: bool) -> Dict[str, Any]:
    return {
        "trusted": bool(attestation_trusted),
        "trust_level": "TRUSTED" if attestation_trusted else "UNKNOWN",
    }


def orchestrate_login_strategy(
    db: Session,
    user: AdminUser,
    login_identifier: Dict[str, Any],
    *,
    device_context: Dict[str, Any],
    risk_context: Dict[str, Any],
    fraud_context: Dict[str, Any],
    passkey_context: Dict[str, Any],
    attestation_context: Dict[str, Any],
    user_login_context: Dict[str, Any],
    login_channel: str = "sms_start",
) -> AdaptiveAuthDecision:
    """
    Arbre de décision explicable. Les entrées sont supposées déjà construites par les builders.
    """
    reasons: List[str] = []
    uid = user.id
    dtl = str(risk_context.get("device_trust_level") or "LOW").upper()
    login_risk = int(risk_context.get("login_risk_score") or 0)
    hint = str(risk_context.get("decision_hint") or "otp_only")
    signals = risk_context.get("signals") or []
    if not isinstance(signals, list):
        signals = []

    fraud_hybrid: Optional[float] = None
    if isinstance(fraud_context.get("hybrid_score"), (int, float)):
        fraud_hybrid = float(fraud_context["hybrid_score"])

    # --- 1. Compte verrouillé
    lu = getattr(user, "security_account_locked_until", None)
    if lu is not None and lu > _utcnow():
        reasons.append("account_security_locked")
        return AdaptiveAuthDecision(
            primary_method="blocked",
            fallback_methods=[],
            blocked=True,
            reason_codes=reasons,
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="blocked",
            session_trust_target="BLOCKED",
            ui_variant="blocked",
        )

    # --- 2. Contexte risk bloqué (device blacklist / score absolu)
    if hint == "blocked" or "device_blacklisted" in signals:
        reasons.append("login_context_blocked")
        return AdaptiveAuthDecision(
            primary_method="blocked",
            fallback_methods=[],
            blocked=True,
            reason_codes=reasons + [f"decision_hint:{hint}"],
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="blocked",
            session_trust_target="BLOCKED",
            ui_variant="blocked",
        )

    # --- 3. Fraude critique (garde-fou : seulement si flag produit + signal déterministe)
    if is_adaptive_block_high_risk_enabled() and not fraud_context.get("skipped"):
        if (
            fraud_context.get("deterministic_block_eligible")
            and str(fraud_context.get("recommendation") or "") == "block"
        ):
            reasons.append("adaptive_fraud_block")
            return AdaptiveAuthDecision(
                primary_method="blocked",
                fallback_methods=[],
                blocked=True,
                reason_codes=reasons,
                device_trust_level=dtl,
                login_risk_score=login_risk,
                fraud_score=fraud_hybrid,
                auth_strength_target="blocked",
                session_trust_target="SUSPICIOUS",
                ui_variant="blocked",
            )

    ident_kind = str(login_identifier.get("kind") or "phone_e164")

    # --- Step-up de base (aligné login_context_risk + fraude)
    step_up = hint == "otp_step_up" or login_risk >= 52
    if not fraud_context.get("skipped"):
        if str(fraud_context.get("recommendation") or "") in ("step_up", "review"):
            hs = int(fraud_context.get("heuristic_score") or 0)
            if hs >= 35 or (fraud_hybrid is not None and fraud_hybrid >= 55):
                step_up = True
                reasons.append("fraud_recommendation_step_up")

    # --- Session refresh : ne pas forcer une méthode primaire métier
    if login_channel == "session_refresh":
        st = session_device_trust_from_profile_level(dtl)
        if step_up:
            reasons.append("session_refresh_step_up")
        bio = dtl == "HIGH" and not step_up
        variant = "cautious" if step_up else "standard"
        return AdaptiveAuthDecision(
            primary_method="otp_sms",
            fallback_methods=["otp_email", "password"] if is_adaptive_email_fallback_enabled() else ["password"],
            auto_trigger_passkey=False,
            step_up_required=step_up,
            local_biometric_recommended=bio,
            blocked=False,
            reason_codes=reasons + [f"channel:{login_channel}"],
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="otp" if step_up else "password",
            session_trust_target=st,
            ui_variant=variant,
        )

    # --- Canal e-mail OTP
    if login_channel == "email_otp_start" or ident_kind == "email":
        if not user_login_context.get("has_email"):
            reasons.append("no_email_on_account")
            return AdaptiveAuthDecision(
                primary_method="blocked",
                fallback_methods=[],
                blocked=True,
                reason_codes=reasons,
                device_trust_level=dtl,
                login_risk_score=login_risk,
                fraud_score=fraud_hybrid,
                auth_strength_target="blocked",
                session_trust_target="UNKNOWN",
                ui_variant="blocked",
            )
        fb: List[str] = []
        if user_login_context.get("has_mobile"):
            fb.append("otp_sms")
        if is_adaptive_email_fallback_enabled():
            fb.append("password")
        variant = "cautious" if step_up else "standard"
        return AdaptiveAuthDecision(
            primary_method="otp_email",
            fallback_methods=fb,
            auto_trigger_passkey=False,
            step_up_required=step_up,
            local_biometric_recommended=dtl == "HIGH" and not step_up,
            blocked=False,
            reason_codes=reasons + [f"channel:{login_channel}"],
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="otp",
            session_trust_target=session_device_trust_from_profile_level(dtl),
            ui_variant=variant,
        )

    # --- Aucun mobile pour parcours téléphone
    if login_channel == "sms_start" and not user_login_context.get("has_mobile"):
        reasons.append("no_mobile_on_account")
        if user_login_context.get("has_email") and is_adaptive_email_fallback_enabled():
            return AdaptiveAuthDecision(
                primary_method="otp_email",
                fallback_methods=["password"],
                auto_trigger_passkey=False,
                step_up_required=True,
                local_biometric_recommended=False,
                blocked=False,
                reason_codes=reasons + ["redirect_email_otp"],
                device_trust_level=dtl,
                login_risk_score=login_risk,
                fraud_score=fraud_hybrid,
                auth_strength_target="otp",
                session_trust_target=session_device_trust_from_profile_level(dtl),
                ui_variant="cautious",
            )
        return AdaptiveAuthDecision(
            primary_method="blocked",
            fallback_methods=[],
            blocked=True,
            reason_codes=reasons,
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="blocked",
            session_trust_target="UNKNOWN",
            ui_variant="blocked",
        )

    # --- Fast lane passkey
    pk_ok = bool(passkey_context.get("recommended")) and is_adaptive_passkey_auto_enabled()
    if (
        pk_ok
        and dtl == "HIGH"
        and hint == "passkey_preferred"
        and not step_up
        and login_channel in ("sms_start", "passkey_start", "orchestrate")
    ):
        reasons.append("adaptive_fast_lane_passkey")
        return AdaptiveAuthDecision(
            primary_method="passkey",
            fallback_methods=["otp_sms", "otp_email"] if is_adaptive_email_fallback_enabled() else ["otp_sms"],
            auto_trigger_passkey=True,
            step_up_required=False,
            local_biometric_recommended=True,
            blocked=False,
            reason_codes=reasons,
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="passkey",
            session_trust_target="TRUSTED",
            ui_variant="fast_lane",
        )

    # --- Device LOW / risque modéré → OTP SMS + step-up possible, pas d’auto passkey
    if dtl == "LOW" or step_up or login_risk >= 58:
        reasons.append("cautious_otp_path")
        fb = ["otp_email", "password"] if is_adaptive_email_fallback_enabled() else ["password"]
        if passkey_context.get("eligible") and not passkey_context.get("recommended"):
            fb = ["passkey"] + fb
        return AdaptiveAuthDecision(
            primary_method="otp_sms",
            fallback_methods=fb,
            auto_trigger_passkey=False,
            step_up_required=step_up or dtl == "LOW",
            local_biometric_recommended=False,
            blocked=False,
            reason_codes=reasons,
            device_trust_level=dtl,
            login_risk_score=login_risk,
            fraud_score=fraud_hybrid,
            auth_strength_target="otp",
            session_trust_target=session_device_trust_from_profile_level(dtl),
            ui_variant="cautious",
        )

    # --- Standard : OTP SMS, passkey manuel possible
    reasons.append("standard_otp_primary")
    fb2: List[str] = ["passkey", "otp_email", "password"] if is_adaptive_email_fallback_enabled() else ["passkey", "password"]
    return AdaptiveAuthDecision(
        primary_method="otp_sms",
        fallback_methods=fb2,
        auto_trigger_passkey=False,
        step_up_required=False,
        local_biometric_recommended=dtl == "HIGH",
        blocked=False,
        reason_codes=reasons,
        device_trust_level=dtl,
        login_risk_score=login_risk,
        fraud_score=fraud_hybrid,
        auth_strength_target="otp",
        session_trust_target=session_device_trust_from_profile_level(dtl),
        ui_variant="standard",
    )


def orchestrate_login_strategy_from_request(
    db: Session,
    request: Request,
    user: AdminUser,
    *,
    device_header: Optional[str],
    login_identifier: Dict[str, Any],
    login_channel: str = "sms_start",
    attestation_trusted: bool = False,
    eval_ctx: Optional[Dict[str, Any]] = None,
) -> Tuple[AdaptiveAuthDecision, Dict[str, Any]]:
    eval_ctx = eval_ctx or build_login_evaluation_context(
        db,
        request,
        user,
        device_header=device_header,
        attestation_trusted=attestation_trusted,
    )
    device_ctx = build_device_context_from_eval_ctx(eval_ctx)
    risk_ctx = build_risk_context_from_eval_ctx(eval_ctx)
    fraud_ctx = build_fraud_context(
        db,
        user.id,
        device_hash=device_ctx.get("device_hash"),
        ip=device_ctx.get("ip"),
    )
    step_up_pre = str(risk_ctx.get("decision_hint") or "") == "otp_step_up" or int(risk_ctx.get("login_risk_score") or 0) >= 52
    pass_ctx = build_passkey_context(
        db,
        user,
        device_ctx=device_ctx,
        risk_ctx=risk_ctx,
        step_up_required=step_up_pre,
    )
    attest_ctx = build_attestation_context(attestation_trusted=attestation_trusted)
    user_ctx = build_user_login_context(user)
    _ = attest_ctx  # réservé extensions (policy ZT)
    decision = orchestrate_login_strategy(
        db,
        user,
        login_identifier,
        device_context=device_ctx,
        risk_context=risk_ctx,
        fraud_context=fraud_ctx,
        passkey_context=pass_ctx,
        attestation_context=attest_ctx,
        user_login_context=user_ctx,
        login_channel=login_channel,
    )
    return decision, eval_ctx


def persist_adaptive_auth_decision(
    db: Session,
    *,
    user_id: Optional[int],
    device_id: str,
    decision: AdaptiveAuthDecision,
    login_channel: str,
    persist_decision_row: bool = True,
) -> None:
    if not is_security_events_enabled():
        return
    meta = decision.to_dict()
    meta["login_channel"] = login_channel
    try:
        persist_auth_security_event(
            user_id=user_id,
            device_id=(device_id or "")[:128] or "unknown",
            event_type="auth.login.orchestrated",
            ip_address=None,
            user_agent=None,
            metadata=meta,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("auth.login.orchestrated persist failed: %s", exc)

    if not persist_decision_row or user_id is None:
        return
    try:
        snap = json.loads(json.dumps(meta, default=str))
    except Exception:  # noqa: BLE001
        snap = meta
    row = AuthSecurityDecision(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=None,
        device_id=(device_id or "")[:128] or None,
        action="auth.login.orchestrated",
        resource="auth:adaptive_orchestrator",
        allow=not decision.blocked,
        require_step_up=decision.step_up_required,
        deny_reason=("blocked" if decision.blocked else None),
        policy_id="adaptive_auth.v1",
        context_snapshot_json=snap,
    )
    try:
        db.add(row)
        db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("adaptive auth_security_decision persist failed: %s", exc)


def adaptive_decision_to_legacy_strategy(
    decision: AdaptiveAuthDecision,
    *,
    eval_ctx: Dict[str, Any],
    login_channel: str,
):
    """Convertit vers ``LoginAuthStrategyResult`` (compat routes existantes)."""
    from services.security.login_auth_strategy_service import LoginAuthStrategyResult

    if login_channel == "session_refresh":
        primary = "otp"
    else:
        primary = "passkey" if decision.primary_method == "passkey" else "otp"

    ctx_out = dict(eval_ctx)
    ctx_out["adaptive_decision"] = decision.to_dict()

    return LoginAuthStrategyResult(
        primary_method=primary,
        step_up_required=decision.step_up_required,
        blocked=decision.blocked,
        reason_codes=list(decision.reason_codes)[:48],
        device_trust_level=decision.device_trust_level,
        session_trust_flag=decision.session_trust_target,
        context=ctx_out,
    )

