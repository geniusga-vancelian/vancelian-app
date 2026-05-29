"""Verrou retrait bundle LI.FI — miroir de ``bundle_invest_lock``."""
from __future__ import annotations

import logging
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.portfolios.models import Portfolio

logger = logging.getLogger(__name__)

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
    "pending_signature",
    "signature_requested",
    "submitted",
    "pending_confirmation",
    "finalizing",
})

# États récupérables — finalize / release partiel possible, ne bloquent pas un nouveau retrait.
RECOVERABLE_WITHDRAW_LOCK_STATUSES = frozenset({
    "partially_unwound",
    "ready_to_release",
    "failed_partial",
})

BLOCKING_WITHDRAW_LOCK_STATUSES = ACTIVE_WITHDRAW_LOCK_STATUSES

TERMINAL_WITHDRAW_LOCK_STATUSES = frozenset({
    "released",
    "failed",
    "expired",
})


def withdraw_lock_ttl_minutes() -> int:
    raw = (os.environ.get("BUNDLE_WITHDRAW_LOCK_TTL_MINUTES") or "120").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 120


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


def _parse_lock_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _lock_age_minutes(lock: dict[str, Any]) -> float:
    ref = lock.get("updated_at") or lock.get("created_at")
    dt = _parse_lock_datetime(str(ref) if ref else None)
    if dt is None:
        return 0.0
    return (datetime.now(timezone.utc) - dt).total_seconds() / 60.0


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
    if status not in BLOCKING_WITHDRAW_LOCK_STATUSES and status not in RECOVERABLE_WITHDRAW_LOCK_STATUSES:
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
    status = str(lock.get("status") or "")
    if status not in BLOCKING_WITHDRAW_LOCK_STATUSES:
        return
    raise BundleWithdrawAlreadyPendingError(
        batch_id=str(lock["batch_id"]),
        lock_status=status or "withdraw_requested",
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


def release_withdraw_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    terminal_status: str,
) -> None:
    allowed = TERMINAL_WITHDRAW_LOCK_STATUSES | RECOVERABLE_WITHDRAW_LOCK_STATUSES
    if terminal_status not in allowed:
        terminal_status = "failed"
    portfolio = load_portfolio_for_withdraw_lock(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    lock = get_withdraw_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id")) != batch_id:
        return
    lock = dict(lock)
    lock["status"] = terminal_status
    lock["updated_at"] = _utc_now_iso()
    lock["released_at"] = lock["updated_at"]
    meta = dict(portfolio.metadata_ or {})
    meta[BUNDLE_WITHDRAW_LOCK_KEY] = lock
    portfolio.metadata_ = meta
    db.add(portfolio)
    db.flush()


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


def _resolve_person_id(db: Session, client_id: UUID) -> Optional[UUID]:
    from services.portfolio_engine.clients.models import Client

    row = db.query(Client).filter(Client.id == client_id).first()
    return row.person_id if row is not None else None


def _swap_batch_has_live_withdraw_sell_work(
    db: Session,
    *,
    person_id: UUID,
    batch_id: str,
) -> bool:
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

    live_statuses = {
        SwapSessionStatus.SUBMITTED.value,
        SwapSessionStatus.AWAITING_SIGNATURE.value,
    }
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status.in_(list(live_statuses)),
        )
        .all()
    )
    for swap in swaps:
        ctx = bundle_context_from_swap_audit(swap)
        if not ctx or str(ctx.get("batch_id")) != batch_id:
            continue
        action = str(ctx.get("bundle_action") or "").strip().lower()
        if action in ("withdraw_sell", "withdraw", "") and ctx.get("bundle_execution"):
            return True
    return False


def expire_stale_withdraw_lock_if_safe(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
) -> bool:
    """Expire un verrou retrait stale sans sell vivant — pas de release auto vers self-trading."""
    lock = get_withdraw_lock(portfolio.metadata_)
    if lock is None:
        return False

    lock_client = str(lock.get("client_id") or "")
    if lock_client and lock_client != str(client_id):
        return False

    age = _lock_age_minutes(lock)
    if age < withdraw_lock_ttl_minutes():
        return False

    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        return False

    person_id = _resolve_person_id(db, client_id)
    if person_id is not None and _swap_batch_has_live_withdraw_sell_work(
        db,
        person_id=person_id,
        batch_id=batch_id,
    ):
        return False

    terminal = "expired"

    release_withdraw_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        terminal_status=terminal,
    )

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action="bundle.withdraw_lock_expired",
        actor_id=f"bundle-withdraw-lock:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "batch_id": batch_id,
            "previous_status": str(lock.get("status") or ""),
            "previous_phase": str(lock.get("withdraw_phase") or ""),
            "lock_age_minutes": round(age, 2),
            "ttl_minutes": withdraw_lock_ttl_minutes(),
            "terminal_status": terminal,
            "no_auto_release_to_self_trading": True,
        },
    )
    db.refresh(portfolio)
    logger.info(
        "bundle_withdraw_lock.expired batch=%s portfolio=%s age_min=%.1f status=%s",
        batch_id,
        portfolio_id,
        age,
        terminal,
    )
    if person_id is not None:
        from services.portfolio_engine.bundle_ledger.service import record_recovery_event

        record_recovery_event(
            db,
            person_id=person_id,
            bundle_portfolio_id=portfolio_id,
            batch_id=batch_id,
            reason="withdraw_lock_ttl_expired",
            lock_type="withdraw",
            previous_status=str(lock.get("status") or ""),
            metadata={
                "previous_phase": str(lock.get("withdraw_phase") or ""),
                "lock_age_minutes": round(age, 2),
                "ttl_minutes": withdraw_lock_ttl_minutes(),
                "no_auto_release_to_self_trading": True,
            },
        )
    return True


def reconcile_or_expire_idle_withdraw_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
) -> bool:
    """Expire un lock withdraw stale ; retourne True si plus de lock actif."""
    expired = expire_stale_withdraw_lock_if_safe(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        portfolio=portfolio,
    )
    if expired:
        return True
    return get_withdraw_lock(portfolio.metadata_) is None


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
