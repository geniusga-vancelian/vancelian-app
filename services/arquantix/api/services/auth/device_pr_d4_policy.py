"""PR D4 — politique : niveau 3, skew signatures sensibles, binding JWT↔device, scope nonce."""
from __future__ import annotations

import hashlib
import os
from typing import Optional

from services.auth.device_security_pr_d2 import device_security_level


def device_pr_d4_enabled() -> bool:
    """``DEVICE_SECURITY_LEVEL >= 3`` — durcissement PR D4 actif."""
    return device_security_level() >= 3


def nonce_route_scoping_enabled() -> bool:
    """Nonce liée à ``(user, device, route)`` lorsque PR D4 actif."""
    return device_pr_d4_enabled()


def device_access_jwt_binding_enabled() -> bool:
    """Claim ``did_h`` dans l’access token + contrôle ``X-Device-ID`` à chaque requête."""
    return device_pr_d4_enabled()


def device_risk_checks_enabled() -> bool:
    """Score de risque + step-up sur routes sensibles."""
    return device_pr_d4_enabled()


def sensitive_signature_clock_skew_sec() -> int:
    """
    Fenêtre ± pour l’horodatage signé (signatures sensibles ARQXD3).

    PR D3 / niveau 2 : défaut large (120s) via ``DEVICE_SIGNATURE_CLOCK_SKEW_SEC``.
    PR D4 / niveau 3 : défaut 30s via ``DEVICE_SIGNATURE_SENSITIVE_CLOCK_SKEW_SEC``.
    """
    if device_pr_d4_enabled():
        try:
            return max(5, min(120, int(os.getenv("DEVICE_SIGNATURE_SENSITIVE_CLOCK_SKEW_SEC", "30"))))
        except ValueError:
            return 30
    try:
        return max(30, min(600, int(os.getenv("DEVICE_SIGNATURE_CLOCK_SKEW_SEC", "120"))))
    except ValueError:
        return 120


def device_risk_step_up_score_threshold() -> int:
    try:
        return max(0, min(100, int(os.getenv("DEVICE_RISK_SENSITIVE_STEP_UP_SCORE", "65"))))
    except ValueError:
        return 65


def device_risk_revoke_all_sessions_threshold() -> Optional[int]:
    """Seuil optionnel (0–100) : au-delà, révocation de toutes les sessions utilisateur. Vide = désactivé."""
    raw = (os.getenv("DEVICE_RISK_REVOKE_ALL_SESSIONS_THRESHOLD") or "").strip()
    if not raw:
        return None
    try:
        return max(0, min(100, int(raw)))
    except ValueError:
        return None


def compute_device_binding_hash(device_id: str) -> str:
    """128 premiers bits du SHA-256 du ``device_id`` normalisé (32 caractères hex, claim ``did_h``)."""
    raw = (device_id or "").strip().encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def device_binding_hashes_equal(stored: str, computed: str) -> bool:
    """Compat jetons anciens (16 hex) vs nouveaux (32 hex) pour un même appareil."""
    s = str(stored).strip().lower()
    c = computed.lower()
    if s == c:
        return True
    if len(s) == 16 and c.startswith(s):
        return True
    return False


def enforce_device_binding_hash_if_present(*, payload: dict, device_id_for_binding: str) -> None:
    """
    Vérifie ``did_h`` dans un payload JWT déjà décodé (access ou refresh).

    ``device_id_for_binding`` : identifiant d’appareil effectif (ex. en-tête normalisé ou ``effective_device`` refresh).
    """
    if not device_access_jwt_binding_enabled():
        return
    from fastapi import HTTPException, status

    from services.auth.refresh_session import LEGACY_UNKNOWN_DEVICE, normalize_device_id

    want = payload.get("did_h")
    if not want:
        return
    did = normalize_device_id(device_id_for_binding)
    if did == LEGACY_UNKNOWN_DEVICE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "device_jwt_binding_required",
                "message": "X-Device-ID required to match token device binding (PR D4).",
            },
        )
    got = compute_device_binding_hash(did)
    if not device_binding_hashes_equal(str(want), got):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "device_jwt_binding_mismatch",
                "message": "Token is bound to another device.",
            },
        )


def enforce_jwt_device_binding_if_configured(*, token: str, x_device_id: Optional[str]) -> None:
    """
    Access token : si ``did_h`` présent, contrôle avec ``X-Device-ID``.

    Jetons sans ``did_h`` : inchangés (rétrocompat avant refresh).
    """
    if not device_access_jwt_binding_enabled():
        return
    from jose import JWTError, jwt

    from auth import ALGORITHM, SECRET_KEY

    from services.auth.refresh_session import normalize_device_id

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return
    enforce_device_binding_hash_if_present(
        payload=payload,
        device_id_for_binding=normalize_device_id(x_device_id or ""),
    )
