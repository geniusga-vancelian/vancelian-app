"""Feature flags Phase 4B — historique bundle via ledger."""
from __future__ import annotations

import os


def _env_bool(name: str, default: str) -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw in ("1", "true", "yes", "on")


def bundle_ledger_history_enabled() -> bool:
    """Active la lecture historique bundle depuis ``bundle_ledger_entries``."""
    return _env_bool("BUNDLE_LEDGER_HISTORY_ENABLED", "false")


def bundle_ledger_backfill_dry_run_default() -> bool:
    """Dry-run par défaut pour le backfill (aucune écriture)."""
    return _env_bool("BUNDLE_LEDGER_BACKFILL_DRY_RUN", "true")
