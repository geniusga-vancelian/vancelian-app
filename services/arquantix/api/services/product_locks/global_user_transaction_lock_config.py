"""Configuration Global User Transaction Lock V1 (défaut OFF)."""
from __future__ import annotations

import os

DEFAULT_GLOBAL_USER_TRANSACTION_LOCK_ENABLED = False
DEFAULT_GLOBAL_USER_TRANSACTION_LOCK_TTL_SECONDS = 3600


def global_user_transaction_lock_enabled() -> bool:
    """Flag V1 — 1 user = 1 transaction financière active."""
    raw = (
        os.getenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED")
        or str(DEFAULT_GLOBAL_USER_TRANSACTION_LOCK_ENABLED)
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def default_global_user_transaction_lock_ttl_seconds() -> int:
    raw = (
        os.getenv("GLOBAL_USER_TRANSACTION_LOCK_TTL_SECONDS")
        or str(DEFAULT_GLOBAL_USER_TRANSACTION_LOCK_TTL_SECONDS)
    ).strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return DEFAULT_GLOBAL_USER_TRANSACTION_LOCK_TTL_SECONDS
