"""Exceptions S4 product locks."""
from __future__ import annotations

from uuid import UUID

from services.product_locks.error_codes import ProductLockErrorCode


class ProductLockMiddlewareError(Exception):
    """Erreur métier mappable HTTP 409 (L4 middleware)."""

    http_status: int = 409

    def __init__(self, message: str, *, error_code: ProductLockErrorCode | str) -> None:
        self.error_code = (
            error_code.value if isinstance(error_code, ProductLockErrorCode) else str(error_code)
        )
        super().__init__(message)


class ProductLockConflict(Exception):
    """Un lock actif existe déjà pour ce slot, porté par un autre intent (L2 acquire)."""

    def __init__(
        self,
        *,
        lock_key: str,
        existing_intent_id: UUID,
        requested_intent_id: UUID,
    ) -> None:
        self.lock_key = lock_key
        self.existing_intent_id = existing_intent_id
        self.requested_intent_id = requested_intent_id
        super().__init__(
            f"product lock conflict on {lock_key}: "
            f"held by intent {existing_intent_id}, requested {requested_intent_id}"
        )


class ProductLockConflict409(ProductLockMiddlewareError):
    """Lock actif détenu par un autre intent (validation L4)."""

    def __init__(
        self,
        *,
        lock_key: str,
        existing_intent_id: UUID,
        requested_intent_id: UUID,
    ) -> None:
        self.lock_key = lock_key
        self.existing_intent_id = existing_intent_id
        self.requested_intent_id = requested_intent_id
        super().__init__(
            f"product lock conflict on {lock_key}: "
            f"held by intent {existing_intent_id}, requested {requested_intent_id}",
            error_code=ProductLockErrorCode.PRODUCT_LOCK_CONFLICT,
        )


class BalanceChanged409(ProductLockMiddlewareError):
    """Snapshot hash ne correspond plus à la balance courante."""

    def __init__(
        self,
        *,
        asset: str,
        scope: str,
        expected_hash: str,
        actual_hash: str,
    ) -> None:
        self.asset = asset
        self.scope = scope
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        super().__init__(
            f"balance changed for {asset}/{scope}: "
            f"expected hash {expected_hash}, actual {actual_hash}",
            error_code=ProductLockErrorCode.BALANCE_CHANGED,
        )


class BalanceVersionMismatch409(ProductLockMiddlewareError):
    """Version PE snapshot différente de celle capturée."""

    def __init__(
        self,
        *,
        asset: str,
        scope: str,
        expected_version: int,
        actual_version: int,
    ) -> None:
        self.asset = asset
        self.scope = scope
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            f"balance version mismatch for {asset}/{scope}: "
            f"expected {expected_version}, actual {actual_version}",
            error_code=ProductLockErrorCode.BALANCE_VERSION_MISMATCH,
        )


class ProductLockDisabled409(ProductLockMiddlewareError):
    """Feature product locks désactivée alors qu'une validation stricte est requise."""

    def __init__(self, message: str = "product locks feature is disabled") -> None:
        super().__init__(message, error_code=ProductLockErrorCode.PRODUCT_LOCK_DISABLED)


class TransactionInProgress409(ProductLockMiddlewareError):
    """Utilisateur a déjà une transaction financière active (global lock V1)."""

    def __init__(
        self,
        *,
        lock_key: str,
        existing_intent_id: UUID,
        requested_intent_id: UUID,
    ) -> None:
        self.lock_key = lock_key
        self.existing_intent_id = existing_intent_id
        self.requested_intent_id = requested_intent_id
        super().__init__(
            f"transaction in progress on {lock_key}: "
            f"held by intent {existing_intent_id}, requested {requested_intent_id}",
            error_code=ProductLockErrorCode.TRANSACTION_IN_PROGRESS,
        )
