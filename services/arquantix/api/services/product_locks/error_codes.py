"""Codes d'erreur S4 product locks (middleware 409)."""
from __future__ import annotations

from enum import Enum


class ProductLockErrorCode(str, Enum):
    PRODUCT_LOCK_CONFLICT = "PRODUCT_LOCK_CONFLICT"
    BALANCE_CHANGED = "BALANCE_CHANGED"
    BALANCE_VERSION_MISMATCH = "BALANCE_VERSION_MISMATCH"
    PRODUCT_LOCK_DISABLED = "PRODUCT_LOCK_DISABLED"
