"""Feature flag Phase 6A — projections UX historique bundle (lecture seule)."""
from __future__ import annotations

import os


def _env_bool(name: str, default: str) -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw in ("1", "true", "yes", "on")


def bundle_transaction_projection_v2_enabled() -> bool:
    """Active les projections self-trading / bundle (rollback : false)."""
    return _env_bool("BUNDLE_TRANSACTION_PROJECTION_V2_ENABLED", "true")
