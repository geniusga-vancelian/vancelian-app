"""Tests — intent transactionnel unifié bundle (deposit+rebalance / rebalance seul)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    BUNDLE_TRANSACTION_FLOW_VERSION,
    BUNDLE_TRANSACTION_INTENT_PRODUCT,
    BUNDLE_TRANSACTION_OPERATION_DEPOSIT_REBALANCE,
    BUNDLE_TRANSACTION_OPERATION_REBALANCE,
    PHASE_REBALANCING,
    create_bundle_transaction_intent,
    find_bundle_transaction_intent_by_rebalance_execution_id,
)
from services.portfolio_engine.bundles.rebalancing_portfolio import (
    preview_rebalancing_portfolio,
    rebalancing_portfolio,
)
from services.portfolio_engine.financial_operations.enums import (
    PortfolioFinancialOperationStatus,
    PortfolioFinancialOperationType,
)
from services.portfolio_engine.financial_operations.models import PortfolioFinancialOperation
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client


def test_create_bundle_transaction_intent_rebalance(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    execution_id = uuid.uuid4()
    intent = create_bundle_transaction_intent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        transaction_execution_id=execution_id,
        operation_type=BUNDLE_TRANSACTION_OPERATION_REBALANCE,
        phase=PHASE_REBALANCING,
    )
    assert intent.product_type == BUNDLE_TRANSACTION_INTENT_PRODUCT
    assert intent.operation_type == BUNDLE_TRANSACTION_OPERATION_REBALANCE
    meta = intent.metadata_json or {}
    assert meta["phase"] == PHASE_REBALANCING
    assert meta["transaction_execution_id"] == str(execution_id)


def test_find_intent_by_rebalance_execution_id(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    rebalance_id = str(uuid.uuid4())
    intent = create_bundle_transaction_intent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        transaction_execution_id=uuid.uuid4(),
        operation_type=BUNDLE_TRANSACTION_OPERATION_DEPOSIT_REBALANCE,
        phase=PHASE_REBALANCING,
        extra_metadata={"rebalance_execution_id": rebalance_id},
    )
    db.commit()
    found = find_bundle_transaction_intent_by_rebalance_execution_id(
        db,
        rebalance_execution_id=rebalance_id,
    )
    assert found is not None
    assert found.id == intent.id


def test_preview_flow_is_bundle_transaction_v1(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    db.commit()
    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value={"snapshot_hash": "h1", "entry_asset": "USDC"},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "p1", "sell_plan": [], "buy_plan": []},
    ):
        out = preview_rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)
    assert out["flow"] == BUNDLE_TRANSACTION_FLOW_VERSION


def test_rebalancing_acquires_bundle_transaction_v3_guard(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    db.commit()
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")

    mock_result = {
        "v3_status": "COMPLETED",
        "rebalance_execution_id": str(uuid.uuid4()),
        "batch_id": str(uuid.uuid4()),
        "sell_results": [],
        "buy_results": [],
    }
    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value={"snapshot_hash": "h1", "entry_asset": "USDC"},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "p1", "sell_plan": [], "buy_plan": []},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.abandon_legacy_invest_lock_for_rebalancing",
        return_value={"abandoned": False},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.execute_v3_bundle_rebalance",
        return_value=mock_result,
    ):
        rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)

    db.commit()
    intent = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.product_type == BUNDLE_TRANSACTION_INTENT_PRODUCT)
        .order_by(TransactionIntent.created_at.desc())
        .first()
    )
    assert intent is not None
    assert intent.operation_type == BUNDLE_TRANSACTION_OPERATION_REBALANCE

    released = (
        db.query(PortfolioFinancialOperation)
        .filter(
            PortfolioFinancialOperation.portfolio_id == portfolio.id,
            PortfolioFinancialOperation.operation_type
            == PortfolioFinancialOperationType.BUNDLE_TRANSACTION_V3.value,
            PortfolioFinancialOperation.status == PortfolioFinancialOperationStatus.RELEASED.value,
        )
        .count()
    )
    assert released == 1


def test_global_lock_blocks_second_bundle_transaction(db: Session, monkeypatch):
    from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
    from tests.test_product_locks_l2_engine import _migration_175_ready

    if not _migration_175_ready():
        pytest.skip("Migration 175 requise (transaction_product_locks).")

    pe = make_linked_client(db)
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )
    portfolio_a = _bundle_portfolio(db, pe.id)
    portfolio_b = _bundle_portfolio(db, pe.id)
    db.commit()
    monkeypatch.setenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "true")
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")

    first_intent = create_bundle_transaction_intent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio_a.id,
        transaction_execution_id=uuid.uuid4(),
        operation_type=BUNDLE_TRANSACTION_OPERATION_REBALANCE,
        phase=PHASE_REBALANCING,
    )
    from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
        acquire_bundle_transaction_global_lock_or_raise,
    )

    acquire_bundle_transaction_global_lock_or_raise(
        db,
        person_id=pe.person_id,
        intent_id=first_intent.id,
    )
    db.commit()

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value={"snapshot_hash": "h1", "entry_asset": "USDC"},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "p1", "sell_plan": [], "buy_plan": []},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.abandon_legacy_invest_lock_for_rebalancing",
        return_value={"abandoned": False},
    ):
        from services.product_locks.exceptions import TransactionInProgress409

        with pytest.raises(TransactionInProgress409):
            rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio_b.id)
