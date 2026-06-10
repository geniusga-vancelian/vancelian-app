"""Clôture intents bundle zombies — plus de status=active sur orphelins."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import (
    close_stale_bundle_invest_intents_for_portfolio,
)
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    LEGACY_REBALANCE_INTENT_PRODUCT,
    close_orphan_bundle_transaction_intents_for_portfolio,
    find_running_bundle_transaction_intent_for_portfolio,
)
from services.portfolio_engine.bundles.rebalancing_portfolio import (
    get_active_bundle_operation,
    reconcile_stale_bundle_portfolio_state,
)
from tests.test_bundle_invest_lock_orphan_fix import _seed_swap
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client


def _seed_orphan_rebalance_intent(
    db: Session,
    *,
    person_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    batch_id: str,
) -> TransactionIntent:
    intent = TransactionIntent(
        person_id=person_id,
        product_type=LEGACY_REBALANCE_INTENT_PRODUCT,
        operation_type="rebalance",
        idempotency_key=f"orphan-{batch_id}",
        status="running",
        metadata_json={
            "portfolio_id": str(portfolio_id),
            "batch_id": batch_id,
            "rebalance_execution_id": batch_id,
            "v3_status": "RUNNING",
            "operation_type": "rebalance",
        },
    )
    db.add(intent)
    db.flush()
    return intent


def test_close_all_orphan_rebalance_intents_without_running_v3(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_a = str(uuid.uuid4())
    batch_b = str(uuid.uuid4())
    _seed_orphan_rebalance_intent(
        db, person_id=pe.person_id, portfolio_id=portfolio.id, batch_id=batch_a,
    )
    _seed_orphan_rebalance_intent(
        db, person_id=pe.person_id, portfolio_id=portfolio.id, batch_id=batch_b,
    )

    closed = close_orphan_bundle_transaction_intents_for_portfolio(
        db, portfolio_id=portfolio.id,
    )
    assert len(closed) == 2
    assert find_running_bundle_transaction_intent_for_portfolio(
        db, portfolio_id=portfolio.id,
    ) is None


def test_get_active_returns_none_for_orphan_intent_without_v3(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    _seed_orphan_rebalance_intent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        batch_id=str(uuid.uuid4()),
    )

    active = get_active_bundle_operation(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    assert active["status"] == "none"


def test_reconcile_stale_closes_orphan_and_stale_invest_intent(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    _seed_orphan_rebalance_intent(
        db, person_id=pe.person_id, portfolio_id=portfolio.id, batch_id=batch_id,
    )

    expired_swap = _seed_swap(
        db,
        pe,
        portfolio_id=str(portfolio.id),
        batch_id=batch_id,
        status=SwapSessionStatus.EXPIRED.value,
    )
    invest_intent = TransactionIntent(
        person_id=pe.person_id,
        product_type="bundle_invest",
        operation_type="invest",
        idempotency_key=f"invest-{batch_id}",
        status="awaiting_signature",
        metadata_json={
            "bundle_id": str(portfolio.id),
            "batch_id": batch_id,
            "legs": [{"status": "pending", "swap_id": str(expired_swap.id)}],
        },
    )
    db.add(invest_intent)
    db.commit()

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalancing_portfolio._compute_drift_and_plan",
        lambda *a, **k: ({}, {"status": "no_action", "plan_hash": "h"}),
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.orchestrator.BundleOrchestrator._load_and_validate_portfolio",
        lambda *a, **k: portfolio,
    )

    result = reconcile_stale_bundle_portfolio_state(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    kinds = {a["kind"] for a in result["actions"]}
    assert "orphan_intent_closed" in kinds
    assert "stale_invest_intent_closed" in kinds
    assert result["active_operation"]["status"] == "none"
