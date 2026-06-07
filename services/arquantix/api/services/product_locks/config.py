"""Configuration S4 product locks (défaut OFF — L2)."""
from __future__ import annotations

import os

DEFAULT_TRANSACTION_PRODUCT_LOCKS_ENABLED = False
DEFAULT_PRODUCT_LOCK_TTL_SECONDS = 3600


def transaction_product_locks_enabled() -> bool:
    """Flag global S4 — acquisition/release actifs uniquement si true."""
    raw = (
        os.getenv("TRANSACTION_PRODUCT_LOCKS_ENABLED")
        or str(DEFAULT_TRANSACTION_PRODUCT_LOCKS_ENABLED)
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def default_product_lock_ttl_seconds() -> int:
    raw = (
        os.getenv("TRANSACTION_PRODUCT_LOCK_TTL_SECONDS")
        or str(DEFAULT_PRODUCT_LOCK_TTL_SECONDS)
    ).strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return DEFAULT_PRODUCT_LOCK_TTL_SECONDS
