"""Construction de lock_key canonique (ADR 001 §5bis)."""
from __future__ import annotations

from uuid import UUID

from services.product_locks.enums import ProductLockScope


def build_lock_key(
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
) -> str:
    """Clé dénormalisée stockée en base pour lookup rapide."""
    scope_value = scope.value if isinstance(scope, ProductLockScope) else str(scope).strip().lower()
    asset_norm = str(asset).strip().upper()
    return f"person:{person_id}:wallet:{wallet_id}:asset:{asset_norm}:scope:{scope_value}"
