"""B3b — Rebalance planner pur (portfolio_after_funding → rebalance_to_target)."""
from __future__ import annotations

import copy
import inspect
from decimal import Decimal

import pytest

from services.portfolio_engine.bundles.event_driven.rebalance_planner import (
    PortfolioSnapshot,
    PositionSnapshot,
    RebalancePolicies,
    TargetAllocationInput,
    plan_rebalance_after_funding,
)


def _empty() -> PortfolioSnapshot:
    return PortfolioSnapshot(bundle_cash_usdc=Decimal("0"))


def _cash_only(amount: str) -> PortfolioSnapshot:
    return PortfolioSnapshot(bundle_cash_usdc=Decimal(amount))


def _with_position(cash: str, asset: str, qty: str) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        bundle_cash_usdc=Decimal(cash),
        positions=(PositionSnapshot(asset=asset, quantity=Decimal(qty)),),
    )


def _with_positions(cash: str, positions: list[tuple[str, str]]) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        bundle_cash_usdc=Decimal(cash),
        positions=tuple(PositionSnapshot(asset=a, quantity=Decimal(q)) for a, q in positions),
    )


PRICES_50_50 = {"BTC": Decimal("1000"), "ETH": Decimal("100")}
TARGET_50_50 = (
    TargetAllocationInput(asset="BTC", weight_bps=5000),
    TargetAllocationInput(asset="ETH", weight_bps=5000),
)


def test_empty_portfolio_funding_100_target_50_50_minus_buffer():
    before = _empty()
    after = _cash_only("100")
    plan = plan_rebalance_after_funding(
        portfolio_before=before,
        funding_usdc=Decimal("100"),
        portfolio_after_funding=after,
        target_allocation=TARGET_50_50,
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(execution_buffer_usdc=Decimal("1"), min_trade_usdc=Decimal("1")),
    )

    buys = {leg.asset: leg.notional_usdc for leg in plan.legs if leg.direction == "buy"}
    assert set(buys) == {"BTC", "ETH"}
    assert sum(buys.values()) == Decimal("99")
    assert plan.residual_usdc == Decimal("1")
    assert all(leg.reason == "underweight" for leg in plan.legs)


def test_overweight_btc_funding_buys_underweight_not_btc():
    before = _with_position("0", "BTC", "0.1")
    after = _with_positions("100", [("BTC", "0.1")])
    plan = plan_rebalance_after_funding(
        portfolio_before=before,
        funding_usdc=Decimal("100"),
        portfolio_after_funding=after,
        target_allocation=(
            TargetAllocationInput(asset="BTC", weight_bps=4000),
            TargetAllocationInput(asset="ETH", weight_bps=6000),
        ),
        prices_used={"BTC": Decimal("1000"), "ETH": Decimal("100")},
        policies=RebalancePolicies(
            execution_buffer_usdc=Decimal("1"),
            min_trade_usdc=Decimal("1"),
            allow_sell=False,
        ),
    )

    buy_assets = [leg.asset for leg in plan.legs if leg.direction == "buy"]
    assert "BTC" not in buy_assets
    assert "ETH" in buy_assets
    assert any(s.asset == "BTC" and "overweight" in s.reason for s in plan.skipped)


def test_existing_cash_residual_not_double_counted():
    before = _cash_only("10")
    after = _cash_only("100")
    plan = plan_rebalance_after_funding(
        portfolio_before=before,
        funding_usdc=Decimal("90"),
        portfolio_after_funding=after,
        target_allocation=TARGET_50_50,
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(execution_buffer_usdc=Decimal("1"), min_trade_usdc=Decimal("1")),
    )

    assert plan.weights_before == {"BTC": 0, "ETH": 0}
    assert sum(leg.notional_usdc for leg in plan.legs) == Decimal("99")


def test_drift_only_funding_zero_no_legs_within_tolerance():
    after = _with_positions("0", [("BTC", "0.05"), ("ETH", "0.5")])
    plan = plan_rebalance_after_funding(
        portfolio_before=after,
        funding_usdc=Decimal("0"),
        portfolio_after_funding=after,
        target_allocation=TARGET_50_50,
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(drift_tolerance_bps=500, min_trade_usdc=Decimal("1")),
    )

    assert len(plan.legs) == 0


def test_drift_only_funding_zero_legs_when_drift_exceeds_tolerance():
    after = _with_positions("0", [("BTC", "0.09"), ("ETH", "0.1")])
    plan = plan_rebalance_after_funding(
        portfolio_before=after,
        funding_usdc=Decimal("0"),
        portfolio_after_funding=after,
        target_allocation=TARGET_50_50,
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(
            drift_tolerance_bps=100,
            min_trade_usdc=Decimal("1"),
            allow_sell=True,
            execution_buffer_usdc=Decimal("0"),
        ),
    )

    assert any(leg.direction == "sell" and leg.asset == "BTC" for leg in plan.legs)
    assert any(leg.direction == "buy" and leg.asset == "ETH" for leg in plan.legs)


def test_overweight_allow_sell_false_no_sell_legs():
    after = _with_positions("50", [("BTC", "0.1")])
    plan = plan_rebalance_after_funding(
        portfolio_before=after,
        funding_usdc=Decimal("0"),
        portfolio_after_funding=after,
        target_allocation=(
            TargetAllocationInput(asset="BTC", weight_bps=2000),
            TargetAllocationInput(asset="ETH", weight_bps=8000),
        ),
        prices_used={"BTC": Decimal("1000"), "ETH": Decimal("100")},
        policies=RebalancePolicies(allow_sell=False, min_trade_usdc=Decimal("1"), drift_tolerance_bps=0),
    )

    assert not any(leg.direction == "sell" for leg in plan.legs)
    assert any(s.asset == "BTC" and "overweight" in s.reason for s in plan.skipped)


def test_overweight_allow_sell_true_generates_sell_leg():
    after = _with_positions("0", [("BTC", "0.1")])
    plan = plan_rebalance_after_funding(
        portfolio_before=after,
        funding_usdc=Decimal("0"),
        portfolio_after_funding=after,
        target_allocation=(
            TargetAllocationInput(asset="BTC", weight_bps=2000),
            TargetAllocationInput(asset="ETH", weight_bps=8000),
        ),
        prices_used={"BTC": Decimal("1000"), "ETH": Decimal("100")},
        policies=RebalancePolicies(
            allow_sell=True,
            min_trade_usdc=Decimal("1"),
            drift_tolerance_bps=0,
            execution_buffer_usdc=Decimal("0"),
        ),
    )

    sells = [leg for leg in plan.legs if leg.direction == "sell"]
    assert len(sells) == 1
    assert sells[0].asset == "BTC"
    assert sells[0].reason == "overweight"


def test_min_trade_usdc_skips_small_legs():
    after = _cash_only("20")
    plan = plan_rebalance_after_funding(
        portfolio_before=_empty(),
        funding_usdc=Decimal("20"),
        portfolio_after_funding=after,
        target_allocation=(
            TargetAllocationInput(asset="BTC", weight_bps=9900),
            TargetAllocationInput(asset="ETH", weight_bps=100),
        ),
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(
            min_trade_usdc=Decimal("5"),
            execution_buffer_usdc=Decimal("1"),
        ),
    )

    eth_buys = [leg for leg in plan.legs if leg.asset == "ETH"]
    assert len(eth_buys) == 0
    assert any(s.asset == "ETH" and s.reason == "below_min_trade" for s in plan.skipped)


def test_missing_price_skipped_with_warning():
    after = _cash_only("100")
    plan = plan_rebalance_after_funding(
        portfolio_before=_empty(),
        funding_usdc=Decimal("100"),
        portfolio_after_funding=after,
        target_allocation=(
            TargetAllocationInput(asset="BTC", weight_bps=5000),
            TargetAllocationInput(asset="ETH", weight_bps=5000),
        ),
        prices_used={"BTC": Decimal("1000")},
        policies=RebalancePolicies(min_trade_usdc=Decimal("1"), execution_buffer_usdc=Decimal("1")),
    )

    assert any(s.asset == "ETH" and s.reason == "no_price" for s in plan.skipped)
    assert any("missing_price:ETH" in w for w in plan.warnings)
    assert all(leg.asset == "BTC" for leg in plan.legs)


def test_hash_deterministic():
    kwargs = dict(
        portfolio_before=_empty(),
        funding_usdc=Decimal("100"),
        portfolio_after_funding=_cash_only("100"),
        target_allocation=TARGET_50_50,
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(execution_buffer_usdc=Decimal("1"), min_trade_usdc=Decimal("1")),
    )
    first = plan_rebalance_after_funding(**kwargs)
    second = plan_rebalance_after_funding(**kwargs)

    assert first.plan_hash == second.plan_hash
    assert first.plan_hash.startswith("sha256:")


def test_expected_weights_after_execution_coherent():
    after = _cash_only("100")
    plan = plan_rebalance_after_funding(
        portfolio_before=_empty(),
        funding_usdc=Decimal("100"),
        portfolio_after_funding=after,
        target_allocation=TARGET_50_50,
        prices_used=PRICES_50_50,
        policies=RebalancePolicies(execution_buffer_usdc=Decimal("1"), min_trade_usdc=Decimal("1")),
    )

    assert plan.weights_expected_after_execution["BTC"] > 0
    assert plan.weights_expected_after_execution["ETH"] > 0
    assert plan.weights_expected_after_execution["BTC"] + plan.weights_expected_after_execution["ETH"] <= 10000
    assert plan.expected_portfolio_after_execution.weights_bps == plan.weights_expected_after_execution


def test_no_input_mutation():
    before = PortfolioSnapshot(bundle_cash_usdc=Decimal("10"))
    after = PortfolioSnapshot(bundle_cash_usdc=Decimal("100"))
    targets = [TargetAllocationInput(asset="BTC", weight_bps=5000), TargetAllocationInput(asset="ETH", weight_bps=5000)]
    prices = {"BTC": Decimal("1000"), "ETH": Decimal("100")}
    policies = RebalancePolicies()

    before_copy = copy.deepcopy(before)
    after_copy = copy.deepcopy(after)
    targets_copy = copy.deepcopy(targets)
    prices_copy = copy.deepcopy(prices)

    plan_rebalance_after_funding(
        portfolio_before=before,
        funding_usdc=Decimal("90"),
        portfolio_after_funding=after,
        target_allocation=targets,
        prices_used=prices,
        policies=policies,
    )

    assert before == before_copy
    assert after == after_copy
    assert targets == targets_copy
    assert prices == prices_copy


def test_no_settlement_worker_controller_imports():
    import services.portfolio_engine.bundles.event_driven.rebalance_planner as mod

    text = inspect.getsource(mod).lower()
    for token in (
        "settlement",
        "transaction_outbox",
        "controller",
        "apply_swap_settlement",
        "cost_basis",
        "sqlalchemy",
    ):
        assert token not in text, token


