"""
Éligibilité **auto-trigger passkey** (fast lane) — distinct de la stratégie session complète.

Règles explicites : device **HIGH** trust, risque modéré, passkey enregistrée, pas de step-up forcé.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database import AdminUser, AuthPasskey, Person
from services.auth.account_policy import is_web_only_mobile_app_user
from services.auth.webauthn_config import is_passkeys_enabled
from services.security.security_env import (
    is_passkey_auto_expose_login_email_enabled,
    is_passkey_auto_trigger_enabled,
    passkey_auto_max_login_risk,
)


@dataclass
class PasskeyLoginEligibilityResult:
    eligible: bool
    recommended: bool
    reason_codes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eligible": self.eligible,
            "recommended": self.recommended,
            "reason_codes": list(self.reason_codes),
        }


def _user_has_active_passkey(db: Session, user_id: int) -> bool:
    n = (
        db.query(AuthPasskey)
        .filter(AuthPasskey.user_id == user_id, AuthPasskey.revoked_at.is_(None))
        .count()
    )
    return n > 0


def evaluate_passkey_login_eligibility(
    db: Session,
    user: AdminUser,
    *,
    device_context: Dict[str, Any],
    risk_context: Dict[str, Any],
    step_up_required: bool,
) -> PasskeyLoginEligibilityResult:
    """
    :param device_context: ex. ``device_id``, ``device_hash`` (audit / extensions futures).
    :param risk_context: sortie de ``evaluate_login_context_risk`` (scores, niveaux, signaux).
    :param step_up_required: fusion réputation + stratégie login (bool).
    """
    reasons: List[str] = []
    if is_web_only_mobile_app_user(user):
        reasons.append("web_admin_only_account")
        return PasskeyLoginEligibilityResult(False, False, reasons)

    if user.person_id is not None:
        pers = db.get(Person, user.person_id)
        if pers is not None and getattr(pers, "login_frozen", False):
            reasons.append("login_frozen")
            return PasskeyLoginEligibilityResult(False, False, reasons)

    if not is_passkey_auto_trigger_enabled():
        reasons.append("passkey_auto_disabled")
        return PasskeyLoginEligibilityResult(False, False, reasons)

    if not is_passkeys_enabled():
        reasons.append("passkeys_feature_disabled")
        return PasskeyLoginEligibilityResult(False, False, reasons)

    if not _user_has_active_passkey(db, user.id):
        reasons.append("no_active_passkey")
        return PasskeyLoginEligibilityResult(False, False, reasons)

    reasons.append("has_active_passkey")
    eligible = True

    hint = str(risk_context.get("decision_hint") or "")
    if hint == "blocked":
        reasons.append("login_context_blocked")
        return PasskeyLoginEligibilityResult(True, False, reasons)

    if step_up_required:
        reasons.append("step_up_required_incompatible")
        return PasskeyLoginEligibilityResult(eligible, False, reasons)

    dtl = str(risk_context.get("device_trust_level") or "LOW").upper()
    if dtl != "HIGH":
        reasons.append(f"device_trust_not_high:{dtl}")
        return PasskeyLoginEligibilityResult(eligible, False, reasons)

    login_risk = int(risk_context.get("login_risk_score") or 0)
    if login_risk > _max_login_risk_for_auto_passkey():
        reasons.append(f"login_risk_above_threshold:{login_risk}")
        return PasskeyLoginEligibilityResult(eligible, False, reasons)

    gl = str(risk_context.get("global_risk_level") or "LOW").upper()
    if gl == "CRITICAL":
        reasons.append("global_risk_critical")
        return PasskeyLoginEligibilityResult(eligible, False, reasons)

    # Signaux explicites qui contredisent une auto-ouverture silencieuse
    signals = risk_context.get("signals") or []
    if isinstance(signals, list):
        if "fingerprint_changed_or_missing_vs_profile" in signals:
            reasons.append("fingerprint_unstable")
            return PasskeyLoginEligibilityResult(eligible, False, reasons)
        if "device_blacklisted" in signals:
            reasons.append("device_blacklisted_signal")
            return PasskeyLoginEligibilityResult(eligible, False, reasons)

    reasons.append("passkey_auto_recommended")
    return PasskeyLoginEligibilityResult(eligible, True, reasons)


def should_expose_passkey_email_for_auto() -> bool:
    """Exposer l’e-mail de connexion passkey dans la réponse SMS start (même contrôle que l’envoi SMS)."""
    return is_passkey_auto_expose_login_email_enabled()
