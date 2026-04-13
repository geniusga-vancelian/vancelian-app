"""
Contrôle d’accès aux données chiffrées / sensibles (purpose → politique ZT).
À appeler avant safe_decrypt ou exposition de champs KYC.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from services.security.zero_trust.request_security_context import RequestSecurityContext
from services.security.zero_trust.security_policy_engine import evaluate_security_policy


def decryption_allowed(
    context: RequestSecurityContext,
    purpose: str,
    resource: str,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Indique si le déchiffrement ou la lecture sensible est autorisée.

    ``purpose`` : ex. contact_submission_read, kyc_pii_read, support_ticket_pii.
    Retourne (allowed, policy_result).
    """
    purpose_l = (purpose or "").lower()
    if "kyc" in purpose_l or purpose_l.startswith("person_pii"):
        action = "kyc.read"
    elif "support" in purpose_l and "pii" in purpose_l:
        action = "crypto.sensitive_decrypt"
        resource = f"support:{resource}"
    elif "contact" in purpose_l:
        action = "crypto.sensitive_decrypt"
        resource = f"contact:{resource}"
    else:
        action = "crypto.sensitive_decrypt"
        resource = f"data:{resource}"

    result = evaluate_security_policy(context, action, resource)
    allowed = bool(result.get("allow")) and not result.get("require_step_up")
    return allowed, result


def admin_list_visibility_allowed(
    context: RequestSecurityContext,
    resource: str = "admin_users",
) -> Tuple[bool, Dict[str, Any]]:
    """Liste des comptes admin : masquage si auth faible ou risque élevé."""
    result = evaluate_security_policy(context, "admin.list_admins", resource)
    return bool(result.get("allow")), result
