"""PR D3 — nonces usage unique pour signatures sensibles."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from database import AuthDeviceSignatureNonce
from services.auth.redis_nonce_guard import release_nonce_replay_slot, try_acquire_nonce_replay_slot

logger = logging.getLogger("arquantix.auth.device_nonce")


def _hash_nonce(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def mint_device_signature_nonce(
    *,
    db: Session,
    user_id: int,
    device_id: str,
    purpose: str,
    ttl_sec: int,
    route_path: Optional[str] = None,
) -> tuple[str, datetime]:
    """Retourne ``(nonce_clair, expires_at)`` — stocker uniquement le hash."""
    raw = secrets.token_urlsafe(32)
    nh = _hash_nonce(raw)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=ttl_sec)
    rp = (route_path or "").strip() or None
    row = AuthDeviceSignatureNonce(
        user_id=user_id,
        device_id=device_id,
        nonce_hash=nh,
        purpose=(purpose or "sensitive")[:32],
        route_path=rp,
        expires_at=exp,
    )
    db.add(row)
    db.commit()
    return raw, exp


def consume_device_signature_nonce(
    *,
    db: Session,
    user_id: int,
    device_id: str,
    nonce: str,
    purpose: str,
    route_path: Optional[str] = None,
    route_scope_required: bool = False,
) -> bool:
    """Marque le nonce consommé si valide (TTL, user, device, purpose, route si PR D4)."""
    if not nonce or not str(nonce).strip():
        return False
    nh = _hash_nonce(str(nonce).strip())
    if not try_acquire_nonce_replay_slot(user_id=user_id, device_id=device_id, nonce_hash=nh):
        return False
    now = datetime.now(timezone.utc)
    q = db.query(AuthDeviceSignatureNonce).filter(
        AuthDeviceSignatureNonce.nonce_hash == nh,
        AuthDeviceSignatureNonce.user_id == user_id,
        AuthDeviceSignatureNonce.device_id == device_id,
        AuthDeviceSignatureNonce.purpose == (purpose or "sensitive")[:32],
        AuthDeviceSignatureNonce.expires_at > now,
        AuthDeviceSignatureNonce.consumed_at.is_(None),
    )
    if route_scope_required:
        rp = (route_path or "").strip()
        if not rp:
            return False
        q = q.filter(AuthDeviceSignatureNonce.route_path == rp)
    else:
        q = q.filter(AuthDeviceSignatureNonce.route_path.is_(None))
    row = q.first()
    if row is None:
        release_nonce_replay_slot(user_id=user_id, device_id=device_id, nonce_hash=nh)
        return False
    row.consumed_at = now
    try:
        db.commit()
    except Exception:
        release_nonce_replay_slot(user_id=user_id, device_id=device_id, nonce_hash=nh)
        raise
    return True
