"""S4 — Product locks (pessimistic asset/scope serialization)."""
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
    "ProductLockConflict",
    "ProductLockScope",
    "ProductLockStatus",
    "ReleaseProductLockResult",
    "TransactionProductLock",
    "acquire_product_lock",
    "build_lock_key",
    "default_product_lock_ttl_seconds",
    "expire_product_locks",
    "release_product_lock",
    "transaction_product_locks_enabled",
]
