"""Verrou retrait bundle LI.FI — miroir de ``bundle_invest_lock``."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.portfolios.models import Portfolio

BUNDLE_WITHDRAW_LOCK_KEY = "bundle_withdraw_lock"
BUNDLE_ACTION_WITHDRAW = "withdraw"

WITHDRAW_PHASE_REQUESTED = "WITHDRAW_REQUESTED"
WITHDRAW_PHASE_UNWINDING = "UNWINDING"
WITHDRAW_PHASE_PARTIALLY_UNWOUND = "PARTIALLY_UNWOUND"
WITHDRAW_PHASE_READY_TO_RELEASE = "READY_TO_RELEASE"
WITHDRAW_PHASE_RELEASED = "RELEASED"
WITHDRAW_PHASE_FAILED_PARTIAL = "FAILED_PARTIAL"

ACTIVE_WITHDRAW_LOCK_STATUSES = frozenset({
    "withdraw_requested",
    "unwinding",
    "partially_unwound",
    "ready_to_release",
    "pending_signature",
    "signature_requested",
    "submitted",
    "pending_confirmation",
    "finalizing",
})

TERMINAL_WITHDRAW_LOCK_STATUSES = frozenset({
    "released",
    "failed_partial",
    "failed",
    "expired",
})


class BundleWithdrawAlreadyPendingError(Exception):
    def __init__(
        self,
        *,
        batch_id: str,
        lock_status: str,
        message: str = "A bundle withdrawal is already in progress",
    ) -> None:
        self.batch_id = batch_id
        self.lock_status = lock_status
        self.message = message
        super().__init__(message)

    def to_response(self) -> dict[str, Any]:
        return {
            "status": "already_pending",
            "batch_id": self.batch_id,
            "lock_status": self.lock_status,
            "message": self.message,
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_withdraw_lock(metadata: Optional[dict]) -> Optional[dict[str, Any]]:
    if not metadata or not isinstance(metadata, dict):
        return None
    raw = metadata.get(BUNDLE_WITHDRAW_LOCK_KEY)
    if not isinstance(raw, dict):
        return None
    if raw.get("bundle_action") != BUNDLE_ACTION_WITHDRAW:
        return None
    status = str(raw.get("status") or "").strip()
    if status in TERMINAL_WITHDRAW_LOCK_STATUSES:
        return None
    if status not in ACTIVE_WITHDRAW_LOCK_STATUSES:
        return None
    batch_id = str(raw.get("batch_id") or "").strip()
    if not batch_id:
        return None
    return raw


def load_portfolio_for_withdraw_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> Portfolio:
    row = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.client_id == client_id,
            Portfolio.status == "active",
        )
        .with_for_update()
        .first()
    )
    if row is None:
        from services.portfolio_engine.bundles.orchestrator import BundleOrchestratorError

        raise BundleOrchestratorError(f"portfolio_not_found: {portfolio_id}")
    return row


def assert_no_active_withdraw_lock(portfolio: Portfolio, client_id: UUID) -> None:
    lock = get_withdraw_lock(portfolio.metadata_)
    if lock is None:
        return
    lock_client = str(lock.get("client_id") or "")
    if lock_client and lock_client != str(client_id):
        return
    raise BundleWithdrawAlreadyPendingError(
        batch_id=str(lock["batch_id"]),
        lock_status=str(lock.get("status") or "withdraw_requested"),
    )


def acquire_withdraw_lock(
    db: Session,
    portfolio: Portfolio,
    *,
    client_id: UUID,
    batch_id: str,
    entry_instrument_id: str,
    entry_asset: str,
    requested_release_amount: str,
    full_withdraw: bool,
    withdraw_phase: str = WITHDRAW_PHASE_REQUESTED,
) -> dict[str, Any]:
    assert_no_active_withdraw_lock(portfolio, client_id)
    now = _utc_now_iso()
    lock = {
        "bundle_action": BUNDLE_ACTION_WITHDRAW,
        "client_id": str(client_id),
        "portfolio_id": str(portfolio.id),
        "batch_id": batch_id,
        "status": "withdraw_requested",
        "withdraw_phase": withdraw_phase,
        "entry_instrument_id": entry_instrument_id,
        "entry_asset": entry_asset,
        "requested_release_amount": requested_release_amount,
        "full_withdraw": full_withdraw,
        "released_amount": "0",
        "sell_legs_total": 0,
        "sell_legs_confirmed": 0,
        "sell_legs_failed": 0,
        "created_at": now,
        "updated_at": now,
    }
    _write_lock(portfolio, lock)
    db.add(portfolio)
    db.flush()
    return lock


def update_withdraw_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    status: Optional[str] = None,
    withdraw_phase: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    portfolio = load_portfolio_for_withdraw_lock(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    lock = get_withdraw_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id")) != batch_id:
        return None
    lock = dict(lock)
    if status is not None:
        lock["status"] = status
    if withdraw_phase is not None:
        lock["withdraw_phase"] = withdraw_phase
    lock["updated_at"] = _utc_now_iso()
    if extra:
        lock.update(extra)
    _write_lock(portfolio, lock)
    db.add(portfolio)
    db.flush()
    return lock


def clear_withdraw_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> None:
    portfolio = load_portfolio_for_withdraw_lock(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    lock = get_withdraw_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id")) != batch_id:
        return
    meta = dict(portfolio.metadata_ or {})
    meta.pop(BUNDLE_WITHDRAW_LOCK_KEY, None)
    portfolio.metadata_ = meta
    db.add(portfolio)
    db.flush()


def _write_lock(portfolio: Portfolio, lock: dict[str, Any]) -> None:
    meta = deepcopy(portfolio.metadata_) if isinstance(portfolio.metadata_, dict) else {}
    meta[BUNDLE_WITHDRAW_LOCK_KEY] = lock
    portfolio.metadata_ = meta


def get_active_withdraw_lock_for_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> Optional[dict[str, Any]]:
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.client_id == client_id,
        )
        .first()
    )
    if portfolio is None:
        return None
    lock = get_withdraw_lock(portfolio.metadata_)
    if lock is None:
        return None
    return dict(lock)
