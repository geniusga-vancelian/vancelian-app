"""Maintenance sessions swap — expiration zombies + réconciliation LI.FI."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.lifi.swap_trace_service import log_swap_trace
from services.transaction_intents.lifi_intent_sync import on_swap_settlement_blocked

logger = logging.getLogger(__name__)

QUOTE_RECEIVED_MAX_AGE_MINUTES = 30
SUBMITTED_STUCK_MINUTES = 10


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    return int(raw) if raw.isdigit() else default


def expire_stale_swap_sessions(
    db: Session,
    *,
    dry_run: bool = True,
    limit: int = 200,
) -> dict[str, Any]:
    """Expire QUOTE_RECEIVED / AWAITING_SIGNATURE dont expires_at est dépassé."""
    now = datetime.now(timezone.utc)
    quote_max_age = timedelta(minutes=_env_int("SWAP_QUOTE_RECEIVED_MAX_AGE_MINUTES", QUOTE_RECEIVED_MAX_AGE_MINUTES))

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "expired_by_expires_at": 0,
        "expired_quote_received_stale": 0,
        "swap_ids": [],
    }

    candidates = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.status.in_(
                [
                    SwapSessionStatus.QUOTE_RECEIVED.value,
                    SwapSessionStatus.AWAITING_SIGNATURE.value,
                    SwapSessionStatus.PENDING.value,
                ]
            )
        )
        .order_by(PersonWalletSwap.updated_at.asc())
        .limit(limit)
        .all()
    )

    repo = PersonWalletSwapRepository()
    for swap in candidates:
        should_expire = False
        reason = ""

        if swap.expires_at and swap.expires_at <= now:
            should_expire = True
            reason = "expires_at_passed"
        elif (
            swap.status == SwapSessionStatus.QUOTE_RECEIVED.value
            and swap.created_at
            and swap.created_at <= now - quote_max_age
        ):
            should_expire = True
            reason = "quote_received_stale"

        if not should_expire:
            continue

        report["swap_ids"].append(str(swap.id))
        if reason == "expires_at_passed":
            report["expired_by_expires_at"] += 1
        else:
            report["expired_quote_received_stale"] += 1

        if dry_run:
            continue

        swap.status = SwapSessionStatus.EXPIRED.value
        swap.error_message = "Devis expiré — refaites une estimation."
        repo.append_audit(swap, {"event": "auto_expired", "reason": reason})
        from services.transaction_intents.lifi_intent_sync import on_swap_failed

        on_swap_failed(db, swap)
        log_swap_trace(
            db,
            swap,
            event="expired",
            status=SwapSessionStatus.EXPIRED.value,
            error_code="quote_expired",
            message=swap.error_message,
            source="swap_session_maintenance",
        )

    if not dry_run and report["swap_ids"]:
        db.commit()

    return report


def reconcile_stuck_submitted_swaps(
    db: Session,
    *,
    dry_run: bool = True,
    execute_service: Any | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Repoll LI.FI pour SUBMITTED bloqués ; marque reconciliation_required si incertain."""
    from services.lifi.lifi_execute_service import LifiExecuteService

    stuck_minutes = _env_int("SWAP_SUBMITTED_STUCK_MINUTES", SUBMITTED_STUCK_MINUTES)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stuck_minutes)
    svc = execute_service or LifiExecuteService()

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "polled": 0,
        "confirmed": 0,
        "failed": 0,
        "reconciliation_required": 0,
        "still_submitted": 0,
        "swap_ids": [],
    }

    rows = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.status == SwapSessionStatus.SUBMITTED.value,
            PersonWalletSwap.tx_hash.isnot(None),
            PersonWalletSwap.updated_at <= cutoff,
        )
        .order_by(PersonWalletSwap.updated_at.asc())
        .limit(limit)
        .all()
    )

    repo = PersonWalletSwapRepository()
    for swap in rows:
        report["swap_ids"].append(str(swap.id))
        if dry_run:
            report["polled"] += 1
            continue

        before = swap.status
        svc.refresh_lifi_status(db, swap)
        db.refresh(swap)
        report["polled"] += 1

        if swap.status == SwapSessionStatus.CONFIRMED.value:
            report["confirmed"] += 1
        elif swap.status == SwapSessionStatus.FAILED.value:
            report["failed"] += 1
        elif before == swap.status == SwapSessionStatus.SUBMITTED.value:
            repo.append_audit(
                swap,
                {
                    "event": "reconciliation_required",
                    "reason": "submitted_stuck",
                    "stuck_minutes": stuck_minutes,
                },
            )
            on_swap_settlement_blocked(db, swap, reason="submitted_stuck")
            log_swap_trace(
                db,
                swap,
                event="reconciliation_required",
                status=swap.status,
                error_code="submitted_stuck",
                tx_hash=swap.tx_hash,
                source="swap_session_maintenance",
            )
            report["reconciliation_required"] += 1
        else:
            report["still_submitted"] += 1

    if not dry_run and report["polled"] > 0:
        db.commit()

    return report


def reconcile_confirmed_without_ledger(
    db: Session,
    *,
    dry_run: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    """Swaps CONFIRMED sans settlement ledger → reconciliation_required."""
    from services.privy_wallet.models import PersonWalletDeposit

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "gaps": 0,
        "swap_ids": [],
    }

    rows = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
            PersonWalletSwap.tx_hash.isnot(None),
        )
        .order_by(PersonWalletSwap.confirmed_at.desc().nullslast())
        .limit(limit)
        .all()
    )

    repo = PersonWalletSwapRepository()
    for swap in rows:
        if swap_settlement_already_applied(swap):
            continue
        dep_count = (
            db.query(PersonWalletDeposit)
            .filter(
                PersonWalletDeposit.person_id == swap.person_id,
                PersonWalletDeposit.tx_hash == swap.tx_hash,
                PersonWalletDeposit.transaction_kind == "crypto_swap",
            )
            .count()
        )
        if dep_count > 0:
            continue

        report["gaps"] += 1
        report["swap_ids"].append(str(swap.id))
        if dry_run:
            continue

        repo.append_audit(
            swap,
            {"event": "reconciliation_required", "reason": "confirmed_without_ledger"},
        )
        on_swap_settlement_blocked(db, swap, reason="confirmed_without_ledger")
        log_swap_trace(
            db,
            swap,
            event="reconciliation_required",
            status=swap.status,
            error_code="confirmed_without_ledger",
            tx_hash=swap.tx_hash,
            source="swap_session_maintenance",
        )

    if not dry_run and report["gaps"] > 0:
        db.commit()

    return report


def reconcile_partial_settlements(
    db: Session,
    *,
    dry_run: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    """Réconcilie les swaps avec crédit destination sans débit source (webhook Privy / SUBMITTED bloqué)."""
    from services.lifi.lifi_swap_reconciliation import (
        find_partial_settlement_candidates,
        settle_lifi_swap_idempotently,
    )

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "candidates": 0,
        "reconciled": 0,
        "errors": 0,
        "swap_ids": [],
        "details": [],
    }

    for swap in find_partial_settlement_candidates(db, limit=limit):
        report["candidates"] += 1
        report["swap_ids"].append(str(swap.id))
        try:
            result = settle_lifi_swap_idempotently(db, swap, dry_run=dry_run)
            report["details"].append(
                {
                    "swap_id": result.swap_id,
                    "action": result.action,
                    "would_write": result.would_write,
                }
            )
            if result.action not in {"noop_already_settled", "noop_legs_complete"}:
                report["reconciled"] += 1
        except Exception as exc:
            report["errors"] += 1
            report["details"].append({"swap_id": str(swap.id), "error": str(exc)[:500]})
            logger.warning(
                "swap.partial_reconciliation.failed",
                extra={"swap_id": str(swap.id)},
                exc_info=True,
            )

    return report


def run_swap_session_maintenance(
    db: Session,
    *,
    dry_run: bool = True,
    execute_service: Any | None = None,
) -> dict[str, Any]:
    """Orchestration maintenance swap (appelée par tick DeFi)."""
    return {
        "expire_stale": expire_stale_swap_sessions(db, dry_run=dry_run),
        "reconcile_submitted": reconcile_stuck_submitted_swaps(
            db, dry_run=dry_run, execute_service=execute_service
        ),
        "reconcile_ledger_gaps": reconcile_confirmed_without_ledger(db, dry_run=dry_run),
        "reconcile_partial_settlements": reconcile_partial_settlements(db, dry_run=dry_run),
    }
