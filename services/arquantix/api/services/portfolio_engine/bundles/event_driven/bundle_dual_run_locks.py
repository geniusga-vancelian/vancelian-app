"""B2b — Dual-run locks Bundle : legacy metadata + S4 parent scope=bundle.

Prérequis acquire : le lock legacy ``bundle_invest_lock`` est déjà posé par l'appelant.
En cas d'échec S4 → rollback legacy (``release_invest_lock`` terminal ``failed``) pour éviter lock zombie.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import (
    clear_invest_lock,
    get_invest_lock,
    release_invest_lock,
)
from services.portfolio_engine.bundles.event_driven.bundle_dual_run_config import (
    bundle_s4_parent_lock_dual_run_enabled,
)
from services.portfolio_engine.bundles.event_driven.bundle_product_locks import (
    acquire_bundle_parent_lock,
    release_bundle_parent_lock,
)
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.portfolio_engine.portfolios.models import Portfolio
from services.privy_wallet.repository import PersonCryptoWalletRepository
from services.product_locks.allowlist import product_locks_enabled_for_person
from services.product_locks.exceptions import ProductLockConflict
from services.product_locks.models import TransactionProductLock

logger = logging.getLogger(__name__)

LegacyTerminal = Literal["clear", "release_failed", "keep"]


def build_planned_allocations_preview(
    db: Session,
    *,
    allocations: list[Any],
    funding_amount: Decimal | str,
    normalize_asset_fn: Any,
) -> list[dict[str, Any]]:
    """Preview allocations planifiées (poids cibles) — lecture seule pour snapshot dual-run."""
    from services.portfolio_engine.instruments.models import Instrument

    funding = Decimal(str(funding_amount))
    if not allocations or funding <= 0:
        return []

    weights: list[tuple[str, Decimal]] = []
    for row in allocations:
        instrument_id = getattr(row, "instrument_id", None)
        target_weight = getattr(row, "target_weight", None)
        if instrument_id is None or target_weight is None:
            continue
        inst = db.query(Instrument).filter(Instrument.id == instrument_id).first()
        if inst is None:
            continue
        symbol = normalize_asset_fn(getattr(inst, "symbol", "") or "")
        if not symbol:
            continue
        weights.append((symbol, Decimal(str(target_weight))))

    if not weights:
        return []

    total = sum(weight for _, weight in weights)
    if total <= 0:
        return []

    preview: list[dict[str, Any]] = []
    for symbol, weight in weights:
        share = funding * weight / total
        preview.append(
            {
                "asset": symbol,
                "weight_bps": int((weight / total * Decimal("10000")).to_integral_value()),
                "planned_usdc": str(share),
            }
        )
    return preview


def resolve_bundle_parent_intent_id(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> UUID | None:
    from services.transaction_intents.repository import TransactionIntentRepository

    row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
    )
    return row.id if row is not None else None


@dataclass(frozen=True)
class BundleDualRunAcquireResult:
    dual_run_flag_on: bool
    s4_attempted: bool
    s4_acquired: bool
    s4_skipped: bool
    s4_idempotent: bool
    legacy_rolled_back: bool
    parent_intent_id: UUID | None
    lock: TransactionProductLock | None
    snapshot_hash: str | None
    skip_reason: str | None = None


@dataclass(frozen=True)
class BundleDualRunReleaseResult:
    dual_run_flag_on: bool
    s4_released: bool
    s4_skipped: bool
    s4_idempotent: bool
    legacy_cleared: bool
    legacy_released_failed: bool


def dual_run_s4_eligible(db: Session, person_id: UUID | None) -> bool:
    """Dual-run flag ON + Product Locks allowlist OK."""
    if not bundle_s4_parent_lock_dual_run_enabled():
        return False
    if person_id is None:
        return False
    return product_locks_enabled_for_person(db, person_id)


def resolve_bundle_dual_run_wallet_id(db: Session, person_id: UUID) -> UUID:
    wallets = PersonCryptoWalletRepository.list_active_for_person(db, person_id)
    if not wallets:
        raise ValueError(f"bundle_dual_run_wallet_missing:{person_id}")
    for wallet in wallets:
        if (wallet.provider or "").strip().lower() == "privy":
            return wallet.id
    return wallets[0].id


def _persist_parent_snapshot(
    db: Session,
    *,
    parent_intent_id: UUID,
    snapshot_dict: dict[str, Any],
) -> None:
    row = db.query(TransactionIntent).filter(TransactionIntent.id == parent_intent_id).first()
    if row is None:
        return
    meta = dict(row.metadata_json) if isinstance(row.metadata_json, dict) else {}
    meta["bundle_parent_snapshot"] = snapshot_dict
    meta["dual_run_s4_active"] = True
    row.metadata_json = meta
    db.add(row)
    db.flush()


def _rollback_legacy_invest_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> None:
    release_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        terminal_status="failed",
    )


def try_acquire_s4_after_legacy_invest_lock(
    db: Session,
    *,
    person_id: UUID | None,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
    batch_id: str,
    parent_intent_id: UUID | None,
    funding_amount_usdc: Decimal | str,
    planned_allocations: list[dict[str, Any]],
    pe_snapshot: CurrentPeScopeSnapshot | None = None,
    bundle_execution_id: UUID | None = None,
    wallet_id: UUID | None = None,
) -> BundleDualRunAcquireResult:
    """Tente le lock S4 parent après lock legacy — rollback legacy si S4 échoue."""
    flag_on = bundle_s4_parent_lock_dual_run_enabled()
    if not flag_on:
        return BundleDualRunAcquireResult(
            dual_run_flag_on=False,
            s4_attempted=False,
            s4_acquired=False,
            s4_skipped=True,
            s4_idempotent=False,
            legacy_rolled_back=False,
            parent_intent_id=parent_intent_id,
            lock=None,
            snapshot_hash=None,
            skip_reason="dual_run_flag_off",
        )

    legacy = get_invest_lock(portfolio.metadata_)
    if legacy is None or str(legacy.get("batch_id")) != batch_id:
        return BundleDualRunAcquireResult(
            dual_run_flag_on=True,
            s4_attempted=False,
            s4_acquired=False,
            s4_skipped=True,
            s4_idempotent=False,
            legacy_rolled_back=False,
            parent_intent_id=parent_intent_id,
            lock=None,
            snapshot_hash=None,
            skip_reason="legacy_lock_missing",
        )

    if parent_intent_id is None or person_id is None:
        return BundleDualRunAcquireResult(
            dual_run_flag_on=True,
            s4_attempted=False,
            s4_acquired=False,
            s4_skipped=True,
            s4_idempotent=False,
            legacy_rolled_back=False,
            parent_intent_id=parent_intent_id,
            lock=None,
            snapshot_hash=None,
            skip_reason="parent_intent_or_person_missing",
        )

    if not product_locks_enabled_for_person(db, person_id):
        return BundleDualRunAcquireResult(
            dual_run_flag_on=True,
            s4_attempted=False,
            s4_acquired=False,
            s4_skipped=True,
            s4_idempotent=False,
            legacy_rolled_back=False,
            parent_intent_id=parent_intent_id,
            lock=None,
            snapshot_hash=None,
            skip_reason="product_locks_not_enabled_for_person",
        )

    resolved_wallet = wallet_id or resolve_bundle_dual_run_wallet_id(db, person_id)
    snapshot_pe = pe_snapshot or read_current_pe_scope_snapshot(db, person_id)

    try:
        s4_result = acquire_bundle_parent_lock(
            db,
            person_id=person_id,
            wallet_id=resolved_wallet,
            parent_intent_id=parent_intent_id,
            funding_amount_usdc=funding_amount_usdc,
            planned_allocations=planned_allocations,
            pe_snapshot=snapshot_pe,
            bundle_execution_id=bundle_execution_id,
        )
    except ProductLockConflict:
        _rollback_legacy_invest_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        logger.warning(
            "bundle.dual_run.s4_conflict_legacy_rolled_back",
            extra={
                "person_id": str(person_id),
                "portfolio_id": str(portfolio_id),
                "batch_id": batch_id,
                "parent_intent_id": str(parent_intent_id),
            },
        )
        raise

    if not s4_result.acquired and not s4_result.idempotent:
        _rollback_legacy_invest_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        return BundleDualRunAcquireResult(
            dual_run_flag_on=True,
            s4_attempted=True,
            s4_acquired=False,
            s4_skipped=s4_result.skipped,
            s4_idempotent=False,
            legacy_rolled_back=True,
            parent_intent_id=parent_intent_id,
            lock=None,
            snapshot_hash=None,
            skip_reason="s4_acquire_failed",
        )

    if s4_result.snapshot is not None:
        _persist_parent_snapshot(
            db,
            parent_intent_id=parent_intent_id,
            snapshot_dict=s4_result.snapshot.to_dict(),
        )

    snapshot_hash = (
        s4_result.snapshot.balance_snapshot_hash if s4_result.snapshot is not None else None
    )
    return BundleDualRunAcquireResult(
        dual_run_flag_on=True,
        s4_attempted=True,
        s4_acquired=s4_result.acquired or s4_result.idempotent,
        s4_skipped=s4_result.skipped,
        s4_idempotent=s4_result.idempotent,
        legacy_rolled_back=False,
        parent_intent_id=parent_intent_id,
        lock=s4_result.lock,
        snapshot_hash=snapshot_hash,
    )


def release_bundle_dual_run_locks(
    db: Session,
    *,
    person_id: UUID | None,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    parent_intent_id: UUID | None,
    wallet_id: UUID | None = None,
    legacy_terminal: LegacyTerminal = "keep",
) -> BundleDualRunReleaseResult:
    """Release S4 (si dual-run actif) + action legacy demandée."""
    flag_on = bundle_s4_parent_lock_dual_run_enabled()
    s4_released = False
    s4_skipped = True
    s4_idempotent = False

    if flag_on and parent_intent_id is not None and person_id is not None:
        if product_locks_enabled_for_person(db, person_id):
            resolved_wallet = wallet_id or resolve_bundle_dual_run_wallet_id(db, person_id)
            s4_result = release_bundle_parent_lock(
                db,
                person_id=person_id,
                wallet_id=resolved_wallet,
                parent_intent_id=parent_intent_id,
            )
            s4_released = s4_result.released or s4_result.idempotent
            s4_skipped = s4_result.skipped
            s4_idempotent = s4_result.idempotent
            row = db.query(TransactionIntent).filter(TransactionIntent.id == parent_intent_id).first()
            if row is not None and isinstance(row.metadata_json, dict):
                meta = dict(row.metadata_json)
                meta.pop("dual_run_s4_active", None)
                row.metadata_json = meta
                db.add(row)
                db.flush()

    legacy_cleared = False
    legacy_released_failed = False
    if legacy_terminal == "clear":
        clear_invest_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        legacy_cleared = True
    elif legacy_terminal == "release_failed":
        release_invest_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            terminal_status="failed",
        )
        legacy_released_failed = True

    return BundleDualRunReleaseResult(
        dual_run_flag_on=flag_on,
        s4_released=s4_released,
        s4_skipped=s4_skipped,
        s4_idempotent=s4_idempotent,
        legacy_cleared=legacy_cleared,
        legacy_released_failed=legacy_released_failed,
    )
