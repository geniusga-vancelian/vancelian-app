"""Verrou PostgreSQL session-level pour defi_observability_tick (Phase 10)."""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Clés stables (deux int32) — ne pas réutiliser ailleurs sans coordination.
_LOCK_KEY1 = 0xDEF1
_LOCK_KEY2 = 0x0909


def try_acquire_defi_tick_lock(db: Session) -> bool:
    """Tente pg_try_advisory_lock ; False si un autre tick no-dry-run tient le verrou."""
    acquired = db.execute(
        text("SELECT pg_try_advisory_lock(:k1, :k2)"),
        {"k1": _LOCK_KEY1, "k2": _LOCK_KEY2},
    ).scalar()
    return bool(acquired)


def release_defi_tick_lock(db: Session) -> bool:
    """Libère le verrou session ; True si le verrou était détenu par cette session."""
    released = db.execute(
        text("SELECT pg_advisory_unlock(:k1, :k2)"),
        {"k1": _LOCK_KEY1, "k2": _LOCK_KEY2},
    ).scalar()
    if not released:
        logger.debug("defi_observability.lock_not_held_on_release")
    return bool(released)
