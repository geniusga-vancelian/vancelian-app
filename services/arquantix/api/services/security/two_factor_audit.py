"""Audit trail for 2FA using public.audit_events (no secrets in payload)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import AuditEvent

logger = logging.getLogger(__name__)


def audit_two_factor_event(
    db: Optional[Session],
    *,
    person_id: UUID,
    event_type: str,
    payload: Dict[str, Any],
    actor_type: str = "user",
    actor_id: Optional[str] = None,
    standalone: bool = False,
) -> None:
    """Best-effort audit: failures must not break the 2FA flow.

    If standalone=True, persist in a new DB session so the row survives rollback
    of the caller transaction (e.g. OTP send failure after challenge insert).
    """
    safe_payload = {k: v for k, v in payload.items() if v is not None}
    try:
        ev = AuditEvent(
            id=uuid.uuid4(),
            person_id=person_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=uuid.uuid4(),
            payload=safe_payload,
            schema_version=1,
            created_at=datetime.now(timezone.utc),
        )
        if standalone:
            from database import SessionLocal

            loc = SessionLocal()
            try:
                loc.add(ev)
                loc.commit()
            finally:
                loc.close()
            return
        if db is None:
            return
        db.add(ev)
        db.flush()
    except Exception:
        logger.exception("2fa audit write failed event_type=%s", event_type)
