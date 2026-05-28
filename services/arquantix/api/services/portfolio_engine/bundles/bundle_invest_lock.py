"""Verrou investissement bundle LI.FI (client + portfolio + action=invest).

Stockage dans ``pe_portfolios.metadata.bundle_invest_lock`` — pas de table dédiée (Phase 2.5).
Préfigure reserved balances / operation lock.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.portfolios.models import Portfolio

BUNDLE_INVEST_LOCK_KEY = "bundle_invest_lock"
BUNDLE_ACTION_INVEST = "invest"

ACTIVE_INVEST_LOCK_STATUSES = frozenset({
    "pending_signature",
    "signature_requested",
    "submitted",
    "pending_confirmation",
    "finalizing",
    "partial_pending",
})

TERMINAL_INVEST_LOCK_STATUSES = frozenset({
    "completed",
    "failed",
    "expired",
})


class BundleInvestAlreadyPendingError(Exception):
    """Un investissement bundle est déjà en cours pour ce portfolio."""

    def __init__(
        self,
        *,
        batch_id: str,
        lock_status: str,
        message: str = "A bundle investment is already in progress",
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


def get_invest_lock(metadata: Optional[dict]) -> Optional[dict[str, Any]]:
    if not metadata or not isinstance(metadata, dict):
        return None
    raw = metadata.get(BUNDLE_INVEST_LOCK_KEY)
    if not isinstance(raw, dict):
        return None
    if raw.get("bundle_action") != BUNDLE_ACTION_INVEST:
        return None
    status = str(raw.get("status") or "").strip()
    if status in TERMINAL_INVEST_LOCK_STATUSES:
        return None
    if status not in ACTIVE_INVEST_LOCK_STATUSES:
        return None
    batch_id = str(raw.get("batch_id") or "").strip()
    if not batch_id:
        return None
    return raw


def load_portfolio_for_invest_lock(
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


def assert_no_active_invest_lock(portfolio: Portfolio, client_id: UUID) -> None:
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None:
        return
    lock_client = str(lock.get("client_id") or "")
    if lock_client and lock_client != str(client_id):
        return
    raise BundleInvestAlreadyPendingError(
        batch_id=str(lock["batch_id"]),
        lock_status=str(lock.get("status") or "pending_signature"),
    )


def acquire_invest_lock(
    db: Session,
    portfolio: Portfolio,
    *,
    client_id: UUID,
    batch_id: str,
    entry_instrument_id: Optional[str] = None,
    status: str = "pending_signature",
    funding_asset: Optional[str] = None,
    funding_amount: Optional[str] = None,
) -> dict[str, Any]:
    assert_no_active_invest_lock(portfolio, client_id)
    now = _utc_now_iso()
    lock = {
        "bundle_action": BUNDLE_ACTION_INVEST,
        "client_id": str(client_id),
        "portfolio_id": str(portfolio.id),
        "batch_id": batch_id,
        "status": status,
        "entry_instrument_id": entry_instrument_id,
        "funding_asset": funding_asset,
        "funding_amount": funding_amount,
        "created_at": now,
        "updated_at": now,
    }
    _write_lock(portfolio, lock)
    db.add(portfolio)
    db.flush()
    return lock


def update_invest_lock_status(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    status: str,
    extra: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    portfolio = load_portfolio_for_invest_lock(db, client_id=client_id, portfolio_id=portfolio_id)
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id")) != batch_id:
        return None
    lock = dict(lock)
    lock["status"] = status
    lock["updated_at"] = _utc_now_iso()
    if extra:
        lock.update(extra)
    _write_lock(portfolio, lock)
    db.add(portfolio)
    db.flush()
    return lock


def release_invest_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    terminal_status: str,
) -> None:
    if terminal_status not in TERMINAL_INVEST_LOCK_STATUSES:
        terminal_status = "failed"
    portfolio = load_portfolio_for_invest_lock(db, client_id=client_id, portfolio_id=portfolio_id)
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id")) != batch_id:
        return
    lock = dict(lock)
    lock["status"] = terminal_status
    lock["updated_at"] = _utc_now_iso()
    lock["released_at"] = lock["updated_at"]
    meta = dict(portfolio.metadata_ or {})
    meta[BUNDLE_INVEST_LOCK_KEY] = lock
    portfolio.metadata_ = meta
    db.add(portfolio)
    db.flush()


def clear_invest_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> None:
    """Retire le verrou actif (batch terminé côté client)."""
    portfolio = load_portfolio_for_invest_lock(db, client_id=client_id, portfolio_id=portfolio_id)
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id")) != batch_id:
        return
    meta = dict(portfolio.metadata_ or {})
    meta.pop(BUNDLE_INVEST_LOCK_KEY, None)
    portfolio.metadata_ = meta
    db.add(portfolio)
    db.flush()


def _resolve_person_id(db: Session, client_id: UUID) -> Optional[UUID]:
    from services.portfolio_engine.clients.models import Client

    row = db.query(Client).filter(Client.id == client_id).first()
    return row.person_id if row is not None else None


def _reconcile_stale_intent_legs_for_batch(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> None:
    """Aligne les legs intent sur l'état réel des swaps (EXPIRED/FAILED → leg failed)."""
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.transaction_intents.bundle_intent_sync import (
        LEG_CONFIRMED,
        LEG_FAILED,
        _normalize_legs,
    )
    from services.transaction_intents.repository import TransactionIntentRepository

    row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
    )
    if row is None:
        return

    legs = _normalize_legs((row.metadata_json or {}).get("legs"))
    if not legs:
        return

    terminal_swap = {
        SwapSessionStatus.CONFIRMED.value,
        SwapSessionStatus.FAILED.value,
        SwapSessionStatus.EXPIRED.value,
    }
    changed = False
    for leg in legs:
        leg_status = str(leg.get("status") or "pending")
        if leg_status in (LEG_CONFIRMED, LEG_FAILED):
            continue
        swap_id_raw = str(leg.get("swap_id") or "").strip()
        if not swap_id_raw:
            leg["status"] = LEG_FAILED
            changed = True
            continue
        try:
            swap_uuid = UUID(swap_id_raw)
        except ValueError:
            leg["status"] = LEG_FAILED
            changed = True
            continue
        swap = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.id == swap_uuid,
                PersonWalletSwap.person_id == person_id,
            )
            .first()
        )
        if swap is None:
            leg["status"] = LEG_FAILED
            changed = True
            continue
        if swap.status == SwapSessionStatus.CONFIRMED.value:
            leg["status"] = LEG_CONFIRMED
            changed = True
        elif swap.status in terminal_swap:
            leg["status"] = LEG_FAILED
            changed = True

    if not changed:
        return

    meta = dict(row.metadata_json or {})
    meta["legs"] = legs
    row.metadata_json = meta
    db.add(row)
    db.flush()


def _intent_batch_has_pending_legs(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> bool:
    from services.transaction_intents.bundle_intent_sync import (
        LEG_CONFIRMED,
        LEG_FAILED,
        _normalize_legs,
    )
    from services.transaction_intents.repository import TransactionIntentRepository

    row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
    )
    if row is None:
        return False
    legs = _normalize_legs((row.metadata_json or {}).get("legs"))
    if not legs:
        return False
    terminal = {LEG_CONFIRMED, LEG_FAILED}
    return any(str(leg.get("status") or "pending") not in terminal for leg in legs)


def _swap_batch_has_pending_allocation(
    db: Session,
    *,
    person_id: UUID,
    batch_id: str,
) -> bool:
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap
    from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

    pending_statuses = {
        SwapSessionStatus.PENDING.value,
        SwapSessionStatus.QUOTE_RECEIVED.value,
        SwapSessionStatus.AWAITING_SIGNATURE.value,
        SwapSessionStatus.SUBMITTED.value,
    }
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status.in_(list(pending_statuses)),
        )
        .all()
    )
    blocking_actions = {"allocation", "invest", ""}
    for swap in swaps:
        ctx = bundle_context_from_swap_audit(swap)
        if not ctx or str(ctx.get("batch_id")) != batch_id:
            continue
        action = str(ctx.get("bundle_action") or "")
        if action in blocking_actions:
            return True
    return False


def _batch_has_blocking_invest_work(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> bool:
    person_id = _resolve_person_id(db, client_id)
    if person_id is None:
        return False
    _reconcile_stale_intent_legs_for_batch(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    )
    if _intent_batch_has_pending_legs(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    ):
        return True
    return _swap_batch_has_pending_allocation(
        db,
        person_id=person_id,
        batch_id=batch_id,
    )


def reconcile_idle_invest_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
) -> bool:
    """Retire un verrou invest obsolète (fund OK, plus de travail LI.FI actif).

    Returns True when no blocking invest lock remains.
    """
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None:
        return True
    lock_client = str(lock.get("client_id") or "")
    if lock_client and lock_client != str(client_id):
        return False

    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        meta = dict(portfolio.metadata_ or {})
        meta.pop(BUNDLE_INVEST_LOCK_KEY, None)
        portfolio.metadata_ = meta
        db.add(portfolio)
        db.flush()
        return True

    if _batch_has_blocking_invest_work(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    ):
        return False

    clear_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
    db.refresh(portfolio)
    return True


def reconcile_idle_invest_lock_for_withdraw(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
) -> bool:
    """Autorise le retrait si le verrou invest est absent ou sans travail en cours."""
    return reconcile_idle_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        portfolio=portfolio,
    )


def reconcile_idle_invest_lock_for_invest(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> bool:
    """Nettoie un verrou invest stale avant un nouvel investissement ou rebalance."""
    portfolio = load_portfolio_for_invest_lock(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    return reconcile_idle_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        portfolio=portfolio,
    )


def get_active_invest_lock_for_portfolio(
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
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None:
        return None
    return dict(lock)


def _write_lock(portfolio: Portfolio, lock: dict[str, Any]) -> None:
    meta = deepcopy(portfolio.metadata_) if isinstance(portfolio.metadata_, dict) else {}
    meta[BUNDLE_INVEST_LOCK_KEY] = lock
    portfolio.metadata_ = meta
