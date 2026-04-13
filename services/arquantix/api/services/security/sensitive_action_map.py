"""
Cartographie des actions sensibles → politique d’auth continue (sans stack parallèle).

Utilisé par ``continuous_auth_engine`` et ``require_continuous_auth_for_action``.
Les clés sont stables (audit, Depends, événements SIEM).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Literal, Optional

SecurityTier = Literal["high", "medium", "low"]


class AuthLevel(str, Enum):
    """Niveau de sensibilité produit (LOW / MEDIUM / HIGH)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class SensitiveActionPolicy:
    """Politique par action — source de vérité pour la couche continuous auth."""

    action_key: str
    required_auth_level: AuthLevel
    requires_step_up: bool
    """Si True : exige toujours une étape OTP/passkey (en plus des règles risque)."""
    requires_recent_auth_seconds: Optional[int]
    """Fenêtre « step-up récent » ; None = ne pas appliquer ce critère."""
    requires_biometric: bool
    """Si True : signal client biométrie / PIN local lorsque pertinent."""
    allowed_if_device_trusted_only: bool
    """Si True : device non trusted → friction renforcée (step-up)."""
    description: str = ""


def _p(
    key: str,
    level: AuthLevel,
    *,
    step_up: bool = False,
    recent: Optional[int] = None,
    biometric: bool = False,
    trusted_only: bool = False,
    desc: str = "",
) -> SensitiveActionPolicy:
    return SensitiveActionPolicy(
        action_key=key,
        required_auth_level=level,
        requires_step_up=step_up,
        requires_recent_auth_seconds=recent,
        requires_biometric=biometric,
        allowed_if_device_trusted_only=trusted_only,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Inventaire — aligner progressivement les routes FastAPI (Depends) sur ces clés.
# ---------------------------------------------------------------------------
ACTION_POLICIES: Dict[str, SensitiveActionPolicy] = {
    # HIGH — mouvements fonds & secrets
    "withdrawal": _p(
        "withdrawal",
        AuthLevel.HIGH,
        step_up=True,
        recent=900,
        biometric=True,
        trusted_only=True,
        desc="Retrait crypto / fiat",
    ),
    "wallet_transfer": _p(
        "wallet_transfer",
        AuthLevel.HIGH,
        step_up=True,
        recent=600,
        biometric=True,
        trusted_only=True,
        desc="Transfert interne / entre comptes",
    ),
    "beneficiary_add": _p(
        "beneficiary_add",
        AuthLevel.HIGH,
        step_up=True,
        recent=900,
        desc="Ajout bénéficiaire",
    ),
    "api_key_create": _p(
        "api_key_create",
        AuthLevel.HIGH,
        step_up=True,
        recent=600,
        biometric=True,
        desc="Création / rotation clé API",
    ),
    "security_settings_change": _p(
        "security_settings_change",
        AuthLevel.HIGH,
        step_up=True,
        recent=900,
        biometric=True,
        desc="Modification paramètres sécurité (2FA, limites, etc.)",
    ),
    "contact_change": _p(
        "contact_change",
        AuthLevel.HIGH,
        step_up=True,
        recent=900,
        desc="Changement e-mail / mobile vérifié",
    ),
    "passcode_reset": _p(
        "passcode_reset",
        AuthLevel.HIGH,
        step_up=True,
        recent=600,
        biometric=True,
        desc="Reset passcode / recovery sensibles",
    ),
    "biometric_disable": _p(
        "biometric_disable",
        AuthLevel.HIGH,
        step_up=True,
        recent=600,
        biometric=False,
        desc="Désactivation biométrie",
    ),
    "data_export": _p(
        "data_export",
        AuthLevel.HIGH,
        step_up=True,
        recent=1200,
        desc="Export RGPD / données personnelles",
    ),
    "session_revoke_all": _p(
        "session_revoke_all",
        AuthLevel.HIGH,
        step_up=False,
        recent=None,
        desc="Révocation globale des sessions",
    ),
    # MEDIUM
    "change_password": _p(
        "change_password",
        AuthLevel.MEDIUM,
        step_up=True,
        recent=900,
        desc="Changement mot de passe",
    ),
    "view_sensitive_data": _p(
        "view_sensitive_data",
        AuthLevel.MEDIUM,
        step_up=True,
        recent=600,
        trusted_only=True,
        desc="Accès données sensibles (KYC, risque, intelligence session) — step-up récent obligatoire",
    ),
    "view_portfolio": _p(
        "view_portfolio",
        AuthLevel.MEDIUM,
        step_up=False,
        desc="Consultation portefeuille agrégée",
    ),
    "internal_transfer_low": _p(
        "internal_transfer_low",
        AuthLevel.MEDIUM,
        step_up=False,
        trusted_only=True,
        desc="Transfert interne faible montant (policy métier à brancher)",
    ),
    # LOW
    "view_balances_summary": _p(
        "view_balances_summary",
        AuthLevel.LOW,
        desc="Soldes synthétiques",
    ),
    "preferences_update": _p(
        "preferences_update",
        AuthLevel.LOW,
        desc="Préférences non financières",
    ),
}


def policy_for_action(action_key: str) -> SensitiveActionPolicy:
    k = (action_key or "").strip().lower()
    if k in ACTION_POLICIES:
        return ACTION_POLICIES[k]
    return SensitiveActionPolicy(
        action_key=k or "unknown",
        required_auth_level=AuthLevel.LOW,
        requires_step_up=False,
        requires_recent_auth_seconds=None,
        requires_biometric=False,
        allowed_if_device_trusted_only=False,
        description="Non mappé explicitement — LOW par défaut",
    )


def auth_level_to_tier(level: AuthLevel) -> SecurityTier:
    return {"LOW": "low", "MEDIUM": "medium", "HIGH": "high"}[level.value]


def tier_for_action(action_key: str) -> SecurityTier:
    """Rétrocompat : dérive le tier depuis la politique."""
    return auth_level_to_tier(policy_for_action(action_key).required_auth_level)
