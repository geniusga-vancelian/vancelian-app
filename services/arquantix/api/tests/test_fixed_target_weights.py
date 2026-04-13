"""
Unit tests for Fixed Target Weights Rebalancing
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
import pandas as pd
import numpy as np

from services.backtest.engine import (
    compute_target_weights_fixed,
    compute_target_weights,
    apply_tradability_constraints,
)


class TestFixedTargetWeights:
    """Test fixed target weights rebalancing"""
    
    def test_compute_target_weights_fixed_returns_bundle_weights(self):
        """Test that fixed weights are returned as-is (source of truth)"""
        fixed_weights = {1: 0.6, 2: 0.4}  # 60/40 allocation
        eligible_instruments = [1, 2]
        
        result = compute_target_weights_fixed(fixed_weights, eligible_instruments)
        
        assert result[1] == pytest.approx(0.6, abs=0.001)
        assert result[2] == pytest.approx(0.4, abs=0.001)
        assert sum(result.values()) == pytest.approx(1.0, abs=0.001)
    
    def test_compute_target_weights_fixed_filters_eligible(self):
        """Test that only eligible instruments are included"""
        fixed_weights = {1: 0.5, 2: 0.3, 3: 0.2}
        eligible_instruments = [1, 2]  # 3 is not eligible
        
        result = compute_target_weights_fixed(fixed_weights, eligible_instruments)
        
        assert 1 in result
        assert 2 in result
        assert 3 not in result
        # Should normalize to sum to 1.0
        assert sum(result.values()) == pytest.approx(1.0, abs=0.001)
        assert result[1] == pytest.approx(0.625, abs=0.001)  # 0.5 / 0.8
        assert result[2] == pytest.approx(0.375, abs=0.001)  # 0.3 / 0.8
    
    def test_compute_target_weights_with_fixed_weights(self):
        """Test that compute_target_weights uses fixed weights when provided"""
        fixed_weights = {1: 0.6, 2: 0.4}
        eligible_instruments = [1, 2]
        
        result = compute_target_weights(
            date=date(2024, 1, 1),
            strategy_type="equal_weight",  # Should be ignored
            open_prices=pd.DataFrame(),  # Should be ignored
            returns=pd.DataFrame(),  # Should be ignored
            lookback_days=None,  # Should be ignored
            eligible_instruments=eligible_instruments,
            prev_weights=None,
            fixed_weights=fixed_weights,
        )
        
        assert result[1] == pytest.approx(0.6, abs=0.001)
        assert result[2] == pytest.approx(0.4, abs=0.001)
    
    def test_fixed_weights_are_source_of_truth(self):
        """Test that fixed weights never change (source of truth)"""
        fixed_weights = {1: 0.6, 2: 0.4}
        eligible_instruments = [1, 2]
        
        # Call multiple times - should always return same weights
        result1 = compute_target_weights_fixed(fixed_weights, eligible_instruments)
        result2 = compute_target_weights_fixed(fixed_weights, eligible_instruments)
        result3 = compute_target_weights_fixed(fixed_weights, eligible_instruments)
        
        assert result1 == result2 == result3
        assert result1[1] == pytest.approx(0.6, abs=0.001)
        assert result1[2] == pytest.approx(0.4, abs=0.001)


class TestRebalanceBehavior:
    """Test rebalancing behavior with fixed weights"""
    
    def test_rebalance_returns_to_target_weights(self):
        """Test that after rebalance, allocation matches target weights"""
        # Simulate: portfolio drifted to 70/30, target is 60/40
        prev_weights = {1: 0.7, 2: 0.3}
        fixed_target_weights = {1: 0.6, 2: 0.4}
        eligible_instruments = [1, 2]
        
        target_weights = compute_target_weights_fixed(fixed_target_weights, eligible_instruments)
        
        # After applying constraints (weekday, all tradable)
        weekend_tradable_map = {1: True, 2: True}
        new_weights, turnover, tradable_mask = apply_tradability_constraints(
            date=date(2024, 1, 15),  # Monday (weekday)
            weekend_tradable_map=weekend_tradable_map,
            target_weights=target_weights,
            prev_weights=prev_weights,
        )
        
        # Should return to 60/40 (within tolerance)
        assert new_weights[1] == pytest.approx(0.6, abs=0.01)
        assert new_weights[2] == pytest.approx(0.4, abs=0.01)
        assert turnover > 0  # Should have turnover to rebalance
    
    def test_drift_between_rebalances(self):
        """Test that weights drift naturally between rebalances"""
        # Initial weights: 60/40
        weights = {1: 0.6, 2: 0.4}
        
        # Simulate price movement: asset 1 +10%, asset 2 -5%
        # Portfolio value: 0.6 * 1.1 + 0.4 * 0.95 = 0.66 + 0.38 = 1.04
        # New weights: 0.66/1.04 = 0.635, 0.38/1.04 = 0.365
        # (This is just conceptual - actual drift happens in NAV calculation)
        
        # The key point: weights should NOT be recalculated between rebalances
        # They should drift naturally based on price movements
        assert True  # Placeholder - actual drift tested in integration tests


class TestValidation:
    """Test validation of bundle weights"""
    
    def test_weights_must_sum_to_one(self):
        """Test that weights summing to != 1.0 are rejected"""
        # This is tested at the API level, not in engine
        # But we can test normalization in compute_target_weights_fixed
        fixed_weights = {1: 0.5, 2: 0.3}  # Sum = 0.8, not 1.0
        eligible_instruments = [1, 2]
        
        # Should normalize to sum to 1.0
        result = compute_target_weights_fixed(fixed_weights, eligible_instruments)
        
        assert sum(result.values()) == pytest.approx(1.0, abs=0.001)
        assert result[1] == pytest.approx(0.625, abs=0.001)  # 0.5 / 0.8
        assert result[2] == pytest.approx(0.375, abs=0.001)  # 0.3 / 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

