"""Tests Portfolio Drift Engine — Bundle V3 PR-1 (read-only)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator
from services.portfolio_engine.positions.models import PositionAtom

from conftest import make_linked_client
from tests.test_bundle_allocation_phase5a import (
    _bundle_with_allocations,
    _instrument_for_asset,
)
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


class _FixedPriceResolver:
    def __init__(self, prices_eur: dict[str, Decimal]):
        self._prices = {k.upper(): v for k, v in prices_eur.items()}

    def resolve_price_eur(self, asset: str) -> Decimal:
        key = asset.upper()
        if key not in self._prices:
            raise ValueError(f"no_price:{key}")
        return self._prices[key]


def _credit_cash(db: Session, portfolio_id, instrument_id, amount: str) -> None:
    BundleOrchestrator._credit_cash_leg(
        db,
        portfolio_id,
        instrument_id,
        Decimal(amount),
        Decimal(amount),
    )


def _credit_spot(db: Session, portfolio_id, instrument_id, qty: str) -> None:
    BundleOrchestrator._sync_pe_position(
        db,
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        quantity_delta=Decimal(qty),
        cost_basis_delta=Decimal(qty),
    )


def _pe_cb_counts(db: Session) -> tuple[int, int]:
    pe = int(db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar() or 0)
    cb = int(db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar() or 0)
    return pe, cb


def test_golden_crypto_majors_drift_audit_shape(db: Session):
    """Cas golden — proportions proches audit pilote Crypto Majors."""
    pe = make_linked_client(db)
    weights = {
        "BTC": Decimal("0.500000"),
        "ETH": Decimal("0.300000"),
        "LINK": Decimal("0.066667"),
        "AAVE": Decimal("0.066667"),
        "UNI": Decimal("0.066666"),
    }
    portfolio, usdc = _bundle_with_allocations(db, pe.id, weights)

    prices = {
        "USDC": Decimal("0.92"),
        "BTC": Decimal("95000"),
        "ETH": Decimal("3200"),
        "LINK": Decimal("14"),
        "AAVE": Decimal("180"),
        "UNI": Decimal("6"),
    }
    resolver = _FixedPriceResolver(prices)

    # Valeurs spot ~ audit (% hors cash) ; cash testé à part (cash_only / preview).
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.0005185000")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "ETH").id, "0.0054700000")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "LINK").id, "0.4700000000")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "AAVE").id, "0.0365000000")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "UNI").id, "0.6230000000")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        price_resolver=resolver,
    )

    assert snap["weight_basis"] == "portfolio_value"
    assert Decimal(snap["cash_value_usdc"]) == 0
    assert Decimal(snap["invested_value_usdc"]) > 0
    assert Decimal(snap["portfolio_value_usdc"]) == Decimal(snap["invested_value_usdc"])

    by_asset = {row["asset"]: row for row in snap["target_assets"]}
    assert set(by_asset) == {"BTC", "ETH", "LINK", "AAVE", "UNI"}
    assert by_asset["BTC"]["target_weight_bps"] == 5000
    assert by_asset["ETH"]["target_weight_bps"] == 3000

    btc_delta = Decimal(by_asset["BTC"]["delta_value_usdc"])
    eth_delta = Decimal(by_asset["ETH"]["delta_value_usdc"])
    assert btc_delta < 0
    assert eth_delta > 0
    assert by_asset["BTC"]["action_hint"] == "sell"
    assert by_asset["ETH"]["action_hint"] == "buy"
    assert snap["snapshot_hash"].startswith("sha256:")


def test_pilot_cash_residual_included_in_portfolio_value(db: Session):
    """Cash ~29.87 USDC augmente portfolio_value (pilote Crypto Majors)."""
    pe = make_linked_client(db)
    weights = {
        "BTC": Decimal("0.500000"),
        "ETH": Decimal("0.300000"),
        "LINK": Decimal("0.066667"),
        "AAVE": Decimal("0.066667"),
        "UNI": Decimal("0.066666"),
    }
    portfolio, usdc = _bundle_with_allocations(db, pe.id, weights)
    resolver = _FixedPriceResolver(
        {
            "USDC": Decimal("0.92"),
            "BTC": Decimal("95000"),
            "ETH": Decimal("3200"),
            "LINK": Decimal("14"),
            "AAVE": Decimal("180"),
            "UNI": Decimal("6"),
        }
    )
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.0005185000")
    _credit_cash(db, portfolio.id, usdc.id, "29.866638")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    assert snap["weight_basis"] == "portfolio_value"
    assert snap["cash_value_usdc"] == "29.866638"
    assert Decimal(snap["invested_value_usdc"]) > 0
    assert Decimal(snap["portfolio_value_usdc"]) == (
        Decimal(snap["invested_value_usdc"]) + Decimal("29.866638")
    )
    by_asset = {r["asset"]: r for r in snap["target_assets"]}
    assert by_asset["BTC"]["action_hint"] == "sell"
    assert by_asset["ETH"]["action_hint"] == "buy"


def test_cash_only_portfolio_all_target_deltas_positive(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    resolver = _FixedPriceResolver({"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")})
    _credit_cash(db, portfolio.id, usdc.id, "100")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    assert Decimal(snap["invested_value_usdc"]) == 0
    for row in snap["target_assets"]:
        assert row["action_hint"] == "buy"


def test_no_cash_portfolio_drift_from_spot_only(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.6"), "ETH": Decimal("0.4")},
    )
    resolver = _FixedPriceResolver({"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")})
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.01")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "ETH").id, "0.01")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    assert Decimal(snap["cash_value_usdc"]) == 0
    assert len(snap["target_assets"]) == 2
    total_delta = sum(Decimal(r["delta_value_usdc"]) for r in snap["target_assets"])
    assert total_delta != 0


def test_non_target_asset_listed(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, {"BTC": Decimal("1.0")})
    sol = _instrument_for_asset(db, "SOL")
    resolver = _FixedPriceResolver(
        {"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "SOL": Decimal("120")},
    )
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.001")
    _credit_spot(db, portfolio.id, sol.id, "2.5")
    db.commit()

    snap = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    assert len(snap["non_target_assets"]) == 1
    assert snap["non_target_assets"][0]["asset"] == "SOL"
    assert snap["non_target_assets"][0]["action_hint"] == "sell_candidate"


def test_deterministic_snapshot_hash(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    resolver = _FixedPriceResolver({"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")})
    _credit_cash(db, portfolio.id, usdc.id, "50")
    db.commit()

    snap1 = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    snap2 = compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    assert snap1["snapshot_hash"] == snap2["snapshot_hash"]


def test_no_side_effects_pe_cb_swaps(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    resolver = _FixedPriceResolver({"USDC": Decimal("0.92"), "BTC": Decimal("90000"), "ETH": Decimal("3000")})
    _credit_cash(db, portfolio.id, usdc.id, "25")
    db.commit()

    pe_before, cb_before = _pe_cb_counts(db)
    swaps_before = int(
        db.execute(text("SELECT COUNT(*) FROM person_wallet_swaps")).scalar() or 0
    )
    intents_before = int(
        db.execute(text("SELECT COUNT(*) FROM transaction_intents")).scalar() or 0
    )

    compute_bundle_drift_snapshot(
        db, client_id=pe.id, portfolio_id=portfolio.id, price_resolver=resolver,
    )
    db.commit()

    pe_after, cb_after = _pe_cb_counts(db)
    swaps_after = int(
        db.execute(text("SELECT COUNT(*) FROM person_wallet_swaps")).scalar() or 0
    )
    intents_after = int(
        db.execute(text("SELECT COUNT(*) FROM transaction_intents")).scalar() or 0
    )

    assert pe_after == pe_before
    assert cb_after == cb_before
    assert swaps_after == swaps_before
    assert intents_after == intents_before


def test_preview_rebalance_includes_drift_snapshot(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "mock")
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    _credit_cash(db, portfolio.id, usdc.id, "100")
    _credit_spot(db, portfolio.id, _instrument_for_asset(db, "BTC").id, "0.001")
    db.commit()

    exchange = MagicMock()
    exchange._resolve_price = MagicMock(
        side_effect=lambda _db, asset, override_price=None, side="sell": {
            "USDC": Decimal("0.92"),
            "BTC": Decimal("90000"),
            "ETH": Decimal("3000"),
        }[asset.upper()]
    )
    orch = BundleRebalanceOrchestrator(exchange_service=exchange)
    preview = orch.preview_rebalance(db, client_id=pe.id, portfolio_id=portfolio.id)
    assert "drift_snapshot" in preview
    assert preview["drift_snapshot"]["portfolio_id"] == str(portfolio.id)
    assert preview["drift_snapshot"]["weight_basis"] == "portfolio_value"
    assert "drift_rebalance_plan" in preview
    assert preview["drift_rebalance_plan"]["weight_basis"] == "portfolio_value"
