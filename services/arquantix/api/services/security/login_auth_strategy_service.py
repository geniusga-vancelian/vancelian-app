"""
Décision d’auth login : **orchestre** profil device, risque contextuel, réputation, passkeys.

Ne recalcule pas le score SIEM : lit ``auth_global_risk_score`` et réutilise
``evaluate_login_context_risk``.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from database import AdminUser, AuthSecurityDecision
from services.auth.device_fingerprint import is_device_fingerprint_enabled, parse_device_fingerprint_header
from services.auth.refresh_session import normalize_device_id
from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event
from services.security.device_reputation.device_reputation_service import (
    is_device_reputation_enabled,
    resolve_device_hash_from_request,
)
from services.security.login_context_risk import evaluate_login_context_risk
from services.security.login_device_trust_service import (
    is_login_device_trust_enabled,
    session_device_trust_from_profile_level,
)
from services.security.security_env import (
    is_login_auth_strategy_enabled,
    is_login_strategy_persist_decisions_enabled,
)

logger = logging.getLogger("arquantix.security.login_auth_strategy")


@dataclass(frozen=True)
class LoginAuthStrategyResult:
    primary_method: str  # "otp" | "passkey"
    step_up_required: bool
    blocked: bool
    reason_codes: List[str]
    device_trust_level: str  # HIGH|MEDIUM|LOW (profil)
    session_trust_flag: str  # TRUSTED|UNKNOWN|SUSPICIOUS
    context: Dict[str, Any]


def _country_from_request(request: Request) -> Optional[str]:
    for h in ("cf-ipcountry", "CF-IPCountry", "x-geo-country", "X-Geo-Country"):
        v = request.headers.get(h)
        if v and str(v).strip():
            return str(v).strip()[:8]
    return None


def _fingerprint_from_request(request: Request):
    raw = request.headers.get("x-device-fingerprint")
    return parse_device_fingerprint_header(raw)


def build_login_evaluation_context(
    db: Session,
    request: Request,
    user: AdminUser,
    *,
    device_header: Optional[str],
    attestation_trusted: bool = False,
) -> Dict[str, Any]:
    device_id = normalize_device_id(device_header)
    fp_meta, fp_hash = _fingerprint_from_request(request)
    if not is_device_fingerprint_enabled():
        fp_hash = None
    device_hash = resolve_device_hash_from_request(request, device_id, fp_hash)
    ip = request.client.host if request.client else None
    country = _country_from_request(request)
    return {
        "device_id": device_id,
        "fingerprint_hash": fp_hash,
        "fingerprint_meta": fp_meta,
        "device_hash": device_hash,
        "ip": ip,
        "country": country,
        "attestation_trusted": attestation_trusted,
        "risk": evaluate_login_context_risk(
            db,
            user,
            device_hash=device_hash,
            device_id_normalized=device_id,
            fingerprint_hash=fp_hash,
            ip_address=ip,
            country_code=country,
            attestation_trusted=attestation_trusted,
        ),
    }


def decide_login_auth_strategy(
    db: Session,
    request: Request,
    user: AdminUser,
    *,
    device_header: Optional[str],
    attestation_trusted: bool = False,
    login_channel: str = "sms_start",
    login_identifier: Optional[Dict[str, Any]] = None,
) -> LoginAuthStrategyResult:
    """
    Décision structurée + codes explicites (pas de boîte noire).

    ``primary_method`` : recommandation UX ; l’API peut toujours offrir plusieurs chemins.
    """
    if not is_login_auth_strategy_enabled():
        return LoginAuthStrategyResult(
            primary_method="otp",
            step_up_required=False,
            blocked=False,
            reason_codes=["strategy_disabled"],
            device_trust_level="MEDIUM",
            session_trust_flag=session_device_trust_from_profile_level("MEDIUM"),
            context={},
        )

    try:
        from services.auth.adaptive_auth_orchestrator import (
            adaptive_decision_to_legacy_strategy,
            is_adaptive_auth_enabled,
            orchestrate_login_strategy_from_request,
            persist_adaptive_auth_decision,
        )

        if is_adaptive_auth_enabled():
            ident = login_identifier
            if ident is None:
                mob = getattr(user, "mobile_e164", None)
                em = getattr(user, "email", None)
                if login_channel == "email_otp_start" and em:
                    ident = {"kind": "email", "value": str(em).strip().lower()}
                else:
                    ident = {"kind": "phone_e164", "value": str(mob or "").strip()}
            decision, eval_ctx = orchestrate_login_strategy_from_request(
                db,
                request,
                user,
                device_header=device_header,
                login_identifier=ident,
                login_channel=login_channel,
                attestation_trusted=attestation_trusted,
            )
            persist_adaptive_auth_decision(
                db,
                user_id=user.id,
                device_id=normalize_device_id(device_header),
                decision=decision,
                login_channel=login_channel,
            )
            return adaptive_decision_to_legacy_strategy(
                decision,
                eval_ctx=eval_ctx,
                login_channel=login_channel,
            )
    except Exception as exc:  # noqa: BLE001 — repli sur héritage
        logger.warning("adaptive auth orchestrator fallback: %s", exc)

    ctx = build_login_evaluation_context(
        db,
        request,
        user,
        device_header=device_header,
        attestation_trusted=attestation_trusted,
    )
    r = ctx["risk"]
    hint = r["decision_hint"]
    reason_codes: List[str] = list(r.get("signals") or [])
    reason_codes.append(f"decision_hint:{hint}")

    blocked = hint == "blocked"
    step_up = hint == "otp_step_up" or r["login_risk_score"] >= 52

    primary = "otp"
    if hint == "passkey_preferred" and r.get("user_has_passkeys"):
        primary = "passkey"
        reason_codes.append("primary_passkey_preferred")

    if blocked:
        primary = "otp"
        step_up = True
        reason_codes.append("login_blocked_by_policy")

    dtl = str(r.get("device_trust_level") or "LOW")
    session_flag = session_device_trust_from_profile_level(dtl)

    return LoginAuthStrategyResult(
        primary_method=primary,
        step_up_required=bool(step_up) and not blocked,
        blocked=blocked,
        reason_codes=reason_codes,
        device_trust_level=dtl,
        session_trust_flag=session_flag,
        context={k: v for k, v in ctx.items() if k != "fingerprint_meta"},
    )


def persist_login_strategy_decision(
    db: Session,
    *,
    user_id: int,
    device_id: Optional[str],
    strategy: LoginAuthStrategyResult,
    action: str,
) -> Optional[AuthSecurityDecision]:
    """Persiste dans ``auth_security_decisions`` (audit login), sans passer par RequestSecurityContext."""
    if not is_login_strategy_persist_decisions_enabled():
        return None
    snap = {
        "primary_method": strategy.primary_method,
        "step_up_required": strategy.step_up_required,
        "blocked": strategy.blocked,
        "reason_codes": strategy.reason_codes[:48],
        "device_trust_level": strategy.device_trust_level,
        "session_trust_flag": strategy.session_trust_flag,
        "risk": strategy.context.get("risk") if strategy.context else None,
    }
    try:
        snap_json = json.loads(json.dumps(snap, default=str))
    except Exception:  # noqa: BLE001
        snap_json = snap

    row = AuthSecurityDecision(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=None,
        device_id=(device_id or "")[:128] or None,
        action=action[:256],
        resource="auth:login:strategy",
        allow=not strategy.blocked,
        require_step_up=strategy.step_up_required,
        deny_reason=("blocked" if strategy.blocked else None),
        policy_id="login.auth_strategy.v1",
        context_snapshot_json=snap_json,
    )
    db.add(row)
    try:
        db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("login strategy decision persist failed: %s", exc)
        return None
    if is_security_events_enabled():
        try:
            persist_auth_security_event(
                user_id=user_id,
                device_id=(device_id or "")[:128] or "unknown",
                event_type="auth.login.strategy_evaluated",
                ip_address=None,
                user_agent=None,
                metadata={
                    "action": action,
                    "allow": not strategy.blocked,
                    "require_step_up": strategy.step_up_required,
                    "primary_method": strategy.primary_method,
                    "reason_codes": strategy.reason_codes[:24],
                },
                db=db,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("login strategy security event skipped: %s", exc)
    return row


def enforce_login_strategy_or_raise(
    db: Session,
    request: Request,
    user: AdminUser,
    *,
    device_header: Optional[str],
    attestation_trusted: bool = False,
    persist_action: str = "auth.login.strategy_evaluated",
    login_channel: str = "session_refresh",
    login_identifier: Optional[Dict[str, Any]] = None,
) -> LoginAuthStrategyResult:
    """
    Applique la stratégie : lève 403 si ``blocked``.

    Retourne le résultat pour enrichir session / métadonnées.
    """
    if not is_login_auth_strategy_enabled():
        return LoginAuthStrategyResult(
            primary_method="otp",
            step_up_required=False,
            blocked=False,
            reason_codes=["strategy_disabled"],
            device_trust_level="MEDIUM",
            session_trust_flag=session_device_trust_from_profile_level("MEDIUM"),
            context={},
        )

    strat = decide_login_auth_strategy(
        db,
        request,
        user,
        device_header=device_header,
        attestation_trusted=attestation_trusted,
        login_channel=login_channel,
        login_identifier=login_identifier,
    )
    persist_login_strategy_decision(
        db,
        user_id=user.id,
        device_id=normalize_device_id(device_header),
        strategy=strat,
        action=persist_action,
    )
    if strat.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LOGIN_CONTEXT_BLOCKED",
                "message": "Connexion refusée pour ce contexte appareil (politique de sécurité).",
                "reason_codes": strat.reason_codes[:20],
            },
        )
    return strat


def merge_step_up_flags(a: bool, b: bool) -> bool:
    return bool(a or b)


_TRUST_STRICTNESS = {"TRUSTED": 0, "UNKNOWN": 1, "SUSPICIOUS": 2, "BLOCKED": 3}


def merge_device_trust_for_session(caller_level: str, strategy_level: str) -> str:
    """Garde le niveau le plus strict (moins favorable) entre appelant et stratégie login."""
    rc = _TRUST_STRICTNESS.get((caller_level or "UNKNOWN").upper(), 1)
    rs = _TRUST_STRICTNESS.get((strategy_level or "UNKNOWN").upper(), 1)
    worst = max(rc, rs)
    for name, rank in _TRUST_STRICTNESS.items():
        if rank == worst:
            return name
    return caller_level or "UNKNOWN"
