"""Read model bundle invest partiel — R4.5-E.2-A (lecture seule, aucune mutation)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_funding import (
    resolve_bundle_cash_leg_available,
)
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundles.bundle_invest_lock import (
    BUNDLE_INVEST_LOCK_KEY,
    invest_lock_ttl_minutes,
)
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from services.transaction_intents.enums import IntentStatus
from services.transaction_intents.repository import TransactionIntentRepository

ALLOCATION_ACTIONS = frozenset({"allocation", "invest", ""})

SWAP_CONFIRMED = SwapSessionStatus.CONFIRMED.value
SWAP_FAILED = SwapSessionStatus.FAILED.value
SWAP_EXPIRED = SwapSessionStatus.EXPIRED.value
SWAP_AWAITING_SIGNATURE = SwapSessionStatus.AWAITING_SIGNATURE.value
SWAP_SUBMITTED = SwapSessionStatus.SUBMITTED.value
SWAP_PENDING = SwapSessionStatus.PENDING.value
SWAP_QUOTE_RECEIVED = SwapSessionStatus.QUOTE_RECEIVED.value

PENDING_SWAP_STATUSES = frozenset({
    SWAP_PENDING,
    SWAP_QUOTE_RECEIVED,
    SWAP_AWAITING_SIGNATURE,
    SWAP_SUBMITTED,
})

STATUS_RECONCILIATION_REQUIRED = "reconciliation_required"
STATUS_PARTIAL_IN_PROGRESS = "partial_in_progress"
STATUS_COMPLETED = "completed"
STATUS_COMPLETED_WITH_CASH_RESIDUAL = "completed_with_cash_residual"
STATUS_IMPOSSIBLE = "impossible"
STATUS_NOT_FOUND = "not_found"

ACTION_RETRY_MISSING_LEG = "retry_missing_leg"
ACTION_COMPLETE_WITH_CASH_RESIDUAL = "complete_with_cash_residual"


class BundleReconciliationNotFoundError(Exception):
    """Batch ou portfolio introuvable pour ce client."""


def reconciliation_stale_progress_minutes() -> int:
    raw = (os.environ.get("BUNDLE_RECONCILIATION_STALE_PROGRESS_MINUTES") or "30").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 30


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def lock_age_minutes(lock: dict[str, Any], *, now: datetime | None = None) -> float | None:
    ref = lock.get("updated_at") or lock.get("created_at")
    dt = _parse_iso_datetime(str(ref) if ref else None)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    return round((now - dt).total_seconds() / 60.0, 2)


def read_raw_invest_lock(metadata: dict | None) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get(BUNDLE_INVEST_LOCK_KEY)
    return dict(raw) if isinstance(raw, dict) else None


def _normalize_swap_leg_status(swap_status: str) -> str:
    s = (swap_status or "").strip().upper()
    if s == SWAP_CONFIRMED:
        return "confirmed"
    if s in (SWAP_FAILED, SWAP_EXPIRED):
        return "failed"
    if s == SWAP_AWAITING_SIGNATURE:
        return "awaiting_signature"
    if s == SWAP_SUBMITTED:
        return "submitted"
    if s in (SWAP_PENDING, SWAP_QUOTE_RECEIVED):
        return "pending"
    return s.lower() or "unknown"


def _allocation_row_from_swap(swap: PersonWalletSwap) -> dict[str, Any]:
    return {
        "swap_id": str(swap.id),
        "asset": str(swap.to_asset or "").upper(),
        "status": _normalize_swap_leg_status(str(swap.status or "")),
        "amount_usdc": float(swap.amount_in or 0),
        "tx_hash": swap.tx_hash,
    }


def list_batch_allocation_swaps(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> list[PersonWalletSwap]:
    portfolio_id_str = str(portfolio_id)
    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.asc())
        .limit(500)
        .all()
    )
    out: list[PersonWalletSwap] = []
    for swap in swaps:
        if not is_bundle_internal_swap(swap):
            continue
        ctx = bundle_context_from_swap_audit(swap) or {}
        if str(ctx.get("portfolio_id") or "") != portfolio_id_str:
            continue
        if str(ctx.get("batch_id") or "") != batch_id:
            continue
        action = str(ctx.get("bundle_action") or "")
        if action not in ALLOCATION_ACTIONS:
            continue
        out.append(swap)
    return out


def _resolve_entry_instrument_id(db: Session, portfolio: Portfolio) -> UUID | None:
    from services.portfolio_engine.assets.models import Asset
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.products.models import ProductDefinition

    product = None
    if portfolio.origin_product_id:
        product = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.id == portfolio.origin_product_id)
            .first()
        )
    meta = product.metadata_ if product and isinstance(product.metadata_, dict) else {}
    entry_asset = str(meta.get("entry_asset_default") or "USDC").upper()
    asset = db.query(Asset).filter(Asset.symbol == entry_asset).first()
    if asset is None:
        return None
    instr = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )
    return instr.id if instr is not None else None


def _intent_for_batch(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> tuple[str | None, dict[str, Any] | None]:
    row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    )
    if row is None:
        return None, None
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return str(row.status or ""), meta


def is_lock_zombie(
    lock: dict[str, Any] | None,
    *,
    intent_status: str | None,
    allocation_swaps: list[PersonWalletSwap],
    now: datetime | None = None,
) -> bool:
    """Lock actif dépassant le TTL sans progression LI.FI récente (lecture seule)."""
    if lock is None:
        return False

    age = lock_age_minutes(lock, now=now)
    if age is None or age < invest_lock_ttl_minutes():
        return False

    intent_norm = (intent_status or "").strip().lower()
    lock_status = str(lock.get("status") or "").lower()
    partial_context = intent_norm in (
        IntentStatus.PARTIAL.value,
        IntentStatus.AWAITING_SIGNATURE.value,
        IntentStatus.SUBMITTED.value,
        "partial_pending",
        "signature_requested",
    ) or lock_status in (
        "signature_requested",
        "partial_pending",
        "pending_signature",
        "submitted",
        "pending_confirmation",
    )
    if not partial_context:
        if intent_norm in (IntentStatus.CONFIRMED.value, IntentStatus.FAILED.value):
            return False

    stale_cutoff = (now or datetime.now(timezone.utc)) - timedelta(
        minutes=reconciliation_stale_progress_minutes(),
    )
    has_confirmed = any(str(s.status) == SWAP_CONFIRMED for s in allocation_swaps)
    if not has_confirmed:
        return False

    stuck_swaps = [
        s for s in allocation_swaps if str(s.status) in PENDING_SWAP_STATUSES
    ]
    if not stuck_swaps:
        return age >= invest_lock_ttl_minutes()

    for swap in stuck_swaps:
        ref = swap.updated_at or swap.created_at
        if ref is None:
            return True
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        if ref <= stale_cutoff:
            return True
    return True


def resolve_reconciliation_status(
    *,
    intent_status: str | None,
    allocation_swaps: list[PersonWalletSwap],
    cash_residual_usdc: float,
    lock: dict[str, Any] | None,
    lock_zombie: bool,
) -> str:
    if not allocation_swaps:
        if cash_residual_usdc > 0 and intent_status:
            return STATUS_RECONCILIATION_REQUIRED
        return STATUS_IMPOSSIBLE

    confirmed = [s for s in allocation_swaps if str(s.status) == SWAP_CONFIRMED]
    pending = [s for s in allocation_swaps if str(s.status) in PENDING_SWAP_STATUSES]
    failed = [
        s for s in allocation_swaps
        if str(s.status) in (SWAP_FAILED, SWAP_EXPIRED)
    ]

    if lock_zombie:
        return STATUS_RECONCILIATION_REQUIRED

    if confirmed and pending:
        return STATUS_RECONCILIATION_REQUIRED

    if confirmed and failed and not pending:
        return STATUS_RECONCILIATION_REQUIRED

    if confirmed and not pending and not failed:
        if cash_residual_usdc > 0:
            return STATUS_COMPLETED_WITH_CASH_RESIDUAL
        return STATUS_COMPLETED

    if pending and not confirmed:
        return STATUS_PARTIAL_IN_PROGRESS

    return STATUS_IMPOSSIBLE


def derive_available_actions(
    status: str,
    *,
    allocation_swaps: list[PersonWalletSwap],
    cash_residual_usdc: float,
) -> list[str]:
    """Actions ops possibles (informatif — non exécuté en E.2-A)."""
    actions: list[str] = []
    has_confirmed = any(str(s.status) == SWAP_CONFIRMED for s in allocation_swaps)
    has_retryable = any(
        str(s.status) in (SWAP_AWAITING_SIGNATURE, SWAP_PENDING, SWAP_QUOTE_RECEIVED)
        for s in allocation_swaps
    )

    if status == STATUS_RECONCILIATION_REQUIRED:
        if has_retryable:
            actions.append(ACTION_RETRY_MISSING_LEG)
        if has_confirmed:
            actions.append(ACTION_COMPLETE_WITH_CASH_RESIDUAL)
    elif status == STATUS_PARTIAL_IN_PROGRESS and has_retryable:
        actions.append(ACTION_RETRY_MISSING_LEG)

    if cash_residual_usdc > 0 and has_confirmed and ACTION_COMPLETE_WITH_CASH_RESIDUAL not in actions:
        if status in (STATUS_RECONCILIATION_REQUIRED, STATUS_COMPLETED_WITH_CASH_RESIDUAL):
            actions.append(ACTION_COMPLETE_WITH_CASH_RESIDUAL)

    return actions


def build_bundle_reconciliation_state(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Agrège PE / swaps / intent / lock — strictement lecture seule."""
    batch_id = str(batch_id).strip()
    if not batch_id:
        raise ValueError("batch_id_required")

    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .first()
    )
    if portfolio is None:
        raise BundleReconciliationNotFoundError("portfolio_not_found")

    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None or client.person_id is None:
        raise BundleReconciliationNotFoundError("client_not_found")

    person_id = client.person_id
    swaps = list_batch_allocation_swaps(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
    intent_status, _intent_meta = _intent_for_batch(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
    if intent_status is None and not swaps:
        raise BundleReconciliationNotFoundError("batch_not_found")

    raw_lock = read_raw_invest_lock(portfolio.metadata_)
    lock_for_batch = (
        raw_lock
        if raw_lock is not None and str(raw_lock.get("batch_id") or "") == batch_id
        else None
    )

    entry_instrument_id = _resolve_entry_instrument_id(db, portfolio)
    cash_residual = Decimal("0")
    if entry_instrument_id is not None:
        cash_residual = resolve_bundle_cash_leg_available(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=entry_instrument_id,
        )
    cash_f = float(cash_residual)

    now = now or datetime.now(timezone.utc)
    lock_zombie = is_lock_zombie(
        lock_for_batch,
        intent_status=intent_status,
        allocation_swaps=swaps,
        now=now,
    )

    status = resolve_reconciliation_status(
        intent_status=intent_status,
        allocation_swaps=swaps,
        cash_residual_usdc=cash_f,
        lock=lock_for_batch,
        lock_zombie=lock_zombie,
    )

    confirmed_allocations = [
        _allocation_row_from_swap(s)
        for s in swaps
        if str(s.status) == SWAP_CONFIRMED
    ]
    pending_allocations = [
        _allocation_row_from_swap(s)
        for s in swaps
        if str(s.status) in PENDING_SWAP_STATUSES
    ]
    failed_allocations = [
        _allocation_row_from_swap(s)
        for s in swaps
        if str(s.status) in (SWAP_FAILED, SWAP_EXPIRED)
    ]

    actions = derive_available_actions(
        status,
        allocation_swaps=swaps,
        cash_residual_usdc=cash_f,
    )

    lock_assessment: dict[str, Any] = {
        "present": lock_for_batch is not None,
        "status": str(lock_for_batch.get("status") or "") if lock_for_batch else None,
        "age_minutes": lock_age_minutes(lock_for_batch, now=now) if lock_for_batch else None,
        "ttl_minutes": invest_lock_ttl_minutes(),
        "zombie": lock_zombie,
        "stale_progress_minutes": reconciliation_stale_progress_minutes(),
    }

    return {
        "read_only": True,
        "batch_id": batch_id,
        "portfolio_id": str(portfolio_id),
        "person_id": str(person_id),
        "status": status,
        "intent_status": intent_status,
        "cash_residual_usdc": cash_f,
        "confirmed_allocations": confirmed_allocations,
        "pending_allocations": pending_allocations,
        "failed_allocations": failed_allocations,
        "available_actions": actions,
        "lock": lock_assessment,
        "reconciliation_reason": _reconciliation_reason(
            status=status,
            lock_zombie=lock_zombie,
            intent_status=intent_status,
            pending_count=len(pending_allocations),
            confirmed_count=len(confirmed_allocations),
        ),
        "inspected_at": now.isoformat(),
    }


def _reconciliation_reason(
    *,
    status: str,
    lock_zombie: bool,
    intent_status: str | None,
    pending_count: int,
    confirmed_count: int,
) -> str | None:
    if status != STATUS_RECONCILIATION_REQUIRED:
        return None
    if lock_zombie:
        return "lock_ttl_exceeded_with_stuck_allocation"
    if confirmed_count > 0 and pending_count > 0:
        return "partial_allocation_with_pending_leg"
    if intent_status == IntentStatus.PARTIAL.value:
        return "intent_partial"
    return "partial_batch"
