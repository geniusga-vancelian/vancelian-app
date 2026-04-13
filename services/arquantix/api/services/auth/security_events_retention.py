"""Purge des événements ``auth_security_events`` plus vieux que le TTL configuré."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from database import AuthSecurityEvent

logger = logging.getLogger("arquantix.auth.security.retention")


def retention_days() -> int:
    raw = (os.getenv("AUTH_SECURITY_EVENTS_RETENTION_DAYS") or "90").strip()
    try:
        n = int(raw)
    except ValueError:
        n = 90
    return max(7, min(730, n))


def purge_old_auth_security_events(db: Session, *, do_commit: bool = True) -> int:
    """Supprime les lignes dont ``created_at`` est antérieur au TTL. Retourne le nombre supprimé."""
    days = retention_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    res = db.execute(delete(AuthSecurityEvent).where(AuthSecurityEvent.created_at < cutoff))
    if do_commit:
        db.commit()
    else:
        db.flush()
    n = res.rowcount or 0
    if n:
        logger.info("auth_security_events retention purge removed %s row(s) older_than_days=%s", n, days)
    return int(n)
