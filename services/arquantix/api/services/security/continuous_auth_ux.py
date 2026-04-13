"""
Couche UX pour l’auth continue (Phase 5A) — messages et tonalité, sans impact sur les décisions.

Les règles de sécurité restent dans ``continuous_auth_engine`` ; ce module ne fait qu’enrichir
les réponses HTTP avec des champs lisibles pour le client.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Priorité pour un seul message utilisateur quand plusieurs reason_codes sont présents.
_REASON_PRIORITY: List[str] = [
    "reauth_required",
    "behavioral_force_reauth",
    "behavioral_force_step_up",
    "risk_engine_reauth",
    "risk_engine_step_up",
    "device_not_trusted",
    "recent_auth_required",
    "policy_requires_step_up",
    "step_up_required",
    "biometric_recommended",
]


def _ux_context_for_action(action_key: str) -> str:
    k = (action_key or "").strip().lower()
    if k in (
        "withdrawal",
        "wallet_transfer",
        "internal_transfer_low",
        "beneficiary_add",
    ):
        return "withdrawal"
    if k in (
        "security_settings_change",
        "api_key_create",
        "passcode_reset",
        "biometric_disable",
        "contact_change",
        "change_password",
        "session_revoke_all",
    ):
        return "security_change"
    # view_sensitive_data, view_portfolio, data_export, défaut
    return "data_access"


def _pick_primary_reason(reason_codes: List[str]) -> Optional[str]:
    codes = {str(c).strip() for c in (reason_codes or []) if c}
    for p in _REASON_PRIORITY:
        if p in codes:
            return p
    # Codes hors liste (ex. continuous_auth_disabled) — pas d’écran d’erreur step-up en pratique
    for c in codes:
        if c not in ("ok", "continuous_auth_disabled", "no_session_intelligence"):
            return c
    return None


def _message_tone_label(
    primary: Optional[str],
    ux_context: str,
    reason_codes: List[str],
) -> Tuple[str, str, str]:
    """Retourne (message, ux_tone, ux_action_label)."""
    rc = {str(c).strip() for c in (reason_codes or [])}

    if primary == "reauth_required":
        return (
            "Votre session a expiré. Reconnectez-vous pour continuer.",
            "critical",
            "Se reconnecter",
        )

    if primary == "device_not_trusted":
        return (
            "Nouvel appareil détecté. Vérifions qu’il s’agit bien de vous.",
            "warning",
            "Continuer",
        )

    if primary == "recent_auth_required":
        if ux_context == "withdrawal":
            return (
                "Pour votre sécurité, confirmez ce transfert.",
                "soft",
                "Confirmer",
            )
        if ux_context == "security_change":
            return (
                "Confirmez votre identité pour modifier ce paramètre sensible.",
                "soft",
                "Confirmer",
            )
        return (
            "Confirmez votre identité pour accéder à ces informations.",
            "soft",
            "Confirmer",
        )

    if primary in ("policy_requires_step_up", "step_up_required"):
        if ux_context == "withdrawal":
            return (
                "Pour votre sécurité, une vérification supplémentaire est nécessaire pour cette opération.",
                "warning",
                "Continuer",
            )
        if ux_context == "security_change":
            return (
                "Une étape de sécurité est requise avant de poursuivre.",
                "warning",
                "Continuer",
            )
        return (
            "Une vérification supplémentaire est nécessaire pour accéder à ces données.",
            "warning",
            "Continuer",
        )

    if primary == "biometric_recommended":
        return (
            "Vérifiez votre identité (code ou biométrie) pour continuer.",
            "soft",
            "Continuer",
        )

    # Inconnu ou liste vide — fallback non technique
    if rc and not rc.issubset({"ok", "continuous_auth_disabled", "no_session_intelligence"}):
        return (
            "Une vérification de sécurité est requise.",
            "warning",
            "Continuer",
        )

    return (
        "Une vérification de sécurité est requise.",
        "warning",
        "Continuer",
    )


def build_continuous_auth_ux_fields(
    *,
    reason_codes: List[str],
    action_key: str,
    risk_level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Champs UX pour ``detail`` HTTP (401/403). Déterministes, courts, non techniques.

    - ux_tone: soft | warning | critical
    - ux_context: withdrawal | data_access | security_change
    """
    ctx = _ux_context_for_action(action_key)
    primary = _pick_primary_reason(reason_codes)
    msg, tone, label = _message_tone_label(primary, ctx, reason_codes)
    out = {
        "ux_message": msg,
        "ux_tone": tone,
        "ux_action_label": label,
        "ux_context": ctx,
    }
    rl = (risk_level or "").strip().lower()
    if rl == "critical":
        out["ux_tone"] = "critical"
    elif rl == "high" and out["ux_tone"] == "soft":
        out["ux_tone"] = "warning"
    return out
