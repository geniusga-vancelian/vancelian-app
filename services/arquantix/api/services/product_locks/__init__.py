"""S4 — Product locks (pessimistic asset/scope serialization)."""
from services.product_locks.balance_snapshot import (
    BalanceAvailableResolver,
    BalanceSnapshot,
    BuildBalanceSnapshotResult,
    build_balance_snapshot,
    compute_balance_snapshot_hash,
    resolve_available_from_pe_snapshot,
)
from services.product_locks.config import (
    default_product_lock_ttl_seconds,
    transaction_product_locks_enabled,
)
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.exceptions import ProductLockConflict
from services.product_locks.lock_key import build_lock_key
from services.product_locks.models import TransactionProductLock
from services.product_locks.results import AcquireProductLockResult, ReleaseProductLockResult
from services.product_locks.service import (
    acquire_product_lock,
    expire_product_locks,
    release_product_lock,
)

__all__ = [
    "AcquireProductLockResult",
    "BalanceAvailableResolver",
    "BalanceSnapshot",
    "BuildBalanceSnapshotResult",
    "ProductLockConflict",
    "ProductLockScope",
    "ProductLockStatus",
    "ReleaseProductLockResult",
    "TransactionProductLock",
    "acquire_product_lock",
    "build_balance_snapshot",
    "build_lock_key",
    "compute_balance_snapshot_hash",
    "default_product_lock_ttl_seconds",
    "expire_product_locks",
    "release_product_lock",
    "resolve_available_from_pe_snapshot",
    "transaction_product_locks_enabled",
]
