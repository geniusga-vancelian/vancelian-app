"""Purge périodique des lignes ``auth_spent_refresh_jti`` anciennes."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from database import AuthSpentRefreshJti

logger = logging.getLogger(__name__)


def spent_jti_retention_days() -> int:
    return max(1, int(os.getenv("AUTH_SPENT_JTI_RETENTION_DAYS", "30")))


def run_spent_jti_cleanup(db: Session) -> int:
    """Supprime les jti dépensés plus vieux que la rétention. Retourne le nombre de lignes supprimées."""
    days = spent_jti_retention_days()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(AuthSpentRefreshJti).filter(AuthSpentRefreshJti.spent_at < cutoff)
    n = q.delete(synchronize_session=False)
    db.commit()
    if n:
        logger.info("auth_spent_jti_cleanup deleted=%s retention_days=%s", n, days)
    return n
