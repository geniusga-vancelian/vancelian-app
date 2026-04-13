"""
Moteur de politique Zero Trust — RBAC + ABAC sur RequestSecurityContext.
Règles initiales codées ; évolution possible vers YAML/DB (voir admin reload).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from services.auth.device_attestation_service import DEVICE_TRUST_BLOCKED, DEVICE_TRUST_SUSPICIOUS
from services.security.zero_trust.request_security_context import RequestSecurityContext


def _truthy(name: str, default: str = "false") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def _int_env(name: str, default: int) -> int:
    try:
        return int((os.getenv(name) or str(default)).strip())
    except ValueError:
        return default


# RBAC : rôles sur admin_users.zero_trust_role
ROLE_POLICY_MAP: Dict[str, Dict[str, Any]] = {
    "admin": {
        "description": "Accès complet sous réserve ABAC (risque, device, auth_strength).",
        "deny_action_prefixes": (),
    },
    "support": {
        "description": "Support : pas d’admin sécurité ni révocation globale.",
        "deny_action_prefixes": ("security.admin", "auth.revoke_all"),
    },
    "readonly": {
        "description": "Lecture seule : pas d’écriture KYC ni opérations sensibles.",
        "deny_action_prefixes": (
            "security.admin",
            "auth.revoke_all",
            "kyc.write",
            "custody.withdraw",
            "custody.transfer",
            "crypto.sensitive_decrypt",
        ),
    },
    "user": {
        "description": "Utilisateur final (hors staff) — chemins identity.",
        "deny_action_prefixes": ("security.admin", "auth.revoke_all", "admin."),
    },
}

# ABAC par action (préfixe ou égalité) — seuils et force d’auth minimale
ACTION_POLICY_MAP: Dict[str, Dict[str, Any]] = {
    "session.api_access": {
        "max_effective_risk_deny": _int_env("ZERO_TRUST_DENY_ALL_RISK_THRESHOLD", 95),
        "max_effective_risk_step_up": _int_env("ZERO_TRUST_STEP_UP_RISK_THRESHOLD", 70),
        "min_auth_strength": "password",
        "sensitive": False,
    },
    "auth.refresh": {
        "max_effective_risk_deny": 95,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "password",
        "sensitive": True,
    },
    "auth.revoke_all": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "otp",
        "sensitive": True,
    },
    "kyc.read": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "password",
        "sensitive": True,
    },
    "kyc.write": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "otp",
        "sensitive": True,
    },
    "custody.withdraw": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "passkey",
        "sensitive": True,
    },
    "custody.transfer": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "passkey",
        "sensitive": True,
    },
    "security.admin": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "otp",
        "sensitive": True,
    },
    "crypto.sensitive_decrypt": {
        "max_effective_risk_deny": 85,
        "max_effective_risk_step_up": 65,
        "min_auth_strength": "otp",
        "sensitive": True,
    },
    "admin.list_admins": {
        "max_effective_risk_deny": 90,
        "max_effective_risk_step_up": 70,
        "min_auth_strength": "otp",
        "sensitive": True,
    },
}

_STRENGTH_ORDER: Dict[str, int] = {
    "password": 10,
    "otp": 30,
    "passkey": 50,
    "passkey+attestation": 70,
}


def effective_risk_score(ctx: RequestSecurityContext) -> int:
    fraud_component = 0
    if ctx.fraud_score is not None:
        fraud_component = min(100, max(0, int(round(float(ctx.fraud_score) * 100))))
    return min(100, max(int(ctx.global_risk_score), fraud_component))


def _strength_meets(min_required: str, actual: str) -> bool:
    ra = _STRENGTH_ORDER.get((actual or "password").lower(), 5)
    rq = _STRENGTH_ORDER.get((min_required or "password").lower(), 10)
    return ra >= rq


def auth_strength_sufficient(min_required: str, actual: str) -> bool:
    """API publique pour les gardes (équivalent à la comparaison de rang interne)."""
    return _strength_meets(min_required, actual)


def _primary_role(ctx: RequestSecurityContext) -> str:
    if not ctx.roles:
        return "admin"
    return str(ctx.roles[0]).lower()


def _action_config(action: str) -> Dict[str, Any]:
    if action in ACTION_POLICY_MAP:
        return ACTION_POLICY_MAP[action]
    best: Optional[Tuple[int, Dict[str, Any]]] = None
    for key, cfg in ACTION_POLICY_MAP.items():
        if action.startswith(key + "."):
            ln = len(key)
            if best is None or ln > best[0]:
                best = (ln, cfg)
    return best[1] if best else ACTION_POLICY_MAP["session.api_access"]


def _role_denies_action(role: str, action: str) -> bool:
    spec = ROLE_POLICY_MAP.get(role) or ROLE_POLICY_MAP["admin"]
    prefixes: Tuple[str, ...] = tuple(spec.get("deny_action_prefixes") or ())
    for p in prefixes:
        if action == p or action.startswith(p + ".") or action.startswith(p):
            return True
    return False


def evaluate_security_policy(
    context: RequestSecurityContext,
    action: str,
    resource: str,
) -> Dict[str, Any]:
    """
    Évalue allow / step_up / deny pour une action et une ressource logiques.

    ``resource`` est journalisé tel quel (ex. person:uuid, contact:123).
    """
    eff = effective_risk_score(context)
    cfg = _action_config(action)
    role = _primary_role(context)
    sensitive = bool(cfg.get("sensitive", False))
    max_deny = int(cfg.get("max_effective_risk_deny", 90))
    max_step = int(cfg.get("max_effective_risk_step_up", 70))
    min_auth = str(cfg.get("min_auth_strength", "password"))

    base: Dict[str, Any] = {
        "effective_risk": eff,
        "resource": resource,
        "action": action,
    }

    if context.account_locked:
        return {
            **base,
            "allow": False,
            "require_step_up": False,
            "deny_reason": "Compte verrouillé (security.account_locked).",
            "policy_id": "zt_account_locked",
            "action_taken": "deny",
        }

    if context.device_reputation_blocked or context.device_trust_level.upper() == DEVICE_TRUST_BLOCKED:
        return {
            **base,
            "allow": False,
            "require_step_up": False,
            "deny_reason": "Appareil bloqué ou réputation device interdite.",
            "policy_id": "zt_device_blocked",
            "action_taken": "deny",
        }

    if _role_denies_action(role, action):
        return {
            **base,
            "allow": False,
            "require_step_up": False,
            "deny_reason": f"Rôle « {role} » interdit pour l’action « {action} ».",
            "policy_id": "zt_rbac_role_deny",
            "action_taken": "deny",
        }

    extreme = _int_env("ZERO_TRUST_DENY_ALL_RISK_THRESHOLD", 95)
    if eff >= extreme:
        return {
            **base,
            "allow": False,
            "require_step_up": False,
            "deny_reason": f"Score de risque effectif {eff} ≥ {extreme} (politique globale).",
            "policy_id": "zt_risk_extreme_deny",
            "action_taken": "deny",
        }

    if sensitive and eff >= max_deny:
        return {
            **base,
            "allow": False,
            "require_step_up": False,
            "deny_reason": f"Action sensible refusée : risque effectif {eff} ≥ {max_deny}.",
            "policy_id": "zt_sensitive_risk_deny",
            "action_taken": "deny",
        }

    suspicious_device = context.device_trust_level.upper() in (DEVICE_TRUST_SUSPICIOUS, "UNTRUSTED")
    if sensitive and suspicious_device and not _strength_meets("otp", context.auth_strength):
        return {
            **base,
            "allow": False,
            "require_step_up": True,
            "deny_reason": "Appareil suspect : authentification renforcée (OTP ou passkey) requise.",
            "policy_id": "zt_device_suspicious_auth",
            "action_taken": "restrict",
        }

    if not _strength_meets(min_auth, context.auth_strength):
        return {
            **base,
            "allow": False,
            "require_step_up": sensitive,
            "deny_reason": f"auth_strength « {context.auth_strength} » insuffisant (min « {min_auth} ») pour cette action.",
            "policy_id": "zt_auth_strength_deny",
            "action_taken": "restrict" if sensitive else "deny",
        }

    require_step_up = eff >= max_step
    strict_default = _truthy("ZERO_TRUST_STRICT_DEFAULT_ACCESS", "false")
    allow = True
    action_taken = "allow"
    policy_id = "zt_allow"
    deny_reason: Optional[str] = None

    if require_step_up:
        policy_id = "zt_risk_step_up"
        action_taken = "step_up"
        deny_reason = f"Risque effectif {eff} ≥ {max_step} : step-up requis."
        if sensitive or strict_default:
            allow = False

    return {
        **base,
        "allow": allow,
        "require_step_up": require_step_up,
        "deny_reason": deny_reason,
        "policy_id": policy_id,
        "action_taken": action_taken,
    }


def list_policy_definitions() -> Dict[str, Any]:
    """Expose la config effective (audit / GET admin)."""
    return {
        "role_policy_map": ROLE_POLICY_MAP,
        "action_policy_map": ACTION_POLICY_MAP,
        "thresholds": {
            "ZERO_TRUST_DENY_ALL_RISK_THRESHOLD": _int_env("ZERO_TRUST_DENY_ALL_RISK_THRESHOLD", 95),
            "ZERO_TRUST_STEP_UP_RISK_THRESHOLD": _int_env("ZERO_TRUST_STEP_UP_RISK_THRESHOLD", 70),
        },
        "strength_order": dict(_STRENGTH_ORDER),
    }
