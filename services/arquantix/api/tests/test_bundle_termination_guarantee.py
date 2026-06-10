"""Garanties de terminaison bundle — stuck swaps, DEAD_LETTER, cron reconcile."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.bundles.bundle_invest_lock import (
    force_expire_stuck_bundle_allocation_swaps,
    stuck_bundle_swap_ttl_minutes,
)
from services.portfolio_engine.bundles.bundle_stale_reconcile_worker import (
    bundle_stale_reconcile_cron_enabled,
    tick_bundle_stale_reconcile,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
    finalize_v3_deposit_outbox_dead_letter,
)
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.models import TransactionOutbox
from tests.test_bundle_invest_lock_orphan_fix import _bundle_swap_audit, _seed_swap
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client


def _stuck_swap(
    db: Session,
    pe,
    *,
    portfolio_id: str,
    batch_id: str,
    status: str = "CONFIRMING",
    age_minutes: int = 999,
) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=status,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=portfolio_id, batch_id=batch_id),
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=age_minutes),
        created_at=datetime.now(timezone.utc) - timedelta(minutes=age_minutes),
    )
    db.add(swap)
    db.flush()
    return swap


def test_force_expire_stuck_confirming_bundle_swap(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    swap = _stuck_swap(
        db,
        pe,
        portfolio_id=str(portfolio.id),
        batch_id=batch_id,
        status="CONFIRMING",
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.bundle_invest_lock.stuck_bundle_swap_ttl_minutes",
        lambda: 1,
    )
    mock_svc = MagicMock()
    mock_svc.refresh_lifi_status.side_effect = lambda _db, row: setattr(
        row, "status", "CONFIRMING",
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.bundle_invest_lock.LifiExecuteService",
        lambda: mock_svc,
    )

    expired = force_expire_stuck_bundle_allocation_swaps(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
    )
    assert expired == [str(swap.id)]
    db.refresh(swap)
    assert swap.status == SwapSessionStatus.EXPIRED.value


def test_finalize_dead_letter_releases_intent_and_lock(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    intent = TransactionIntent(
        person_id=pe.person_id,
        product_type="bundle_deposit_v3",
        operation_type="deposit_rebalance",
        idempotency_key=f"dl-{batch_id}",
        status="running",
        metadata_json={
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "v3_status": "RUNNING",
        },
    )
    db.add(intent)
    outbox = TransactionOutbox(
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        status=OutboxEventStatus.DEAD_LETTER.value,
        payload_json={
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "deposit_execution_id": batch_id,
            "batch_id": batch_id,
        },
        intent_id=None,
        attempt_count=10,
        max_attempts=10,
    )
    db.add(outbox)
    db.flush()
    outbox.intent_id = intent.id
    db.commit()

    released: list[bool] = []

    def _fake_release(*args, **kwargs):
        released.append(True)
        return True

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.release_bundle_transaction_v3_portfolio_operation",
        _fake_release,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.terminalize_stale_v3_rebalance_execution",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service.find_running_v3_rebalance_execution",
        lambda *a, **k: None,
    )

    result = finalize_v3_deposit_outbox_dead_letter(
        db,
        outbox=outbox,
        reason="test_dead_letter",
    )
    db.refresh(intent)
    assert result["v3_status"] == "FAILED"
    assert intent.status == "failed"
    assert released


def test_tick_bundle_stale_reconcile_disabled(monkeypatch):
    monkeypatch.setenv("BUNDLE_STALE_RECONCILE_CRON_ENABLED", "false")
    assert bundle_stale_reconcile_cron_enabled() is False


def test_tick_bundle_stale_reconcile_dry_run(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_STALE_RECONCILE_CRON_ENABLED", "true")
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": str(uuid.uuid4()),
            "status": "pending_signature",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.commit()

    result = tick_bundle_stale_reconcile(db, dry_run=True)
    assert result["enabled"] is True
    assert result["targets"] >= 1
