"""Résultats du service product locks (S4 L2)."""
from __future__ import annotations

from dataclasses import dataclass

from services.product_locks.models import TransactionProductLock


@dataclass(frozen=True)
class AcquireProductLockResult:
    acquired: bool
    skipped: bool
    idempotent: bool
    lock: TransactionProductLock | None


@dataclass(frozen=True)
class ReleaseProductLockResult:
    released: bool
    skipped: bool
    idempotent: bool
    lock: TransactionProductLock | None
