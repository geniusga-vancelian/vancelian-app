"""Compat : pipeline SIEM déplacé sous ``services.security.security_event_pipeline``."""
from __future__ import annotations

from services.security.security_event_pipeline import (  # noqa: F401
    build_structured_preview,
    emit_security_event,
    forward_after_persist,
    normalize_security_metadata,
    security_events_sink_name,
)
