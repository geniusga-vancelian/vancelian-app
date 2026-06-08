"""Verrou investissement bundle LI.FI (client + portfolio + action=invest).

Stockage dans ``pe_portfolios.metadata.bundle_invest_lock`` — pas de table dédiée (Phase 2.5).
Préfigure reserved balances / operation lock.
"""
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

BUNDLE_INVEST_LOCK_KEY = "bundle_invest_lock"
BUNDLE_BATCH_RECOVERY_KEY = "bundle_batch_recovery"
BUNDLE_ACTION_INVEST = "invest"

AUDIT_ACTION_EXPIRED_REQUOTE = "bundle.invest_expired_requote"

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

# Statuts récupérables — ne bloquent pas un nouvel invest (non listés dans ACTIVE).
RECOVERABLE_INVEST_LOCK_STATUSES = frozenset({
    "partial",
    "failed",
    "expired",
})

AUDIT_ACTION_LOCK_REACQUIRED = "bundle.invest_lock_reacquired"
AUDIT_ACTION_RECONCILE_SKIPPED = "bundle.invest_lock_reconcile_skipped_pending_work"

BLOCKING_BUNDLE_SWAP_STATUSES = frozenset({
    "PENDING",
    "QUOTE_RECEIVED",
    "AWAITING_SIGNATURE",
    "SUBMITTED",
    "CONFIRMING",
    "PROCESSING",
    "PARTIAL",
})

BLOCKING_BUNDLE_SWAP_ACTIONS = frozenset({"allocation", "invest", ""})


class BundleInvestLockMissingWhileBatchActiveError(Exception):
    """Lock metadata absent alors qu'un batch bundle a encore du travail pending."""

    def __init__(self, *, batch_id: str, portfolio_id: str) -> None:
        self.batch_id = batch_id
        self.portfolio_id = portfolio_id
        super().__init__(
            f"invest_lock_missing_while_batch_active: portfolio={portfolio_id} batch={batch_id}",
        )


def invest_lock_ttl_minutes() -> int:
    raw = (os.environ.get("BUNDLE_INVEST_LOCK_TTL_MINUTES") or "120").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 120


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
        if _batch_has_blocking_invest_work(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        ):
            return reacquire_invest_lock_for_batch(
                db,
                portfolio=portfolio,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status=status,
                extra=extra,
                reason="update_invest_lock_status",
            )
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


def transition_invest_lock_recovery_batch(
    db: Session,
    *,
    portfolio: Portfolio,
    client_id: UUID,
    portfolio_id: UUID,
    old_batch_id: str,
    new_batch_id: str,
    status: str = "pending_signature",
    funding_amount: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Bascule le lock invest vers un batch recovery (re-quote expired legs)."""
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None or str(lock.get("batch_id") or "").strip() != old_batch_id:
        raise BundleInvestLockMissingWhileBatchActiveError(
            batch_id=old_batch_id,
            portfolio_id=str(portfolio_id),
        )
    now = _utc_now_iso()
    new_lock = dict(lock)
    new_lock.update({
        "batch_id": new_batch_id,
        "status": status,
        "updated_at": now,
        "recovery_from_batch_id": old_batch_id,
        "recovery_status": "recovery_started",
    })
    if funding_amount is not None:
        new_lock["funding_amount"] = funding_amount
    if extra:
        new_lock.update(extra)
    _write_lock(portfolio, new_lock)
    db.add(portfolio)
    db.flush()
    return dict(new_lock)


def resolve_existing_recovery_batch(
    metadata: Optional[dict],
    *,
    lock: dict[str, Any],
) -> tuple[Optional[str], Optional[str]]:
    """Retourne ``(source_batch_id, recovery_batch_id)`` si recovery déjà démarré."""
    recovery_from = str(lock.get("recovery_from_batch_id") or "").strip()
    current = str(lock.get("batch_id") or "").strip()
    if recovery_from and current:
        return recovery_from, current

    recoveries = dict((metadata or {}).get(BUNDLE_BATCH_RECOVERY_KEY) or {})
    if current in recoveries:
        recovery_batch_id = str(recoveries[current].get("recovery_batch_id") or "").strip()
        if recovery_batch_id:
            return current, recovery_batch_id
    return None, None


def record_batch_recovery_status(
    portfolio: Portfolio,
    *,
    old_batch_id: str,
    new_batch_id: str,
    status: str = "requoted",
    reason: str = "expired_invest_legs",
) -> None:
    """Trace recovery sur le portfolio — pas de cleanup DB des swaps expirés."""
    meta = dict(portfolio.metadata_ or {})
    recoveries = dict(meta.get(BUNDLE_BATCH_RECOVERY_KEY) or {})
    recoveries[old_batch_id] = {
        "status": status,
        "recovery_batch_id": new_batch_id,
        "reason": reason,
        "requoted_at": _utc_now_iso(),
    }
    meta[BUNDLE_BATCH_RECOVERY_KEY] = recoveries
    portfolio.metadata_ = meta


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


def _portfolio_pending_bundle_allocation_batch_ids(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
) -> set[str]:
    """Batch_ids avec swaps bundle allocation encore non terminaux sur ce portfolio."""
    from services.lifi.models import PersonWalletSwap
    from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

    portfolio_key = str(portfolio_id)
    batch_ids: set[str] = set()
    swaps = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.person_id == person_id,
            PersonWalletSwap.status.in_(list(BLOCKING_BUNDLE_SWAP_STATUSES)),
        )
        .all()
    )
    for swap in swaps:
        ctx = bundle_context_from_swap_audit(swap)
        if not ctx:
            continue
        if str(ctx.get("portfolio_id") or "") != portfolio_key:
            continue
        if not ctx.get("bundle_execution"):
            continue
        action = str(ctx.get("bundle_action") or "")
        if action not in BLOCKING_BUNDLE_SWAP_ACTIONS:
            continue
        bid = str(ctx.get("batch_id") or "").strip()
        if bid:
            batch_ids.add(bid)
    return batch_ids


def portfolio_has_pending_bundle_allocation_swaps(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> bool:
    person_id = _resolve_person_id(db, client_id)
    if person_id is None:
        return False
    return bool(
        _portfolio_pending_bundle_allocation_batch_ids(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        )
    )


def find_active_bundle_batch_ids_for_portfolio(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> list[str]:
    """Batch_ids actifs (swaps allocation pending) pour un portfolio — ordre stable."""
    person_id = _resolve_person_id(db, client_id)
    if person_id is None:
        return []
    return sorted(
        _portfolio_pending_bundle_allocation_batch_ids(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        )
    )


def _batch_funding_hints(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> dict[str, Any]:
    from services.transaction_intents.repository import TransactionIntentRepository

    row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    )
    if row is None:
        return {}
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "funding_amount": meta.get("funding_amount"),
        "funding_asset": meta.get("funding_asset"),
        "entry_instrument_id": meta.get("entry_instrument_id"),
    }


def reacquire_invest_lock_for_batch(
    db: Session,
    *,
    portfolio: Portfolio,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    status: str = "pending_signature",
    extra: Optional[dict[str, Any]] = None,
    reason: str = "batch_pending_work",
) -> dict[str, Any]:
    """Réécrit bundle_invest_lock quand le batch a encore du travail LI.FI actif."""
    person_id = _resolve_person_id(db, client_id)
    hints = (
        _batch_funding_hints(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        if person_id is not None
        else {}
    )
    now = _utc_now_iso()
    lock = {
        "bundle_action": BUNDLE_ACTION_INVEST,
        "client_id": str(client_id),
        "portfolio_id": str(portfolio_id),
        "batch_id": batch_id,
        "status": status,
        "entry_instrument_id": hints.get("entry_instrument_id"),
        "funding_asset": hints.get("funding_asset"),
        "funding_amount": hints.get("funding_amount"),
        "created_at": now,
        "updated_at": now,
        "reacquired": True,
        "reacquired_reason": reason,
    }
    if extra:
        lock.update(extra)
    _write_lock(portfolio, lock)
    db.add(portfolio)
    db.flush()

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action=AUDIT_ACTION_LOCK_REACQUIRED,
        actor_id=f"bundle-invest-lock:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "batch_id": batch_id,
            "status": status,
            "reason": reason,
        },
    )
    logger.info(
        "bundle_invest_lock.reacquired batch=%s portfolio=%s reason=%s",
        batch_id,
        portfolio_id,
        reason,
    )
    return dict(lock)


def _build_recoverable_lock_snapshot(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
) -> dict[str, Any]:
    """Snapshot read-only du lock attendu pour un batch pending (sans écriture DB)."""
    person_id = _resolve_person_id(db, client_id)
    hints = (
        _batch_funding_hints(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        if person_id is not None
        else {}
    )
    now = _utc_now_iso()
    return {
        "bundle_action": BUNDLE_ACTION_INVEST,
        "client_id": str(client_id),
        "portfolio_id": str(portfolio_id),
        "batch_id": batch_id,
        "status": "pending_signature",
        "entry_instrument_id": hints.get("entry_instrument_id"),
        "funding_asset": hints.get("funding_asset"),
        "funding_amount": hints.get("funding_amount"),
        "created_at": now,
        "updated_at": now,
        "synthetic": True,
    }


def peek_bundle_invest_lock_state(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> dict[str, Any]:
    """Lecture seule — aucune reconcile / clear / commit."""
    lock = get_active_invest_lock_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if lock is not None:
        return {
            "status": "active",
            "lock": lock,
            "resume_available": True,
            "read_only": True,
        }

    active_batches = find_active_bundle_batch_ids_for_portfolio(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    if not active_batches:
        return {"status": "none", "read_only": True}
    if len(active_batches) > 1:
        return {
            "status": "ambiguous",
            "active_batches": active_batches,
            "read_only": True,
            "message": "multiple_active_bundle_batches",
        }

    batch_id = active_batches[0]
    return {
        "status": "active",
        "lock": _build_recoverable_lock_snapshot(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        ),
        "recovered_from_pending_batch": True,
        "resume_available": True,
        "read_only": True,
    }


def _log_reconcile_skipped_pending_work(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    pending_batches: set[str],
) -> None:
    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action=AUDIT_ACTION_RECONCILE_SKIPPED,
        actor_id=f"bundle-invest-lock:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "lock_batch_id": batch_id,
            "pending_batches": sorted(pending_batches),
        },
    )


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


def _swap_batch_has_live_invest_work(
    db: Session,
    *,
    person_id: UUID,
    batch_id: str,
) -> bool:
    """Swap bundle encore en attente signature ou confirmation on-chain."""
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
        if ctx.get("bundle_execution"):
            return True
    return False


def expire_stale_invest_lock_if_safe(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
) -> bool:
    """Marque un verrou invest stale comme ``expired`` si aucun swap vivant ne le justifie.

    La cash leg reste intacte — état récupérable via rebalance / nouvel invest.
    """
    lock = get_invest_lock(portfolio.metadata_)
    if lock is None:
        return False

    lock_client = str(lock.get("client_id") or "")
    if lock_client and lock_client != str(client_id):
        return False

    age = _lock_age_minutes(lock)
    if age < invest_lock_ttl_minutes():
        return False

    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        return False

    person_id = _resolve_person_id(db, client_id)
    if person_id is not None and _swap_batch_has_live_invest_work(
        db,
        person_id=person_id,
        batch_id=batch_id,
    ):
        return False

    if _batch_has_blocking_invest_work(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    ):
        return False

    if person_id is not None:
        pending_batches = _portfolio_pending_bundle_allocation_batch_ids(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        )
        if pending_batches:
            _log_reconcile_skipped_pending_work(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                pending_batches=pending_batches,
            )
            return False

    release_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        terminal_status="expired",
    )

    from services.portfolio_engine.hardening.audit_service import AuditService

    AuditService.log_success(
        db,
        entity_type="portfolio",
        entity_id=str(portfolio_id),
        action="bundle.invest_lock_expired",
        actor_id=f"bundle-invest-lock:{batch_id}",
        metadata={
            "client_id": str(client_id),
            "portfolio_id": str(portfolio_id),
            "batch_id": batch_id,
            "previous_status": str(lock.get("status") or ""),
            "lock_age_minutes": round(age, 2),
            "ttl_minutes": invest_lock_ttl_minutes(),
            "cash_leg_preserved": True,
        },
    )
    db.refresh(portfolio)
    logger.info(
        "bundle_invest_lock.expired batch=%s portfolio=%s age_min=%.1f",
        batch_id,
        portfolio_id,
        age,
    )
    person_id = _resolve_person_id(db, client_id)
    if person_id is not None:
        from services.portfolio_engine.bundle_ledger.service import record_recovery_event

        record_recovery_event(
            db,
            person_id=person_id,
            bundle_portfolio_id=portfolio_id,
            batch_id=batch_id,
            reason="invest_lock_ttl_expired",
            lock_type="invest",
            previous_status=str(lock.get("status") or ""),
            metadata={
                "lock_age_minutes": round(age, 2),
                "ttl_minutes": invest_lock_ttl_minutes(),
            },
        )
    return True


def reconcile_or_expire_idle_invest_lock(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    portfolio: Portfolio,
) -> bool:
    """Expire un lock stale puis nettoie un lock sans travail LI.FI actif."""
    expired = expire_stale_invest_lock_if_safe(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        portfolio=portfolio,
    )
    if expired:
        return True
    return reconcile_idle_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        portfolio=portfolio,
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
        person_id = _resolve_person_id(db, client_id)
        if person_id is not None:
            pending_batches = _portfolio_pending_bundle_allocation_batch_ids(
                db,
                person_id=person_id,
                portfolio_id=portfolio_id,
            )
            if pending_batches:
                _log_reconcile_skipped_pending_work(
                    db,
                    client_id=client_id,
                    portfolio_id=portfolio_id,
                    batch_id="",
                    pending_batches=pending_batches,
                )
                return False
        meta = dict(portfolio.metadata_ or {})
        meta.pop(BUNDLE_INVEST_LOCK_KEY, None)
        portfolio.metadata_ = meta
        db.add(portfolio)
        db.flush()
        return True

    person_id = _resolve_person_id(db, client_id)
    if person_id is not None:
        pending_batches = _portfolio_pending_bundle_allocation_batch_ids(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        )
        if pending_batches:
            _log_reconcile_skipped_pending_work(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                pending_batches=pending_batches,
            )
            return False

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
    """Autorise le retrait si le verrou invest est absent, expiré ou sans travail en cours."""
    return reconcile_or_expire_idle_invest_lock(
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
    """Nettoie ou expire un verrou invest stale avant un nouvel investissement ou rebalance."""
    portfolio = load_portfolio_for_invest_lock(
        db, client_id=client_id, portfolio_id=portfolio_id,
    )
    return reconcile_or_expire_idle_invest_lock(
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
