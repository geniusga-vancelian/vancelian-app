"""Observabilité runtime — endpoints persons legacy (Phase 4C.1).

Chaque appel émet :
- un log structuré JSON (toujours actif) ;
- si ``AUTH_SECURITY_EVENTS_ENABLED``, un événement ``auth_security_events`` (SIEM).
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from core.env import allow_legacy_unauthenticated_kyc
from services.auth.models import AuthContext
from services.auth.security_events_service import persist_auth_security_event
from services.persons.legacy_persons_metrics import get_legacy_persons_metrics

logger = logging.getLogger("arquantix.persons.legacy")

LEGACY_PERSONS_ENDPOINT_HIT = "legacy_persons_endpoint_hit"

_ENDPOINT_LABELS = {
    "legacy_get_person": "GET /api/persons/{person_id}",
    "legacy_set_field": "POST /api/persons/{person_id}/fields",
}


def _person_id_fingerprint(person_id: UUID) -> str:
    """Empreinte non réversible courte — pas d’UUID en clair dans les logs / SIEM."""
    return hashlib.sha256(f"person:{person_id}".encode()).hexdigest()[:16]


def _caller_category(auth: Optional[AuthContext]) -> str:
    if auth is None:
        return "unauthenticated"
    if auth.is_admin:
        return "admin"
    return "owner"


def record_legacy_persons_endpoint_hit(
    *,
    request: Request,
    db: Session,
    person_id: UUID,
    endpoint_key: str,
    method: str,
    auth: Optional[AuthContext],
) -> None:
    endpoint_name = _ENDPOINT_LABELS.get(endpoint_key, endpoint_key)
    successor = (
        "/api/persons/{person_id}/identity" if endpoint_key == "legacy_get_person" else None
    )
    meta: dict = {
        "legacy_persons_event": LEGACY_PERSONS_ENDPOINT_HIT,
        "legacy": True,
        "endpoint_name": endpoint_name,
        "method": method,
        "authenticated": auth is not None,
        "allow_legacy_unauthenticated_kyc": allow_legacy_unauthenticated_kyc(),
        "person_id_fingerprint": _person_id_fingerprint(person_id),
        "caller_category": _caller_category(auth),
        "successor_endpoint": successor,
    }
    get_legacy_persons_metrics().record_hit(
        endpoint_name=meta["endpoint_name"],
        method=meta["method"],
        authenticated=bool(meta["authenticated"]),
        caller_category=meta["caller_category"],
        allow_legacy_unauthenticated_kyc=bool(meta["allow_legacy_unauthenticated_kyc"]),
    )

    payload = json.dumps(meta, sort_keys=True, default=str)
    logger.info("%s %s", LEGACY_PERSONS_ENDPOINT_HIT, payload)

    dev = (request.headers.get("x-device-id") or "")[:128]
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    if ua and len(ua) > 512:
        ua = ua[:512]
    user_id = auth.user_id if auth is not None else None

    # ``persist_auth_security_event`` no-op si ``AUTH_SECURITY_EVENTS_ENABLED`` est faux.
    persist_auth_security_event(
        user_id=user_id,
        device_id=dev,
        event_type=LEGACY_PERSONS_ENDPOINT_HIT,
        ip_address=ip,
        user_agent=ua,
        metadata=meta,
        db=db,
    )
