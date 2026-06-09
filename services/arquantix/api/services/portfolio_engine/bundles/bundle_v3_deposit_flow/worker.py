"""Worker — traite les événements bundle.v3_rebalance_requested."""
from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from services.portfolio_engine.bundles.bundle_v3_deposit_flow.config import (
    bundle_v3_deposit_worker_enabled,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    process_v3_deposit_rebalance_outbox_event,
)
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.repository import TransactionOutboxRepository

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 10
DEFAULT_WORKER_ID = "bundle-v3-deposit-worker"
WORKER_ACTOR = "bundle_v3_deposit_outbox_worker"


def _worker_instance_id() -> str:
    host = socket.gethostname() or "local"
    pid = os.getpid()
    return f"{WORKER_ACTOR}:{host}:{pid}"


@dataclass(frozen=True)
class BundleV3DepositWorkerTickResult:
    processed: int
    failed: int
    skipped: bool
    polled: int = 0


def _process_polled_rows(db: Session, rows: list) -> tuple[int, int]:
    processed = 0
    failed = 0
    for row in rows:
        try:
            result = process_v3_deposit_rebalance_outbox_event(db, outbox=row)
            if result.get("terminal"):
                if row.status != OutboxEventStatus.PROCESSED.value:
                    row.status = OutboxEventStatus.PROCESSED.value
                row.processed_at = datetime.now(timezone.utc)
                row.locked_by = None
                row.locked_at = None
                db.flush()
                processed += 1
            else:
                # RUNNING — rebalance en cours : libérer le lock outbox, réessayer plus tard.
                TransactionOutboxRepository.release_processing_lock(db, row)
        except Exception as exc:
            failed += 1
            row.attempt_count = int(row.attempt_count or 0) + 1
            row.last_error = str(exc)[:2000]
            row.locked_by = None
            row.locked_at = None
            if row.attempt_count >= int(row.max_attempts or 10):
                row.status = OutboxEventStatus.DEAD_LETTER.value
            else:
                row.status = OutboxEventStatus.PENDING.value
                row.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            db.flush()
            logger.exception("bundle_v3_deposit_worker failed outbox=%s", row.id)
    return processed, failed


def process_bundle_v3_deposit_outbox(
    db: Session,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Point d'entrée ECS — poll ``bundle.v3_rebalance_requested`` (flag requis)."""
    if not bundle_v3_deposit_worker_enabled():
        return {
            "enabled": False,
            "polled": 0,
            "processed": 0,
            "failed": 0,
            "skipped": True,
        }

    locked_by = _worker_instance_id()
    rows = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        limit=limit,
        locked_by=locked_by,
    )
    processed, failed = _process_polled_rows(db, rows)
    if processed or failed or rows:
        db.commit()

    return {
        "enabled": True,
        "polled": len(rows),
        "processed": processed,
        "failed": failed,
        "skipped": False,
    }


def tick_bundle_v3_deposit_worker(
    db: Session,
    *,
    worker_id: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> BundleV3DepositWorkerTickResult:
    """Poll outbox et exécute rebalance V3 pour dépôts en file."""
    if not bundle_v3_deposit_worker_enabled():
        return BundleV3DepositWorkerTickResult(processed=0, failed=0, skipped=True, polled=0)

    locked_by = worker_id or _worker_instance_id()
    rows = TransactionOutboxRepository.poll_pending_events(
        db,
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        limit=batch_size,
        locked_by=locked_by,
    )
    processed, failed = _process_polled_rows(db, rows)
    return BundleV3DepositWorkerTickResult(
        processed=processed,
        failed=failed,
        skipped=False,
        polled=len(rows),
    )
