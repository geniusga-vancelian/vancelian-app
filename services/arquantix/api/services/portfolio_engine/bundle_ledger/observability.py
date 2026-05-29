"""Logs structurés Phase 4C — rollout bundle ledger."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("bundle_ledger.observability")


def log_bundle_ledger_event(event: str, **fields: Any) -> None:
    """Émet un log structuré bundle ledger (monitoring / rollout)."""
    payload = {"event": event, "logged_at": datetime.now(timezone.utc).isoformat(), **fields}
    level = logging.ERROR if event == "ledger_reconciliation_diff" else logging.INFO
    if event == "bundle_backfill_warning":
        level = logging.WARNING
    if event == "ledger_history_fallback":
        level = logging.WARNING
    logger.log(level, "bundle_ledger.%s %s", event, json.dumps(payload, default=str))
