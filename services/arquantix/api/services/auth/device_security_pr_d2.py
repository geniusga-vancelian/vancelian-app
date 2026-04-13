"""PR D2 — politique device : niveau sécurité, signature refresh, fraîcheur attestation.

* ``DEVICE_SECURITY_LEVEL`` : 0 = désactivé (défaut), 1 = vérifier si clé enregistrée + en-têtes,
  2 = signature obligatoire si credential existe (sinon step-up / refus selon config),
  3 = PR D4 : skew serré signatures sensibles, nonces scopées par route, JWT lié au device, risque.
* ``DEVICE_SIGNATURE_STRICT`` : si true et niveau >= 1, refuser refresh sans signature valide
  lorsqu'une ligne ``auth_device_credentials`` existe pour ce couple user/device.
* ``ATTESTATION_SESSION_MAX_AGE_SEC`` : vide = pas d'exigence ; sinon 403 step-up si
  ``auth_sessions.attestation_verified_at`` plus vieux que ce délai (refresh).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from database import AuthDeviceCredential, AuthSession


def device_security_level() -> int:
    try:
        return max(0, min(3, int(os.getenv("DEVICE_SECURITY_LEVEL", "0"))))
    except ValueError:
        return 0


def device_signature_strict() -> bool:
    return (os.getenv("DEVICE_SIGNATURE_STRICT", "false").strip().lower() in ("1", "true", "yes"))


def attestation_session_max_age_sec() -> Optional[int]:
    raw = (os.getenv("ATTESTATION_SESSION_MAX_AGE_SEC") or "").strip()
    if not raw:
        return None
    try:
        return max(60, min(86400 * 30, int(raw)))
    except ValueError:
        return None


def has_device_credential(db: Session, *, user_id: int, device_id: str) -> bool:
    return (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == user_id,
            AuthDeviceCredential.device_id == device_id,
        )
        .first()
        is not None
    )


def check_attestation_freshness_or_raise(
    *,
    session: AuthSession,
    now: Optional[datetime] = None,
) -> None:
    """Lève HTTPException 403 step-up si attestation trop vieille (policy activée)."""
    from fastapi import HTTPException, status

    max_age = attestation_session_max_age_sec()
    if max_age is None:
        return
    verified = session.attestation_verified_at
    if verified is None:
        return
    now = now or datetime.now(timezone.utc)
    if verified.tzinfo is None:
        verified = verified.replace(tzinfo=timezone.utc)
    age = (now - verified).total_seconds()
    if age <= max_age:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "device_attestation_stale",
            "step_up": True,
            "message": "Device attestation must be renewed.",
            "otp_login_path": "/auth/login/email-otp/start",
        },
    )


def enforce_refresh_device_signature_if_configured(
    *,
    db: Session,
    request,  # Request
    session: AuthSession,
    refresh_token: str,
    normalized_session_device_id: str,
) -> None:
    """
    Si PR D2 actif et credential présent(e), vérifie ``X-Device-Signature`` / Timestamp.
    Lève ``HTTPException`` 403 en cas d'échec lorsque la politique l'exige.
    """
    from fastapi import HTTPException, status

    from services.auth.device_request_signature import verify_refresh_device_signature

    lvl = device_security_level()
    if lvl == 0:
        return

    cred = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == session.user_id,
            AuthDeviceCredential.device_id == normalized_session_device_id,
        )
        .first()
    )
    if cred is None:
        return

    sig = request.headers.get("X-Device-Signature")
    ts = request.headers.get("X-Device-Signature-Timestamp")
    ok = verify_refresh_device_signature(
        public_key_spki_b64=cred.public_key_spki_b64,
        refresh_token=refresh_token,
        signature_b64=sig,
        timestamp_raw=ts,
    )
    if ok:
        cred.last_used_at = datetime.now(timezone.utc)
        return

    strict_fail = lvl >= 2 or device_signature_strict()
    optional_attempt = bool(sig or ts) and lvl == 1 and not device_signature_strict()
    if optional_attempt or strict_fail:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "device_signature_invalid",
                "step_up": True,
                "message": "Refresh signature verification failed.",
            },
        )
