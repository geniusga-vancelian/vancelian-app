"""Tests — rebalancing_portfolio (abandon legacy lock + drift plan + financial guard)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.bundles.rebalancing_portfolio import (
    abandon_legacy_invest_lock_for_rebalancing,
    cash_rebalance_required_body,
    portfolio_rebalancing_required_body,
    preflight_rebalancing_portfolio,
    preview_rebalancing_portfolio,
    rebalancing_portfolio,
    should_use_portfolio_rebalancing,
)
from services.portfolio_engine.financial_operations.enums import (
    PortfolioFinancialOperationStatus,
    PortfolioFinancialOperationType,
)
from services.portfolio_engine.financial_operations.exceptions import (
    PortfolioFinancialOperationInProgress409,
)
from services.portfolio_engine.financial_operations.models import PortfolioFinancialOperation
from services.portfolio_engine.portfolios.models import Portfolio
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client

MAJORS_CASH_USDC = "29.870000"
MAJORS_INVESTED_USDC = "70.130000"
MAJORS_LEGACY_BATCH = "10d688bb-0000-4000-8000-000000000001"


def _portfolio_with_legacy_lock(db: Session, pe, *, batch_id: str) -> Portfolio:
    portfolio = _bundle_portfolio(db, pe.id)
    row = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    now = datetime.now(timezone.utc).isoformat()
    row.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": "pending_signature",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(row)
    db.flush()
    return portfolio


def _majors_drift_snapshot() -> dict:
    return {
        "snapshot_hash": "majors-snap",
        "entry_asset": "USDC",
        "invested_value_usdc": MAJORS_INVESTED_USDC,
        "cash_value_usdc": MAJORS_CASH_USDC,
        "target_assets": [
            {
                "asset": "ETH",
                "instrument_id": str(uuid.uuid4()),
                "delta_value_usdc": "-17.000000",
                "drift_bps": -1100,
                "target_weight_bps": 3000,
            },
        ],
        "non_target_assets": [],
    }


def _majors_rebalance_plan() -> dict:
    return {
        "status": "ok",
        "plan_hash": "majors-plan",
        "snapshot_hash": "majors-snap",
        "sell_plan": [],
        "buy_plan": [
            {
                "asset": "ETH",
                "instrument_id": str(uuid.uuid4()),
                "amount_usdc": "17.000000",
                "action": "buy",
                "funded_by": "cash_leg",
            },
        ],
    }


def test_abandon_legacy_invest_lock(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_legacy_lock(db, pe, batch_id=batch_id)
    db.commit()

    result = abandon_legacy_invest_lock_for_rebalancing(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    assert result["abandoned"] is True
    assert result["batch_id"] == batch_id


def test_preview_returns_asset_lines(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    db.commit()

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value={
            "snapshot_hash": "h1",
            "entry_asset": "USDC",
            "invested_value_usdc": "10",
            "cash_value_usdc": "20",
            "target_assets": [],
            "non_target_assets": [],
        },
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value={
            "status": "ok",
            "plan_hash": "p1",
            "sell_plan": [],
            "buy_plan": [{"asset": "ETH", "instrument_id": str(uuid.uuid4()), "amount_usdc": "5", "action": "buy"}],
        },
    ):
        out = preview_rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)

    assert out["flow"] == "bundle_portfolio_rebalance_v1"
    assert len(out["asset_lines"]) == 1
    assert out["asset_lines"][0]["asset"] == "ETH"


def test_preflight_majors_scenario_can_execute(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _portfolio_with_legacy_lock(
        db, pe, batch_id=MAJORS_LEGACY_BATCH,
    )
    db.commit()
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value=_majors_drift_snapshot(),
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value=_majors_rebalance_plan(),
    ):
        out = preflight_rebalancing_portfolio(
            db, client_id=pe.id, portfolio_id=portfolio.id,
        )

    assert out["can_execute"] is True
    assert out["would_abandon_legacy_lock"] is True
    assert out["rebalance_plan"]["status"] == "ok"
    assert len(out["rebalance_plan"]["buy_plan"]) == 1


def test_preflight_blocks_when_financial_operation_active(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    db.commit()
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")

    now = datetime.now(timezone.utc)
    other_exec = uuid.uuid4()
    db.add(
        PortfolioFinancialOperation(
            portfolio_id=portfolio.id,
            operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST.value,
            execution_id=other_exec,
            status=PortfolioFinancialOperationStatus.ACTIVE.value,
            started_at=now,
            expires_at=now + timedelta(minutes=30),
        ),
    )
    db.commit()

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value=_majors_drift_snapshot(),
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value=_majors_rebalance_plan(),
    ):
        out = preflight_rebalancing_portfolio(
            db, client_id=pe.id, portfolio_id=portfolio.id,
        )

    assert out["can_execute"] is False
    assert out["blockers"][0]["code"] == "portfolio_financial_operation_in_progress"


def test_rebalancing_abandons_lock_and_acquires_guard(db: Session, monkeypatch):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_legacy_lock(db, pe, batch_id=batch_id)
    db.commit()
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")

    mock_result = {
        "v3_status": "COMPLETED",
        "rebalance_execution_id": str(uuid.uuid4()),
        "batch_id": str(uuid.uuid4()),
        "sell_results": [],
        "buy_results": [{"asset": "ETH", "status": "completed", "amount_usdc": "5"}],
    }

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value={"snapshot_hash": "h1", "entry_asset": "USDC"},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "p1", "sell_plan": [], "buy_plan": []},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.execute_v3_bundle_rebalance",
        return_value=mock_result,
    ) as execute_mock:
        out = rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)

    assert out["legacy_lock_abandoned"]["abandoned"] is True
    assert out["financial_operation_execution_id"]
    execute_mock.assert_called_once()
    db.commit()

    active = (
        db.query(PortfolioFinancialOperation)
        .filter(
            PortfolioFinancialOperation.portfolio_id == portfolio.id,
            PortfolioFinancialOperation.status == PortfolioFinancialOperationStatus.ACTIVE.value,
        )
        .count()
    )
    assert active == 0


def test_rebalancing_conflicts_with_active_invest_guard(db: Session, monkeypatch):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    db.commit()
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")

    now = datetime.now(timezone.utc)
    db.add(
        PortfolioFinancialOperation(
            portfolio_id=portfolio.id,
            operation_type=PortfolioFinancialOperationType.BUNDLE_INVEST.value,
            execution_id=uuid.uuid4(),
            status=PortfolioFinancialOperationStatus.ACTIVE.value,
            started_at=now,
            expires_at=now + timedelta(minutes=30),
        ),
    )
    db.commit()

    with pytest.raises(PortfolioFinancialOperationInProgress409):
        rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)


def test_should_use_portfolio_rebalancing_with_legacy_lock(db: Session):
    pe = make_linked_client(db)
    portfolio = _portfolio_with_legacy_lock(
        db, pe, batch_id=MAJORS_LEGACY_BATCH,
    )
    db.commit()

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.is_v3_deposit_batch",
        return_value=False,
    ):
        assert should_use_portfolio_rebalancing(
            db, client_id=pe.id, portfolio_id=portfolio.id,
        ) is True


def test_redirect_response_bodies():
    reb = portfolio_rebalancing_required_body()
    assert reb["error_code"] == "portfolio_rebalancing_required"
    cash = cash_rebalance_required_body(batch_id="10d688bb")
    assert cash["error_code"] == "cash_rebalance_required"
    assert cash["batch_id"] == "10d688bb"
