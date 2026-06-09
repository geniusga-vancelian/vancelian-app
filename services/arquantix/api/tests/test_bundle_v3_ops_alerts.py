"""Tests alertes ops Bundle V3 — outbox PENDING / guard ACTIVE."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.ops_alerts import (
    OUTBOX_EVENT_TYPE,
    audit_bundle_v3_deposit_ops,
    bundle_v3_ops_alerts_for_tick,
)
from services.transaction_outbox.enums import OutboxEventStatus
from services.transaction_outbox.models import TransactionOutbox
from tests.conftest import make_linked_client


def _migrations_ready() -> bool:
    try:
        with engine.connect() as conn:
            for table in ("transaction_outbox", "portfolio_financial_operations"):
                row = conn.execute(
                    sa.text(
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :t"
                    ),
                    {"t": table},
                ).fetchone()
                if row is None:
                    return False
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migrations_ready(),
    reason="Migrations 173+178 requises.",
)


def _outbox_row(
    db: Session,
    *,
    portfolio_id: str,
    batch_id: str,
    created_at: datetime,
) -> TransactionOutbox:
    pe = make_linked_client(db)
    intent = TransactionIntent(
        person_id=pe.person_id,
        product_type="bundle_invest",
        operation_type="invest",
        idempotency_key=f"ops-alert-{uuid.uuid4()}",
        status="created",
    )
    db.add(intent)
    db.flush()
    row = TransactionOutbox(
        intent_id=intent.id,
        event_type=OUTBOX_EVENT_TYPE,
        status=OutboxEventStatus.PENDING.value,
        payload_json={"portfolio_id": portfolio_id, "batch_id": batch_id},
        next_retry_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    db.execute(
        sa.text("UPDATE transaction_outbox SET created_at = :created_at WHERE id = :id"),
        {"created_at": created_at, "id": row.id},
    )
    db.flush()
    return row


def test_ops_alerts_stale_pending_outbox_critical(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_V3_OUTBOX_PENDING_ALERT_MINUTES", "10")
    portfolio_id = str(uuid.uuid4())
    batch_id = str(uuid.uuid4())
    stale_at = datetime.now(timezone.utc) - timedelta(minutes=15)
    row = _outbox_row(db, portfolio_id=portfolio_id, batch_id=batch_id, created_at=stale_at)

    audit = audit_bundle_v3_deposit_ops(db)
    assert audit["pending_outbox_count"] >= 1
    codes = [a["code"] for a in audit["alerts"]]
    assert "bundle_v3_outbox_pending_stale" in codes
    stale = [a for a in audit["alerts"] if a.get("outbox_id") == str(row.id)]
    assert stale and stale[0]["level"] == "critical"


def test_ops_alerts_fresh_outbox_no_critical(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_V3_OUTBOX_PENDING_ALERT_MINUTES", "10")
    portfolio_id = str(uuid.uuid4())
    batch_id = str(uuid.uuid4())
    row = _outbox_row(
        db,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        created_at=datetime.now(timezone.utc),
    )

    alerts = bundle_v3_ops_alerts_for_tick(db)
    assert not any(a.get("outbox_id") == str(row.id) for a in alerts)
