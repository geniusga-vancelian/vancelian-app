"""Persistance des événements de sécurité auth (feature flag ``AUTH_SECURITY_EVENTS_ENABLED``)."""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from database import AuthSecurityEvent, SessionLocal
from services.security.security_env import is_security_events_enabled

logger = logging.getLogger("arquantix.auth.security")


def persist_auth_security_event(
    *,
    user_id: Optional[int],
    device_id: str,
    event_type: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> None:
    """
    Enregistre un événement. Si ``db`` est fourni : add + flush (commit côté appelant).
    Sinon : session courte + commit (chemins avec rollback ou sans transaction).
    """
    if not is_security_events_enabled():
        return
    meta: Dict[str, Any] = dict(metadata or {})
    row = AuthSecurityEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        device_id=(device_id or "")[:128],
        event_type=event_type[:128],
        ip_address=(ip_address or None)[:45] if ip_address else None,
        user_agent=(user_agent or None)[:512] if user_agent else None,
        metadata_payload=meta,
    )
    if db is not None:
        db.add(row)
        db.flush()
        _forward_to_siem_pipeline(row, db)
        return
    s = SessionLocal()
    try:
        s.add(row)
        s.commit()
        s.refresh(row)
        _forward_to_siem_pipeline(row, None)
    except Exception as exc:  # noqa: BLE001 — audit path : ne pas casser le flux auth
        logger.warning("auth_security_event persist failed: %s", exc)
        s.rollback()
    finally:
        s.close()


def _forward_to_siem_pipeline(row: AuthSecurityEvent, db: Optional[Session]) -> None:
    try:
        from services.security.security_event_pipeline import forward_after_persist

        meta = row.metadata_payload if isinstance(row.metadata_payload, dict) else {}

        forward_after_persist(
            event_id=str(row.id),
            event_type=row.event_type,
            user_id=row.user_id,
            device_id=row.device_id,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            metadata=meta,
            db=db,
        )
    except Exception as exc:  # noqa: BLE001 — ne jamais casser l’auth
        logger.warning("security_event_pipeline forward failed: %s", exc)
