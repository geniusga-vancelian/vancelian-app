#!/usr/bin/env bash
# Dry-run maintenance swap LI.FI en prod (lecture seule, aucune écriture DB).
# Utilise run_swap_session_maintenance si présent dans l'image, sinon réplique inline.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CMD='cd /app && python3 - <<'"'"'PYEOF'"'"'
import json
import main  # noqa: F401
from datetime import datetime, timedelta, timezone

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent

QUOTE_RECEIVED_MAX_AGE_MINUTES = 30
SUBMITTED_STUCK_MINUTES = 10


def _dry_run_replica(db):
    now = datetime.now(timezone.utc)
    quote_max_age = timedelta(minutes=QUOTE_RECEIVED_MAX_AGE_MINUTES)
    stuck_cutoff = now - timedelta(minutes=SUBMITTED_STUCK_MINUTES)

    expire_report = {
        "dry_run": True,
        "expired_by_expires_at": 0,
        "expired_quote_received_stale": 0,
        "swap_ids": [],
        "source": "inline_replica",
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
        .limit(200)
        .all()
    )
    for swap in candidates:
        reason = None
        if swap.expires_at and swap.expires_at <= now:
            reason = "expires_at_passed"
        elif (
            swap.status == SwapSessionStatus.QUOTE_RECEIVED.value
            and swap.created_at
            and swap.created_at <= now - quote_max_age
        ):
            reason = "quote_received_stale"
        if not reason:
            continue
        expire_report["swap_ids"].append(str(swap.id))
        if reason == "expires_at_passed":
            expire_report["expired_by_expires_at"] += 1
        else:
            expire_report["expired_quote_received_stale"] += 1

    submitted_report = {
        "dry_run": True,
        "polled": 0,
        "swap_ids": [],
        "source": "inline_replica",
    }
    submitted_rows = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.status == SwapSessionStatus.SUBMITTED.value,
            PersonWalletSwap.tx_hash.isnot(None),
            PersonWalletSwap.updated_at <= stuck_cutoff,
        )
        .order_by(PersonWalletSwap.updated_at.asc())
        .limit(50)
        .all()
    )
    for swap in submitted_rows:
        submitted_report["polled"] += 1
        submitted_report["swap_ids"].append(str(swap.id))

    ledger_report = {"dry_run": True, "gaps": 0, "swap_ids": [], "source": "inline_replica"}
    from services.privy_wallet.models import PersonWalletDeposit

    confirmed_rows = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
            PersonWalletSwap.tx_hash.isnot(None),
        )
        .order_by(PersonWalletSwap.confirmed_at.desc().nullslast())
        .limit(50)
        .all()
    )
    for swap in confirmed_rows:
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
        ledger_report["gaps"] += 1
        ledger_report["swap_ids"].append(str(swap.id))

    return {
        "expire_stale": expire_report,
        "reconcile_submitted": submitted_report,
        "reconcile_ledger_gaps": ledger_report,
    }


db = SessionLocal()
try:
    maintenance_source = "official"
    try:
        from services.lifi.swap_session_maintenance import run_swap_session_maintenance

        report = run_swap_session_maintenance(db, dry_run=True)
    except ImportError:
        maintenance_source = "inline_replica_pr15_not_deployed"
        report = _dry_run_replica(db)

    from sqlalchemy import func

    status_counts = dict(
        db.query(PersonWalletSwap.status, func.count())
        .group_by(PersonWalletSwap.status)
        .all()
    )
    intent_recon = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.product_type == "lifi_swap",
            TransactionIntent.status == "reconciliation_required",
        )
        .count()
    )

    out = {
        "maintenance_source": maintenance_source,
        "dry_run": True,
        "swap_maintenance": report,
        "current_db": {
            "swap_status_counts": status_counts,
            "expired_swaps_now": status_counts.get(SwapSessionStatus.EXPIRED.value, 0),
            "lifi_swap_intents_reconciliation_required": intent_recon,
        },
        "would_on_execute": {
            "expire_to_expired": len((report.get("expire_stale") or {}).get("swap_ids") or []),
            "submitted_stuck_candidates": (report.get("reconcile_submitted") or {}).get("polled", 0),
            "ledger_gap_candidates": (report.get("reconcile_ledger_gaps") or {}).get("gaps", 0),
        },
    }
    print(json.dumps(out, indent=2, default=str))
finally:
    db.close()
PYEOF'

exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$CMD"
