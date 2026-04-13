"""Compteur optionnel d’exécutions SQL (SQLAlchemy) — observabilité PR C.1.

Activer : ``AUTH_SQL_METRICS_ENABLED=1``. Écoute ``before_cursor_execute`` sur l’engine principal.
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import event

from services.auth.auth_performance_metrics import bump_db_cursor_execute

logger = logging.getLogger(__name__)
_installed_on = None


def install_db_sql_metrics_listener(engine) -> None:
    """Idempotent : un seul listener par processus par engine."""
    global _installed_on
    if _installed_on is engine:
        return
    if os.getenv("AUTH_SQL_METRICS_ENABLED", "").lower() not in ("1", "true", "yes"):
        return

    @event.listens_for(engine, "before_cursor_execute", retval=False)
    def _on_before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        bump_db_cursor_execute()

    _installed_on = engine
    logger.info("db_sql_metrics: before_cursor_execute listener installed on engine")
