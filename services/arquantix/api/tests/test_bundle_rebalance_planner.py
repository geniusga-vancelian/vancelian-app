"""Tests Bundle Rebalancing Planner — V3 PR-2."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.rebalance_planner import (
    MIN_REBALANCE_DELTA_USDC,
    plan_bundle_rebalance_from_drift,
)

from conftest import make_linked_client
from tests.test_bundle_allocation_phase5a import (
    _bundle_with_allocations,
    _instrument_for_asset,
)
from tests.test_bundle_drift_engine import _FixedPriceResolver, _credit_cash, _credit_spot


def _majors_weights() -> dict[str, Decimal]:
    return {
        "BTC": Decimal("0.500000"),
        "ETH": Decimal("0.300000"),
        "LINK": Decimal("0.066667"),
        "AAVE": Decimal("0.066667"),
        "UNI": Decimal("0.066666"),
    }


def _majors_prices() -> dict[str, Decimal]:
    return {
        "USDC": Decimal("0.92"),
        "BTC": Decimal("95000"),
        "ETH": Decimal("3200"),
        "LINK": Decimal("14"),
        "AAVE": Decimal("180"),
        "UNI": Decimal("6"),
    }


def _seed_majors_spot(db: Session, portfolio_id) -> None:
    _credit_spot(db, portfolio_id, _instrument_for_asset(db, "BTC").id, "0.0005185000")
    _credit_spot(db, portfolio_id, _instrument_for_asset(db, "ETH").id, "0.0054700000")
    _credit_spot(db, portfolio_id, _instrument_for_asset(db, "LINK").id, "0.4700000000")
    _credit_spot(db, portfolio_id, _instrument_for_asset(db, "AAVE").id, "0.0365000000")
    _credit_spot(db, portfolio_id, _instrument_for_asset(db, "UNI").id, "0.6230000000")


def test_drift_uses_invested_assets_weight_basis(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    resolver = _FixedPriceResolver(_majors_prices())
    _seed_majors_spot(db, portfolio.id)
    _credit_cash(db, portfolio.id, usdc.id, "29.866638")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    assert snap["weight_basis"] == "invested_assets"
    assert Decimal(snap["cash_value_usdc"]) == Decimal("29.866638")
    assert Decimal(snap["invested_value_usdc"]) > 0
    assert Decimal(snap["portfolio_value_usdc"]) == (
        Decimal(snap["invested_value_usdc"]) + Decimal(snap["cash_value_usdc"])
    )

    by_asset = {r["asset"]: r for r in snap["target_assets"]}
    assert by_asset["BTC"]["action_hint"] == "sell"
    assert by_asset["ETH"]["action_hint"] == "buy"
    assert Decimal(by_asset["ETH"]["delta_value_usdc"]) > 0


def test_cash_residual_sell_plan_empty_buy_eth_uni(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    resolver = _FixedPriceResolver(_majors_prices())
    _seed_majors_spot(db, portfolio.id)
    _credit_cash(db, portfolio.id, usdc.id, "29.866638")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    plan = plan_bundle_rebalance_from_drift(snap)

    assert plan["status"] == "ok"
    assert plan["sell_plan"] == []
    assert plan["weight_basis"] == "invested_assets"
    assert plan["cash_funding_source"] == "separate"

    buy_assets = {row["asset"] for row in plan["buy_plan"]}
    assert "ETH" in buy_assets
    assert "UNI" in buy_assets
    assert "BTC" not in buy_assets

    total_buy = sum(Decimal(r["amount_usdc"]) for r in plan["buy_plan"])
    assert total_buy <= Decimal(snap["cash_value_usdc"])
    assert total_buy >= MIN_REBALANCE_DELTA_USDC


def test_cash_only_deploy_by_target_weights(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.7"), "ETH": Decimal("0.3")},
    )
    resolver = _FixedPriceResolver(
        {"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")},
    )
    _credit_cash(db, portfolio.id, usdc.id, "100")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    plan = plan_bundle_rebalance_from_drift(snap)

    assert plan["sell_plan"] == []
    assert len(plan["buy_plan"]) == 2
    btc_buy = next(r for r in plan["buy_plan"] if r["asset"] == "BTC")
    eth_buy = next(r for r in plan["buy_plan"] if r["asset"] == "ETH")
    assert Decimal(btc_buy["amount_usdc"]) > Decimal(eth_buy["amount_usdc"])


def test_sell_when_cash_insufficient(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    resolver = _FixedPriceResolver(
        {"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")},
    )
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.02")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "ETH").id, "0.001")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    plan = plan_bundle_rebalance_from_drift(snap)

    assert plan["status"] == "ok"
    assert any(r["asset"] == "BTC" for r in plan.get("sell_plan") or [])
    assert any(r["asset"] == "ETH" for r in plan.get("buy_plan") or [])


def test_plan_hash_deterministic(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, _majors_weights())
    resolver = _FixedPriceResolver(_majors_prices())
    _seed_majors_spot(db, portfolio.id)
    _credit_cash(db, portfolio.id, usdc.id, "10")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    plan1 = plan_bundle_rebalance_from_drift(snap)
    plan2 = plan_bundle_rebalance_from_drift(snap)
    assert plan1["plan_hash"] == plan2["plan_hash"]
    assert plan1["plan_hash"].startswith("sha256:")


def test_kings_cash_dominant_deploys_portfolio_value_targets():
    """Cash leg >> investi → achats BTC+ETH sur NAV totale (pas drift 1,5 USDC)."""
    snap = {
        "snapshot_hash": "kings-snap",
        "entry_asset": "USDC",
        "weight_basis": "invested_assets",
        "invested_value_usdc": "35.158969",
        "cash_value_usdc": "125.685470",
        "portfolio_value_usdc": "160.844439",
        "target_assets": [
            {
                "asset": "BTC",
                "instrument_id": "btc-id",
                "target_weight_bps": 7000,
                "current_value_usdc": "26.184873",
                "target_value_usdc": "24.611278",
                "delta_value_usdc": "-1.573595",
                "drift_bps": 447,
                "price_usdc": "61570.903020",
            },
            {
                "asset": "ETH",
                "instrument_id": "eth-id",
                "target_weight_bps": 3000,
                "current_value_usdc": "8.974096",
                "target_value_usdc": "10.547690",
                "delta_value_usdc": "1.573594",
                "drift_bps": -448,
                "price_usdc": "1633.613579",
            },
        ],
        "non_target_assets": [],
    }
    plan = plan_bundle_rebalance_from_drift(snap)

    assert plan["planning_mode"] == "portfolio_value_cash_deploy"
    assert plan["status"] == "ok"
    assert plan["sell_plan"] == []

    buys = {row["asset"]: row for row in plan["buy_plan"]}
    assert "BTC" in buys
    assert "ETH" in buys

    total_buy = sum(Decimal(r["amount_usdc"]) for r in plan["buy_plan"])
    assert total_buy <= Decimal(snap["cash_value_usdc"])
    assert total_buy >= Decimal("120")

    btc_buy = Decimal(buys["BTC"]["amount_usdc"])
    eth_buy = Decimal(buys["ETH"]["amount_usdc"])
    assert btc_buy > eth_buy
    assert "target_value_usdc" in buys["BTC"]
    assert "amount_crypto" in buys["BTC"]
    assert Decimal(buys["BTC"]["target_value_usdc"]) > Decimal("100")


def test_deltas_below_min_ignored(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.500000"), "ETH": Decimal("0.500000")},
    )
    resolver = _FixedPriceResolver(
        {"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")},
    )
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.0005500000")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "ETH").id, "0.0164800000")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    plan = plan_bundle_rebalance_from_drift(snap)
    assert plan["status"] == "no_action"
