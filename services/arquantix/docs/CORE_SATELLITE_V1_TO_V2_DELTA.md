# Core-Satellite V1 -> V2 Delta

## Overview

V2 is an upgrade of V1 with improved optimization, better risk modeling, and enhanced reporting, while keeping the same architecture and benchmark (Core only).

## Key Changes

### 1. Optimization Algorithm

**V1:**
- Grid search over core_weight in [core_min, 1.0] with step `core_grid_step` (default 0.01)
- Simple greedy allocation for satellite weights (top mu assets, respect max_weight_per_asset)
- No turnover/stability constraints
- No shrinkage for covariance

**V2:**
- **Improved optimization**: Quadratic optimization for satellite weights given core_weight
- **Shrinkage** (optional): Ledoit-Wolf shrinkage estimator for covariance matrix
- **Turnover control** (optional): Penalty term to reduce rebalance turnover
- **Stability control** (optional): Penalty term to reduce weight changes vs previous weights
- **Better solver**: Uses numpy-based quadratic programming (no external dependencies)

### 2. New Parameters

**V1:**
- `target_te`, `te_tolerance`, `te_max_hard_mult`
- `lookback_risk_days`, `lookback_return_days`
- `core_min`, `max_weight_per_asset`, `core_grid_step`
- `top_k_satellite` (optional filter)

**V2 (adds):**
- `shrinkage` (bool, default false): Enable Ledoit-Wolf shrinkage for covariance
- `turnover_penalty` (float, default 0.0): Penalty coefficient for turnover control
- `stability_penalty` (float, default 0.0): Penalty coefficient for stability control
- `sat_min` (float, default 0.0): Minimum satellite weight (sum of satellite weights >= sat_min)
- `optimization_method` (str, default "quadratic"): "grid" (V1) or "quadratic" (V2)

### 3. New Metrics/Series

**V1 portfolio_series weights_json:**
- `_core_weight`: Core weight
- `_te_realized`: Realized TE (if computed)
- `_te_pred`: Predicted TE (if available)

**V2 portfolio_series weights_json (adds):**
- `_core_weight`: Core weight (same)
- `_te_realized`: Realized TE (same)
- `_te_pred`: Predicted TE (same, but with shrinkage if enabled)
- `_te_pred_shrunk`: Predicted TE with shrinkage (if shrinkage enabled)
- `_satellite_turnover`: Satellite turnover (sum of abs weight changes)
- `_portfolio_turnover`: Total portfolio turnover (including core)
- `_optimization_score`: Optimization score (objective value)

**V2 metrics (adds):**
- `avg_realized_te`: Average realized TE over the period
- `avg_predicted_te`: Average predicted TE over the period
- `avg_turnover`: Average turnover per rebalance
- `te_ratio`: Ratio of realized_te / target_te (final)

### 4. Optimization Details

**V1:**
```python
# Grid search over w_core
for w_core in grid:
    budget = 1 - w_core
    # Greedy allocation: allocate to top mu assets
    satellite_weights = greedy_allocate(mu_sat, budget, max_weight_per_asset)
    te_pred = sqrt(w_sat^T Σ w_sat) * sqrt(day_count)
    # Choose best by excess return within TE tolerance
```

**V2:**
```python
# Grid search over w_core (same)
for w_core in grid:
    budget = 1 - w_core
    # Quadratic optimization for satellite weights
    # Objective: max mu_sat^T w_sat - penalty * (turnover + stability)
    # Constraints: sum(w_sat) = budget, w_sat >= 0, w_sat <= max_weight_per_asset, sum(w_sat) >= sat_min
    satellite_weights = quadratic_optimize(mu_sat, Σ, budget, constraints, penalties)
    
    # Shrinkage (optional)
    if shrinkage:
        Σ_shrunk = ledoit_wolf_shrinkage(Σ)
        te_pred = sqrt(w_sat^T Σ_shrunk w_sat) * sqrt(day_count)
    else:
        te_pred = sqrt(w_sat^T Σ w_sat) * sqrt(day_count)
    
    # Choose best by optimization score (adjusted for TE constraint)
```

### 5. What Remains Simplified

- **Benchmark = Core only**: No complex benchmark index (same as V1)
- **Core yield = constant**: No time-varying core yield (same as V1)
- **No liquidity constraints**: Core is fully liquid (same as V1)
- **No transaction cost optimization**: Costs applied after optimization (same as V1)
- **No multi-period optimization**: Single-period optimization per rebalance (same as V1)

### 6. Backward Compatibility

V2 maintains backward compatibility:
- If `optimization_method="grid"` or not specified, uses V1 grid search
- If `optimization_method="quadratic"`, uses V2 quadratic optimization
- V1 params still work (treated as V1 if optimization_method not set)
- V2 params are optional (defaults maintain V1 behavior)

### 7. Implementation Notes

- **No external dependencies**: Uses numpy/scipy (already in requirements)
- **Ledoit-Wolf shrinkage**: Implemented from scratch (no sklearn dependency)
- **Quadratic optimization**: Uses scipy.optimize (already available)
- **Same architecture**: Follows CPPI pattern (run_core_satellite_backtest, executor dispatch)

### 8. Performance Improvements

- **Faster optimization**: Quadratic solver faster than exhaustive grid search for large universes
- **Better risk control**: Shrinkage improves covariance estimation for small samples
- **Stability**: Turnover/stability penalties reduce unnecessary rebalancing
- **Reporting**: More detailed metrics for analysis

## Migration Guide

To upgrade from V1 to V2:

1. **Keep V1 behavior**: Don't change any params (V1 still works)
2. **Enable V2**: Set `optimization_method="quadratic"` in params
3. **Optional enhancements**:
   - Enable `shrinkage: true` for better covariance estimation
   - Set `turnover_penalty` (e.g., 0.001) to reduce turnover
   - Set `stability_penalty` (e.g., 0.0001) to reduce weight changes
   - Set `sat_min` (e.g., 0.0) to enforce minimum satellite allocation

Example V2 request:
```json
{
  "strategy": {
    "type": "CORE_SATELLITE",
    "params": {
      "target_te": 0.10,
      "core_yield": 0.035,
      "optimization_method": "quadratic",
      "shrinkage": true,
      "turnover_penalty": 0.001,
      "stability_penalty": 0.0001,
      "sat_min": 0.0
    }
  }
}
```
