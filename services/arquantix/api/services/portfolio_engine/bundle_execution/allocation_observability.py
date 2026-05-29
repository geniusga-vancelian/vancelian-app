"""Logs structurés Phase 5A.5 — allocation bundle."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("bundle_allocation.observability")


def log_allocation_event(event: str, **fields: Any) -> None:
    """Émet un log structuré ``bundle_allocation.<event>``."""
    payload = {"event": event, "logged_at": datetime.now(timezone.utc).isoformat(), **fields}
    level = logging.WARNING if event.endswith("_failed") else logging.INFO
    logger.log(level, "bundle_allocation.%s %s", event, json.dumps(payload, default=str))
