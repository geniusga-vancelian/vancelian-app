"""Tests terminalisation V3 — legs planifiés non quotés."""
from __future__ import annotations

from services.portfolio_engine.bundles.rebalance_executor import (
    BundleRebalanceExecutor,
    V3LegExecutionResult,
    has_unquoted_plan_legs,
)


def _leg(asset: str, status: str) -> V3LegExecutionResult:
    return V3LegExecutionResult(
        asset=asset,
        instrument_id="00000000-0000-0000-0000-000000000001",
        action="buy",
        amount_usdc="10",
        status=status,
        attempts=1,
    )


def test_has_unquoted_plan_legs_detects_missing_eth():
    buy_plan = [
        {"asset": "BTC", "amount_usdc": "40"},
        {"asset": "ETH", "amount_usdc": "20"},
    ]
    buy_results = [_leg("BTC", "completed")]
    assert has_unquoted_plan_legs(
        sell_plan=[],
        buy_plan=buy_plan,
        sell_results=[],
        buy_results=buy_results,
    )


def test_resolve_terminal_status_partial_plan_is_residual_cash():
    buy_plan = [
        {"asset": "BTC", "amount_usdc": "40"},
        {"asset": "ETH", "amount_usdc": "20"},
    ]
    buy_results = [_leg("BTC", "completed")]
    status = BundleRebalanceExecutor._resolve_terminal_status(
        [],
        buy_results,
        sell_plan=[],
        buy_plan=buy_plan,
        cash_remaining_usdc="20",
    )
    assert status == "COMPLETED_WITH_RESIDUAL_CASH"


def test_leg_to_dict_includes_lifi_quote_fields_for_sell():
    leg = V3LegExecutionResult(
        asset="AAVE",
        instrument_id="00000000-0000-0000-0000-000000000001",
        action="sell",
        amount_usdc="4.33",
        status="pending",
        attempts=1,
        swap_id="swap-1",
        amount_in="0.068",
        estimated_receive="4.31",
        from_asset="AAVE",
        to_asset="USDC",
    )
    payload = leg.to_dict()
    assert payload["amount_in"] == "0.068"
    assert payload["estimated_receive"] == "4.31"
    assert payload["from_asset"] == "AAVE"
    assert payload["quantity_sold"] == 0.068
    assert payload["entry_asset_received"] == 4.31


def test_resolve_terminal_status_full_plan_is_completed():
    buy_plan = [
        {"asset": "BTC", "amount_usdc": "40"},
        {"asset": "ETH", "amount_usdc": "20"},
    ]
    buy_results = [_leg("BTC", "completed"), _leg("ETH", "completed")]
    status = BundleRebalanceExecutor._resolve_terminal_status(
        [],
        buy_results,
        sell_plan=[],
        buy_plan=buy_plan,
    )
    assert status == "COMPLETED"
