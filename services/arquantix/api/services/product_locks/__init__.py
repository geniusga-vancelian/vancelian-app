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
from services.product_locks.error_codes import ProductLockErrorCode
from services.product_locks.exceptions import (
    BalanceChanged409,
    BalanceVersionMismatch409,
    ProductLockConflict,
    ProductLockConflict409,
    ProductLockDisabled409,
    ProductLockMiddlewareError,
)
from services.product_locks.lock_key import build_lock_key
from services.product_locks.middleware import (
    ProductLockMiddlewareResult,
    validate_balance_snapshot_or_raise,
    validate_product_lock_or_raise,
)
from services.product_locks.models import TransactionProductLock
from services.product_locks.results import (
    AcquireProductLockResult,
    ReleaseProductLockResult,
    ReleaseProductLocksForIntentResult,
)
from services.product_locks.service import (
    acquire_product_lock,
    expire_product_locks,
    release_product_lock,
    release_product_locks_for_intent,
)

__all__ = [
    "AcquireProductLockResult",
    "BalanceAvailableResolver",
    "BalanceChanged409",
    "BalanceSnapshot",
    "BalanceVersionMismatch409",
    "BuildBalanceSnapshotResult",
    "ProductLockConflict",
    "ProductLockConflict409",
    "ProductLockDisabled409",
    "ProductLockErrorCode",
    "ProductLockMiddlewareError",
    "ProductLockMiddlewareResult",
    "ProductLockScope",
    "ProductLockStatus",
    "ReleaseProductLocksForIntentResult",
    "ReleaseProductLockResult",
    "TransactionProductLock",
    "acquire_product_lock",
    "build_balance_snapshot",
    "build_lock_key",
    "compute_balance_snapshot_hash",
    "default_product_lock_ttl_seconds",
    "expire_product_locks",
    "release_product_lock",
    "release_product_locks_for_intent",
    "resolve_available_from_pe_snapshot",
    "transaction_product_locks_enabled",
    "validate_balance_snapshot_or_raise",
    "validate_product_lock_or_raise",
]
