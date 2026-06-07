"""Snapshot balance S4 (L3 — metadata only, non branché runtime)."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from services.exchange.assets import ASSET_PRECISION
from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.product_locks.config import transaction_product_locks_enabled
from services.product_locks.enums import ProductLockScope

BalanceAvailableResolver = Callable[[], Decimal]


def _normalize_asset(asset: str) -> str:
    return str(asset).strip().upper()


def _normalize_scope(scope: ProductLockScope | str) -> str:
    if isinstance(scope, ProductLockScope):
        return scope.value
    return str(scope).strip().lower()


def _format_available_amount(value: Decimal, *, asset: str) -> str:
    """Format canonique aligné sur Portfolio Breakdown ``_fmt``."""
    asset_norm = _normalize_asset(asset)
    qty = Decimal(str(value))
    precision = ASSET_PRECISION.get(asset_norm, 8)
    text = f"{qty:.{precision}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _get_pe_bucket_amount(bucket: dict[str, Decimal], asset: str) -> Decimal:
    asset_norm = _normalize_asset(asset)
    if asset_norm in bucket:
        return bucket[asset_norm]
    for key, value in bucket.items():
        if str(key).strip().upper() == asset_norm:
            return value
    return Decimal("0")


def resolve_available_from_pe_snapshot(
    pe: CurrentPeScopeSnapshot,
    *,
    asset: str,
    scope: ProductLockScope | str,
) -> Decimal:
    """Projection PE par scope — même buckets que Portfolio Breakdown (lecture seule)."""
    asset_norm = _normalize_asset(asset)
    scope_norm = _normalize_scope(scope)

    if scope_norm == ProductLockScope.TRADING_AVAILABLE.value:
        return _get_pe_bucket_amount(pe.trading_available, asset_norm)
    if scope_norm == ProductLockScope.BUNDLE.value:
        cash = _get_pe_bucket_amount(pe.bundle_cash, asset_norm)
        position = _get_pe_bucket_amount(pe.bundle_position, asset_norm)
        return cash + position
    if scope_norm == ProductLockScope.VAULT.value:
        return _get_pe_bucket_amount(pe.vault_position, asset_norm)
    if scope_norm == ProductLockScope.LOMBARD_COLLATERAL.value:
        return _get_pe_bucket_amount(pe.trading_locked_collateral, asset_norm)
    if scope_norm == ProductLockScope.LOMBARD_BORROW.value:
        return _get_pe_bucket_amount(pe.liability, asset_norm)

    raise ValueError(f"Unsupported product lock scope: {scope_norm}")


def compute_balance_snapshot_hash(
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
    available: str | Decimal,
    version: int,
) -> str:
    """Hash déterministe (JSON canonique · clés triées)."""
    asset_norm = _normalize_asset(asset)
    available_norm = (
        available
        if isinstance(available, str)
        else _format_available_amount(available, asset=asset_norm)
    )
    payload: dict[str, Any] = {
        "person_id": str(person_id),
        "wallet_id": str(wallet_id),
        "asset": asset_norm,
        "scope": _normalize_scope(scope),
        "available": available_norm,
        "version": int(version),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class BalanceSnapshot:
    asset: str
    available: str
    version: int
    hash: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "asset": self.asset,
            "available": self.available,
            "version": self.version,
            "hash": self.hash,
        }


@dataclass(frozen=True)
class BuildBalanceSnapshotResult:
    skipped: bool
    snapshot: BalanceSnapshot | None


def build_balance_snapshot(
    *,
    person_id: UUID,
    wallet_id: UUID,
    asset: str,
    scope: ProductLockScope | str,
    version: int,
    available: Decimal | str | None = None,
    pe_snapshot: CurrentPeScopeSnapshot | None = None,
    resolve_available: BalanceAvailableResolver | None = None,
) -> BuildBalanceSnapshotResult:
    """Construit le metadata snapshot balance (flag OFF → no-op).

    Résolution ``available`` (priorité) :
    1. argument ``available`` explicite ;
    2. callable ``resolve_available`` ;
    3. ``pe_snapshot`` + projection scope PE.
    """
    if not transaction_product_locks_enabled():
        return BuildBalanceSnapshotResult(skipped=True, snapshot=None)

    asset_norm = _normalize_asset(asset)
    scope_norm = _normalize_scope(scope)

    if available is not None:
        available_amount = (
            Decimal(str(available))
            if not isinstance(available, Decimal)
            else available
        )
    elif resolve_available is not None:
        available_amount = resolve_available()
    elif pe_snapshot is not None:
        available_amount = resolve_available_from_pe_snapshot(
            pe_snapshot,
            asset=asset_norm,
            scope=scope_norm,
        )
    else:
        raise ValueError(
            "build_balance_snapshot requires available, resolve_available, or pe_snapshot"
        )

    available_text = _format_available_amount(available_amount, asset=asset_norm)
    snapshot_hash = compute_balance_snapshot_hash(
        person_id=person_id,
        wallet_id=wallet_id,
        asset=asset_norm,
        scope=scope_norm,
        available=available_text,
        version=version,
    )
    return BuildBalanceSnapshotResult(
        skipped=False,
        snapshot=BalanceSnapshot(
            asset=asset_norm,
            available=available_text,
            version=int(version),
            hash=snapshot_hash,
        ),
    )
