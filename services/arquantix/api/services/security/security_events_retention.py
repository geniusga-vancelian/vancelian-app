"""Rétention ``auth_security_events`` — réexport du module auth (purge TTL)."""
from __future__ import annotations

from services.auth.security_events_retention import (  # noqa: F401
    purge_old_auth_security_events,
    retention_days,
)
