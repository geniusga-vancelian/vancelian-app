"""
Évaluation du risque **login** (contexte device + utilisateur), distincte du score SIEM global
mais **alimentée** par les mêmes sources (réputation device, profil utilisateur-device, risque global).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database import AdminUser, AuthGlobalRiskScore, AuthPasskey
from services.security.device_reputation.device_reputation_service import (
    is_device_blacklisted,
    is_device_reputation_enabled,
)
from services.security.login_device_trust_service import (
    build_trust_input_for_profile,
    compute_device_trust_level,
    compute_device_trust_score,
    is_login_device_trust_enabled,
    resolve_user_device_profile,
    snapshot_profile_for_audit,
)


def _abs_block_threshold() -> int:
    try:
        return max(70, min(100, int(os.getenv("LOGIN_CONTEXT_BLOCK_MIN_SCORE", "96"))))
    except ValueError:
        return 96


def _user_has_passkeys(db: Session, user_id: int) -> bool:
    n = (
        db.query(AuthPasskey)
        .filter(AuthPasskey.user_id == user_id, AuthPasskey.revoked_at.is_(None))
        .count()
    )
    return n > 0


def _stored_global_risk(db: Session, user_id: int) -> Tuple[int, str]:
    row = db.query(AuthGlobalRiskScore).filter(AuthGlobalRiskScore.user_id == user_id).first()
    if row is None:
        return 0, "LOW"
    return int(row.score or 0), str(row.level or "LOW")


def evaluate_login_context_risk(
    db: Session,
    user: AdminUser,
    *,
    device_hash: str,
    device_id_normalized: str,
    fingerprint_hash: Optional[str],
    ip_address: Optional[str],
    country_code: Optional[str],
    attestation_trusted: bool,
) -> Dict[str, Any]:
    """
    Retourne un dict JSON-safe avec scores, signaux et **decision_hint** explicable.

    - ``device_trust_score`` / ``device_trust_level`` : profil utilisateur-device + réputation.
    - ``login_risk_score`` 0–100 (**plus haut = plus risqué**), combinaison explicite.
    - ``decision_hint`` : otp_only | otp_step_up | passkey_preferred | blocked
    """
    signals: List[str] = []

    profile = None
    if is_login_device_trust_enabled():
        profile = resolve_user_device_profile(db, user.id, device_hash)

    inp = build_trust_input_for_profile(
        db,
        profile,
        current_fingerprint_hash=fingerprint_hash,
        current_country=country_code,
        attestation_trusted=attestation_trusted,
        device_hash=device_hash,
    )
    if not inp.fingerprint_stable:
        signals.append("fingerprint_changed_or_missing_vs_profile")
    if not inp.ip_country_stable:
        signals.append("country_changed_vs_profile")
    if profile is None:
        signals.append("new_user_device_profile")

    device_trust_score = compute_device_trust_score(inp)
    device_trust_level = compute_device_trust_level(device_trust_score)

    global_score, global_level = _stored_global_risk(db, user.id)

    login_risk_score = max(0, min(100, 100 - device_trust_score))
    login_risk_score = max(login_risk_score, int(global_score * 0.45))
    if global_level in ("HIGH", "CRITICAL"):
        signals.append("global_user_risk_elevated")
        login_risk_score = min(100, login_risk_score + 12)
    if global_level == "CRITICAL":
        login_risk_score = min(100, login_risk_score + 10)

    blacklisted = False
    if is_device_reputation_enabled():
        blacklisted = is_device_blacklisted(db, device_hash)
        if blacklisted:
            signals.append("device_blacklisted")
            login_risk_score = 100

    has_pk = _user_has_passkeys(db, user.id)
    if has_pk and device_trust_level == "LOW":
        signals.append("passkey_available_low_device_trust")

    decision_hint = "otp_only"
    if blacklisted or login_risk_score >= _abs_block_threshold():
        decision_hint = "blocked"
    elif has_pk and (device_trust_level != "HIGH" or "new_user_device_profile" in signals):
        decision_hint = "passkey_preferred"
    elif (
        device_trust_level == "LOW"
        or "fingerprint_changed_or_missing_vs_profile" in signals
        or login_risk_score >= 58
    ):
        decision_hint = "otp_step_up"

    return {
        "device_trust_score": device_trust_score,
        "device_trust_level": device_trust_level,
        "login_risk_score": login_risk_score,
        "signals": signals,
        "decision_hint": decision_hint,
        "global_risk_score": global_score,
        "global_risk_level": global_level,
        "profile_snapshot": snapshot_profile_for_audit(profile),
        "user_has_passkeys": has_pk,
    }
