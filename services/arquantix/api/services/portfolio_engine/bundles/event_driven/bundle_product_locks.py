"""B2 — Product Lock parent Bundle (scope bundle · flag + allowlist · no legacy replacement)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.assets import ASSET_PRECISION
from services.portfolio_engine.bundle_execution.allocation_config import compute_execution_buffer
from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.product_locks.allowlist import product_locks_enabled_for_person
from services.product_locks.balance_snapshot import resolve_available_from_pe_snapshot
from services.product_locks.enums import ProductLockScope
from services.product_locks.models import TransactionProductLock
from services.product_locks.service import acquire_product_lock, release_product_lock
from services.product_locks.service import AcquireProductLockResult, ReleaseProductLockResult
from services.transaction_intents.enums import IntentProductType

BUNDLE_PARENT_SNAPSHOT_VERSION = "bundle-invest-v1"
BUNDLE_PARENT_LOCK_ASSET = "USDC"
BUNDLE_PARENT_LOCK_SCOPE = ProductLockScope.BUNDLE


def _normalize_asset(asset: str) -> str:
    return str(asset).strip().upper()


def _bundle_locks_active(db: Session, person_id: UUID) -> bool:
    """Flag ON + allowlist configurée + personne éligible — sinon no-op strict."""
    return product_locks_enabled_for_person(db, person_id)


def _format_amount(value: Decimal, *, asset: str) -> str:
    asset_norm = _normalize_asset(asset)
    qty = Decimal(str(value))
    precision = ASSET_PRECISION.get(asset_norm, 8)
    text = f"{qty:.{precision}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _format_decimal_map(bucket: dict[str, Decimal]) -> dict[str, str]:
    out: dict[str, str] = {}
    for asset in sorted(bucket.keys(), key=lambda k: str(k).upper()):
        asset_norm = _normalize_asset(asset)
        out[asset_norm] = _format_amount(bucket[asset], asset=asset_norm)
    return out


def _normalize_planned_allocations(
    planned_allocations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in planned_allocations:
        if not isinstance(row, dict):
            continue
        asset = _normalize_asset(str(row.get("asset") or ""))
        if not asset:
            continue
        entry: dict[str, Any] = {"asset": asset}
        if row.get("weight_bps") is not None:
            entry["weight_bps"] = int(row["weight_bps"])
        if row.get("planned_usdc") is not None:
            planned = Decimal(str(row["planned_usdc"]))
            entry["planned_usdc"] = _format_amount(planned, asset=BUNDLE_PARENT_LOCK_ASSET)
        normalized.append(entry)
    return sorted(normalized, key=lambda item: item["asset"])


def compute_bundle_parent_snapshot_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


@dataclass(frozen=True)
class BundleParentSnapshot:
    version: str
    source: str
    asset: str
    scopes: dict[str, dict[str, str]]
    funding: dict[str, str]
    planned_allocations: list[dict[str, Any]]
    execution_buffer_usdc: str
    balance_snapshot_hash: str
    bundle_execution_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "asset": self.asset,
            "bundle_execution_id": self.bundle_execution_id,
            "scopes": self.scopes,
            "funding": self.funding,
            "planned_allocations": self.planned_allocations,
            "execution_buffer_usdc": self.execution_buffer_usdc,
            "balance_snapshot_hash": self.balance_snapshot_hash,
        }


@dataclass(frozen=True)
class BuildBundleParentSnapshotResult:
    skipped: bool
    snapshot: BundleParentSnapshot | None


@dataclass(frozen=True)
class AcquireBundleParentLockResult:
    acquired: bool
    skipped: bool
    idempotent: bool
    lock: TransactionProductLock | None
    snapshot: BundleParentSnapshot | None


@dataclass(frozen=True)
class ReleaseBundleParentLockResult:
    released: bool
    skipped: bool
    idempotent: bool
    lock: TransactionProductLock | None


def build_bundle_parent_snapshot(
    *,
    person_id: UUID,
    wallet_id: UUID,
    funding_amount_usdc: Decimal | str,
    planned_allocations: list[dict[str, Any]],
    pe_snapshot: CurrentPeScopeSnapshot,
    bundle_execution_id: UUID | None = None,
    execution_buffer_usdc: Decimal | str | None = None,
    entry_asset: str = BUNDLE_PARENT_LOCK_ASSET,
) -> BuildBundleParentSnapshotResult:
    """Snapshot canonique parent Bundle — metadata only (pas d'écriture intent en B2)."""
    funding = Decimal(str(funding_amount_usdc))
    buffer = (
        Decimal(str(execution_buffer_usdc))
        if execution_buffer_usdc is not None
        else compute_execution_buffer(funding)
    )
    asset_norm = _normalize_asset(entry_asset)
    planned = _normalize_planned_allocations(planned_allocations)
    scopes = {
        "trading_available": _format_decimal_map(pe_snapshot.trading_available),
        "bundle_cash": _format_decimal_map(pe_snapshot.bundle_cash),
        "bundle_position": _format_decimal_map(pe_snapshot.bundle_position),
    }
    funding_block = {
        "amount_usdc": _format_amount(funding, asset=asset_norm),
        "entry_asset": asset_norm,
    }
    hash_payload = {
        "version": BUNDLE_PARENT_SNAPSHOT_VERSION,
        "person_id": str(person_id),
        "wallet_id": str(wallet_id),
        "asset": asset_norm,
        "bundle_execution_id": str(bundle_execution_id) if bundle_execution_id else None,
        "scopes": scopes,
        "funding": funding_block,
        "planned_allocations": planned,
        "execution_buffer_usdc": _format_amount(buffer, asset=asset_norm),
    }
    snapshot = BundleParentSnapshot(
        version=BUNDLE_PARENT_SNAPSHOT_VERSION,
        source="pe",
        asset=asset_norm,
        bundle_execution_id=str(bundle_execution_id) if bundle_execution_id else None,
        scopes=scopes,
        funding=funding_block,
        planned_allocations=planned,
        execution_buffer_usdc=_format_amount(buffer, asset=asset_norm),
        balance_snapshot_hash=compute_bundle_parent_snapshot_hash(hash_payload),
    )
    return BuildBundleParentSnapshotResult(skipped=False, snapshot=snapshot)


def build_bundle_parent_snapshot_if_enabled(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    funding_amount_usdc: Decimal | str,
    planned_allocations: list[dict[str, Any]],
    pe_snapshot: CurrentPeScopeSnapshot,
    bundle_execution_id: UUID | None = None,
    execution_buffer_usdc: Decimal | str | None = None,
    entry_asset: str = BUNDLE_PARENT_LOCK_ASSET,
) -> BuildBundleParentSnapshotResult:
    if not _bundle_locks_active(db, person_id):
        return BuildBundleParentSnapshotResult(skipped=True, snapshot=None)
    return build_bundle_parent_snapshot(
        person_id=person_id,
        wallet_id=wallet_id,
        funding_amount_usdc=funding_amount_usdc,
        planned_allocations=planned_allocations,
        pe_snapshot=pe_snapshot,
        bundle_execution_id=bundle_execution_id,
        execution_buffer_usdc=execution_buffer_usdc,
        entry_asset=entry_asset,
    )


def acquire_bundle_parent_lock(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    parent_intent_id: UUID,
    funding_amount_usdc: Decimal | str,
    planned_allocations: list[dict[str, Any]],
    pe_snapshot: CurrentPeScopeSnapshot,
    bundle_execution_id: UUID | None = None,
    ttl_seconds: int | None = None,
) -> AcquireBundleParentLockResult:
    """Lock S4 parent ``bundle_invest`` — scope ``bundle`` · asset USDC.

    Flag OFF ou personne hors allowlist → no-op strict (aucune ligne lock).
    Ne modifie pas ``pe_portfolios.metadata.bundle_invest_lock`` (legacy intact).
    """
    if not _bundle_locks_active(db, person_id):
        return AcquireBundleParentLockResult(
            acquired=False,
            skipped=True,
            idempotent=False,
            lock=None,
            snapshot=None,
        )

    snapshot_result = build_bundle_parent_snapshot(
        person_id=person_id,
        wallet_id=wallet_id,
        funding_amount_usdc=funding_amount_usdc,
        planned_allocations=planned_allocations,
        pe_snapshot=pe_snapshot,
        bundle_execution_id=bundle_execution_id,
    )

    lock_result: AcquireProductLockResult = acquire_product_lock(
        db,
        person_id=person_id,
        wallet_id=wallet_id,
        asset=BUNDLE_PARENT_LOCK_ASSET,
        scope=BUNDLE_PARENT_LOCK_SCOPE,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        intent_id=parent_intent_id,
        ttl_seconds=ttl_seconds,
    )

    return AcquireBundleParentLockResult(
        acquired=lock_result.acquired,
        skipped=lock_result.skipped,
        idempotent=lock_result.idempotent,
        lock=lock_result.lock,
        snapshot=snapshot_result.snapshot,
    )


def release_bundle_parent_lock(
    db: Session,
    *,
    person_id: UUID,
    wallet_id: UUID,
    parent_intent_id: UUID,
) -> ReleaseBundleParentLockResult:
    """Release lock parent scope bundle — flag/allowlist OFF → no-op."""
    if not _bundle_locks_active(db, person_id):
        return ReleaseBundleParentLockResult(
            released=False,
            skipped=True,
            idempotent=False,
            lock=None,
        )

    result: ReleaseProductLockResult = release_product_lock(
        db,
        intent_id=parent_intent_id,
        person_id=person_id,
        wallet_id=wallet_id,
        asset=BUNDLE_PARENT_LOCK_ASSET,
        scope=BUNDLE_PARENT_LOCK_SCOPE,
    )
    return ReleaseBundleParentLockResult(
        released=result.released,
        skipped=result.skipped,
        idempotent=result.idempotent,
        lock=result.lock,
    )


def resolve_bundle_scope_available(
    pe_snapshot: CurrentPeScopeSnapshot,
    *,
    asset: str = BUNDLE_PARENT_LOCK_ASSET,
) -> Decimal:
    """Projection PE scope bundle (cash + position) — lecture seule."""
    return resolve_available_from_pe_snapshot(
        pe_snapshot,
        asset=asset,
        scope=BUNDLE_PARENT_LOCK_SCOPE,
    )
