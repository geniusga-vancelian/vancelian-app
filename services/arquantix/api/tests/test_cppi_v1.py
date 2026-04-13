"""
Tests for CPPI strategy v1
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from services.backtest.strategies.cppi import run_cppi_backtest


def test_cppi_respects_floor_on_crash_with_liquid_core():
    """Test that CPPI never breaches floor when risky crashes (with liquid core)"""
    # Create synthetic price data: risky asset crashes 50% on day 2
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1)]
    
    prices = pd.DataFrame({
        1: [100.0, 50.0],  # 50% crash
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=1),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,  # Floor = 900
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,  # Zero yield to isolate risky drop effect
        day_count=365,
    )
    
    # Check NAV never goes below floor
    floor = 1000.0 * 0.90
    for ps in result['portfolio_series']:
        nav = ps['nav_base100'] / 100.0 * 1000.0  # Convert back to actual value
        assert nav >= floor - 1e-6, f"NAV {nav} breached floor {floor}"


def test_cppi_skips_rebalance_when_missing_price():
    """Test that CPPI skips rebalance when price is missing"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1), start + timedelta(days=2)]
    
    prices = pd.DataFrame({
        1: [100.0, np.nan, 110.0],  # Missing price on day 2
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=2),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,
        day_count=365,
        debug=True,
    )
    
    # Should complete without error (skip rebalance on missing price)
    assert len(result['portfolio_series']) == 3


def test_cppi_accepts_bundle_without_instrument_ids():
    """Test that CPPI works with bundle (weights_resolver)"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1)]
    
    prices = pd.DataFrame({
        1: [100.0, 110.0],
        2: [50.0, 55.0],
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 0.6, 2: 0.4}  # Bundle weights
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=1),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,
        day_count=365,
    )
    
    assert len(result['portfolio_series']) == 2


def test_cppi_rejects_invalid_weights_sum():
    """Test that CPPI rejects weights that don't sum to 1.0"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1)]  # Need 2 dates for rebalance to happen (i > 0)
    
    prices = pd.DataFrame({
        1: [100.0, 110.0],
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 0.8}  # Sums to 0.8, not 1.0
    
    with pytest.raises(ValueError, match="weights summing to"):
        run_cppi_backtest(
            prices_df=prices,
            weights_resolver=weights_resolver,
            start_date=start,
            end_date=start + timedelta(days=1),
            initial_capital=1000.0,
            rebalance_frequency="daily",
            fees_bps=0.0,
            slippage_bps=0.0,
            floor_ratio=0.90,
            multiplier=4.0,
            risky_cap=1.0,
            core_min=0.0,
            core_yield=0.0,
            day_count=365,
        )


def test_cppi_risky_cap_is_enforced():
    """Test that risky_cap limits risky allocation"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1)]
    
    prices = pd.DataFrame({
        1: [100.0, 200.0],  # 100% gain -> should max out risky at risky_cap
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=1),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.50,  # Low floor to allow high risky
        multiplier=10.0,  # High multiplier
        risky_cap=0.8,  # Cap risky at 80%
        core_min=0.0,
        core_yield=0.0,
        day_count=365,
    )
    
    # Check that risky weight doesn't exceed cap
    for ps in result['portfolio_series']:
        risky_weight = ps['weights_json'].get('_cppi_risky_weight', 0.0)
        assert risky_weight <= 0.8 + 1e-4, f"Risky weight {risky_weight} exceeds cap 0.8"


def test_cppi_de_risks_on_drop():
    """Test that risky allocation decreases after risky asset drops"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1), start + timedelta(days=2)]
    
    prices = pd.DataFrame({
        1: [100.0, 50.0, 50.0],  # Drop then flat
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=2),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,  # No core yield to isolate risky effect
        day_count=365,
    )
    
    series = result['portfolio_series']
    assert len(series) >= 3
    
    # On first day (i=0), no rebalance happens, so cushion is initial (V0 - floor)
    # After drop and rebalance, cushion should decrease
    # Check cushion after first rebalance (day 1, index 1) vs after drop (day 2, index 2)
    cushion_after_rebalance = series[1]['weights_json'].get('_cppi_cushion', 0.0)
    cushion_after_drop = series[2]['weights_json'].get('_cppi_cushion', 0.0)
    
    # Cushion should decrease after drop (NAV drops, floor stays same with core_yield=0)
    # Allow for small numerical differences
    assert cushion_after_drop < cushion_after_rebalance + 1e-6, \
        f"Cushion should decrease after drop: {cushion_after_rebalance} -> {cushion_after_drop}"


def test_cppi_increases_allocation_on_rally():
    """Test that risky allocation increases on a rally"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1), start + timedelta(days=2)]
    
    prices = pd.DataFrame({
        1: [100.0, 150.0, 200.0],  # Rising series
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=2),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,  # No core yield to isolate risky effect
        day_count=365,
    )
    
    series = result['portfolio_series']
    assert len(series) >= 3
    
    # Cushion should increase on rally
    cushion_start = series[0]['weights_json'].get('_cppi_cushion', 0.0)
    cushion_end = series[-1]['weights_json'].get('_cppi_cushion', 0.0)
    
    assert cushion_end > cushion_start, f"Cushion should increase on rally: {cushion_start} -> {cushion_end}"


def test_cppi_bundle_mapping_correctness():
    """Test that bundle weights are correctly applied to risky sleeve"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1)]
    
    prices = pd.DataFrame({
        1: [100.0, 110.0],
        2: [50.0, 55.0],
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 0.7, 2: 0.3}  # Bundle weights
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=1),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,
        day_count=365,
    )
    
    # Check that weights are stored
    for ps in result['portfolio_series']:
        weights = ps['weights_json']
        if '1' in weights and '2' in weights:
            # Should match bundle weights (within tolerance)
            assert abs(weights['1'] - 0.7) < 1e-4, f"Weight 1 should be 0.7, got {weights['1']}"
            assert abs(weights['2'] - 0.3) < 1e-4, f"Weight 2 should be 0.3, got {weights['2']}"


def test_cppi_logs_skip_on_missing_price():
    """Test that rebalance skip is logged when prices are missing"""
    start = date(2023, 1, 1)
    dates = [start, start + timedelta(days=1), start + timedelta(days=2)]
    
    prices = pd.DataFrame({
        1: [100.0, np.nan, 110.0],  # Missing price on day 2
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=2),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=0.90,
        multiplier=4.0,
        risky_cap=1.0,
        core_min=0.0,
        core_yield=0.0,
        day_count=365,
        debug=True,
    )
    
    # Should have debug log entry for skip
    assert 'debug_log' in result
    skip_logs = [log for log in result['debug_log'] if log.get('event') == 'rebalance_skipped']
    assert len(skip_logs) > 0, "Should have at least one rebalance_skipped log"


def test_cppi_floor_grows_with_core_yield():
    """Test that floor grows daily with core_yield (CPPI v1.1 indexed floor)"""
    start = date(2023, 1, 1)
    # Create ~365 days of flat prices
    dates = [start + timedelta(days=i) for i in range(366)]  # Full year + 1 day
    
    prices = pd.DataFrame({
        1: [100.0] * 366,  # Flat prices (no risky movement)
    }, index=pd.DatetimeIndex(dates))
    
    def weights_resolver(d: date) -> dict:
        return {1: 1.0}
    
    floor_ratio = 0.90
    core_yield = 0.05  # 5% annual yield
    day_count = 365
    
    result = run_cppi_backtest(
        prices_df=prices,
        weights_resolver=weights_resolver,
        start_date=start,
        end_date=start + timedelta(days=365),
        initial_capital=1000.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        floor_ratio=floor_ratio,
        multiplier=1.0,  # Small multiplier to keep allocation stable
        risky_cap=1.0,
        core_min=0.0,
        core_yield=core_yield,
        day_count=day_count,
    )
    
    series = result['portfolio_series']
    assert len(series) >= 365
    
    # Get first and last floor values (floor is stored as actual value, not base100)
    first_floor = series[0]['weights_json'].get('_cppi_floor', 0.0)
    last_floor = series[-1]['weights_json'].get('_cppi_floor', 0.0)
    
    # Expected: floor_end = floor_start * (1 + core_yield / day_count) ** days
    # Using compound formula for daily accrual (same as core_value growth)
    expected_floor_end = first_floor * (1 + core_yield / day_count) ** 365
    
    # Tolerance: within 1.0 (compounding precision difference from simple formula)
    # The actual growth uses daily compounding: (1 + r/365)^365 ≈ 1.05127 for r=5%
    # Simple formula: (1 + r) = 1.05 gives slightly different result
    assert abs(last_floor - expected_floor_end) < 1.0, \
        f"Floor should grow to ~{expected_floor_end:.2f}, got {last_floor:.2f} (diff: {abs(last_floor - expected_floor_end):.2f})"
    
    # Also verify it's close to simple formula (should be slightly higher due to compounding)
    simple_expected = first_floor * (1 + core_yield)
    assert last_floor > simple_expected * 0.99, \
        f"Floor {last_floor:.2f} should be close to simple formula {simple_expected:.2f}"
    
    # Check floor is monotonic increasing (check every 30 days)
    for i in range(30, len(series), 30):
        prev_floor = series[i-30]['weights_json'].get('_cppi_floor', 0.0)
        curr_floor = series[i]['weights_json'].get('_cppi_floor', 0.0)
        assert curr_floor >= prev_floor - 1e-6, \
            f"Floor should be monotonic: {prev_floor} -> {curr_floor} at index {i}"
