"""PR D4 — score de risque actions sensibles (step-up, révocation sessions si seuil extrême)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import AuthDeviceCredential, AuthUserDeviceProfile
from services.auth.device_pr_d4_policy import (
    device_risk_revoke_all_sessions_threshold,
    device_risk_step_up_score_threshold,
)
from services.auth.device_sensitive_action_velocity import get_sensitive_action_count
from services.auth.device_signature_failure_rl import get_signature_failure_count

logger = logging.getLogger("arquantix.auth.device_risk_d4")

_STRONG_ATTEST = frozenset({"HIGH", "TIER1", "STRONG", "ATTESTED"})


def _client_ip(request: Request) -> Optional[str]:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()[:45]
    if request.client:
        return (request.client.host or "")[:45] or None
    return None


def _country_hint(request: Request) -> Optional[str]:
    v = (
        request.headers.get("cf-ipcountry")
        or request.headers.get("CF-IPCountry")
        or request.headers.get("x-country-code")
        or ""
    )
    v = str(v).strip().upper()
    return v[:8] if v else None


def evaluate_sensitive_route_risk(
    db: Session,
    *,
    user_id: int,
    device_id: str,
    request: Request,
) -> Tuple[int, bool, bool]:
    """
    Retourne ``(score 0–100, step_up_requis, révoquer_toutes_sessions)``.

    * step_up : score >= ``DEVICE_RISK_SENSITIVE_STEP_UP_SCORE`` et pas de révocation globale.
    * révocation : score >= ``DEVICE_RISK_REVOKE_ALL_SESSIONS_THRESHOLD`` si ce seuil est défini.
    """
    score = 0
    cred = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == user_id,
            AuthDeviceCredential.device_id == device_id,
            AuthDeviceCredential.revoked_at.is_(None),
        )
        .first()
    )
    if cred is None:
        score += 45
    else:
        al = (cred.attestation_level or "").strip().upper()
        if not al:
            score += 15
        elif al not in _STRONG_ATTEST:
            score += 28

    rl_key = f"{user_id}:{device_id}"
    fails = get_signature_failure_count(rl_key)
    score += min(40, fails * 12)

    ip = _client_ip(request)
    country = _country_hint(request)
    prof = (
        db.query(AuthUserDeviceProfile)
        .filter(
            AuthUserDeviceProfile.user_id == user_id,
            AuthUserDeviceProfile.device_id == device_id,
        )
        .first()
    )
    if prof:
        if ip and prof.last_ip and ip != prof.last_ip:
            score += 14
        if country and prof.last_country and country != (prof.last_country or "").strip().upper():
            score += 20
    else:
        score += 5

    vel = get_sensitive_action_count(user_id, device_id)
    if vel > 3:
        score += min(25, (vel - 3) * 5)

    now = datetime.now(timezone.utc)
    recent = now - timedelta(hours=24)
    churn = (
        db.query(func.count(AuthDeviceCredential.id))
        .filter(
            AuthDeviceCredential.user_id == user_id,
            AuthDeviceCredential.created_at >= recent,
        )
        .scalar()
    ) or 0
    if churn > 4:
        score += min(15, (churn - 4) * 3)

    score = min(100, score)
    revoke_thr = device_risk_revoke_all_sessions_threshold()
    step_thr = device_risk_step_up_score_threshold()

    session_revoke = revoke_thr is not None and score >= revoke_thr
    step_up = (not session_revoke) and score >= step_thr

    if session_revoke:
        logger.warning(
            "device_risk_revoke_all_sessions user=%s device=%s score=%s threshold=%s",
            user_id,
            device_id[:12],
            score,
            revoke_thr,
        )
    elif step_up:
        logger.info(
            "device_risk_step_up user=%s device=%s score=%s threshold=%s",
            user_id,
            device_id[:12],
            score,
            step_thr,
        )
    return score, step_up, session_revoke
