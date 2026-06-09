"""Tests — rebalancing_portfolio (abandon legacy lock + drift plan)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.bundles.rebalancing_portfolio import (
    abandon_legacy_invest_lock_for_rebalancing,
    preview_rebalancing_portfolio,
    rebalancing_portfolio,
)
from services.portfolio_engine.portfolios.models import Portfolio
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client


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


def test_rebalancing_abandons_lock_before_execute(db: Session):
    pe = make_linked_client(db)
    batch_id = str(uuid.uuid4())
    portfolio = _portfolio_with_legacy_lock(db, pe, batch_id=batch_id)
    db.commit()

    mock_result = {
        "v3_status": "NO_ACTION",
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
        return_value={"status": "no_action", "plan_hash": "p1", "sell_plan": [], "buy_plan": []},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.execute_v3_bundle_rebalance",
        return_value=mock_result,
    ) as execute_mock:
        out = rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)

    assert out["legacy_lock_abandoned"]["abandoned"] is True
    execute_mock.assert_called_once()
