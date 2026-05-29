"""Parse métriques logs bundle ledger (Phase 4D)."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_EVENT_RE = re.compile(r"bundle_ledger\.([a-z_]+)\s+(\{.*\})\s*$")


def parse_log_metrics(
    log_paths: list[Path],
    *,
    since_hours: int = 24,
) -> dict[str, Any]:
    """Compte les événements ``bundle_ledger.*`` dans les fichiers logs."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    counts: Counter[str] = Counter()
    skipped_old = 0
    skipped_unparseable = 0

    for path in log_paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _EVENT_RE.search(line.strip())
            if not match:
                continue
            event_name = match.group(1)
            try:
                payload = json.loads(match.group(2))
            except json.JSONDecodeError:
                skipped_unparseable += 1
                continue
            logged_at = payload.get("logged_at")
            if logged_at:
                try:
                    ts = datetime.fromisoformat(str(logged_at).replace("Z", "+00:00"))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts < cutoff:
                        skipped_old += 1
                        continue
                except ValueError:
                    pass
            counts[event_name] += 1

    return {
        "since_hours": since_hours,
        "log_paths": [str(p) for p in log_paths if p.exists()],
        "ledger_history_read": counts.get("ledger_history_read", 0),
        "ledger_history_fallback": counts.get("ledger_history_fallback", 0),
        "ledger_reconciliation_diff": counts.get("ledger_reconciliation_diff", 0),
        "bundle_backfill_applied": counts.get("bundle_backfill_applied", 0),
        "bundle_backfill_warning": counts.get("bundle_backfill_warning", 0),
        "event_counts": dict(counts),
        "skipped_old": skipped_old,
        "skipped_unparseable": skipped_unparseable,
    }
