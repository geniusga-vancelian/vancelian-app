# Core-Satellite Strategy v1.0 / v2.0

## Overview

Core-Satellite is a portfolio strategy that targets a specific tracking error (TE) vs a Core benchmark while maximizing expected excess return. The portfolio is split into:

- **Core**: Synthetic fixed-yield accrual (similar to CPPI core_yield)
- **Satellite**: Optimized risky assets (weights optimized to target TE)

**Benchmark = Core only** (same as CPPI simplification).

## Formulas

### Returns

- **r_p(t)**: Portfolio return on day t
- **r_c(t)**: Core return on day t
- **Active return**: a(t) = r_p(t) - r_c(t)

### Tracking Error (TE)

Given a lookback window of N days (default 63 trading days):

1. Compute daily active return series a(t) for the last N days
2. Calculate sample standard deviation: sigma_a = std(a(t)) using ddof=1
3. Annualized Tracking Error: **TE = sigma_a * sqrt(day_count)**

Where `day_count` is the annualization factor (default 252 for trading days).

### Core Benchmark Return

Core is synthetic yield:

- Core daily growth factor: `core_daily_growth = (1 + core_yield)^(1/day_count)`
- Core daily return: `r_c(t) = core_daily_growth - 1`

Same approach as CPPI floor accrual.

### Portfolio Construction

Portfolio is split:
- **w_core(t)**: Core weight
- **w_sat_i(t)**: Satellite weights for each instrument

Sum constraint: `w_core + sum_i w_sat_i = 1`

Constraints:
- No leverage (default)
- All weights >= 0 (long-only, default)

### Expected Returns Proxy

For v1, uses momentum / historical mean returns:
- **mu_i**: mean(r_i(t)) over `lookback_return_days` (default 63)
- **mu_core**: core_daily_return (constant)

### Active Risk

Since Core is deterministic (variance ~0), TE is essentially volatility of portfolio returns around the constant core return:

**Var(active) = Var(sum_i w_i r_i(t))**

Therefore:
**TE ≈ sqrt(w_sat^T Σ w_sat) * sqrt(day_count)**

Where:
- w_sat: satellite weights vector
- Σ: covariance matrix of risky returns
- w_sat sums to (1 - w_core)

### Optimization Problem (v1)

Goal: Choose satellite weights and core weight to target TE close to target.

Implementation uses grid search:
1. Grid search on w_core in [core_min, 1.0] with step `core_grid_step` (default 0.01)
2. For each w_core:
   - Budget = 1 - w_core
   - Find satellite weights that maximize mu_sat^T w_sat subject to:
     - sum(w_sat) = budget
     - w_sat_i >= 0
     - w_sat_i <= max_weight_per_asset (default 0.40)
   - Compute predicted TE: `TE_pred = sqrt(w_sat^T Σ w_sat) * sqrt(day_count)`
   - Keep solutions where `TE_pred <= target_te + te_tolerance`
3. Choose candidate with highest expected excess return (mu_p - mu_core)

If no solution matches TE band, choose solution with TE_pred closest to target_te, but never exceed `target_te * te_max_hard_mult` (default 1.10).

### Rebalance Logic

On each rebalance date:
- If any selected risky asset price is missing for that date, **SKIP** the rebalance (same as CPPI rule) and keep last weights
- Else recompute weights using the optimizer with rolling lookback windows
- Apply transaction costs using turnover: `turnover = sum(|w_new - w_old|) / 2`
- Costs: `costs = turnover * (fees_bps + slippage_bps) / 10000 * V`
- Deduct costs from NAV

## Parameters

- `core_yield` (float, default 0.035): Annual yield for core sleeve (3.5%)
- `target_te` (float, default 0.10): Target annualized tracking error (10%)
- `te_tolerance` (float, default 0.0025): Tolerance for TE target matching
- `te_max_hard_mult` (float, default 1.10): Hard cap multiplier for TE (target_te * te_max_hard_mult)
- `lookback_risk_days` (int, default 63): Lookback window for risk (covariance) estimation
- `lookback_return_days` (int, default 63): Lookback window for expected returns (momentum)
- `day_count` (int, default 252): Days per year for annualization
- `core_min` (float, default 0.0): Minimum core weight
- `max_weight_per_asset` (float, default 0.40): Maximum weight per satellite asset (40%)
- `core_grid_step` (float, default 0.01): Grid search step for core weight
- `top_k_satellite` (int, optional): Filter to top-K assets by momentum (if provided)
- `debug` (bool, default false): Enable debug logging

### Validation Rules

- `0 <= core_min <= 1`
- `0 < target_te <= 1`
- `0 < max_weight_per_asset <= 1`
- `lookback_* >= 5`
- `day_count` in [252, 365] allowed

## Bundle Semantics

**Important**: In Core-Satellite, bundle defines the **universe** (candidate instruments), NOT fixed allocations.

- If `bundle_id` is provided: bundle constituents become the instrument_ids universe
- Weights are **optimized** (not fixed) from this universe
- This is different from `bundle_strategy` where bundle weights are fixed

Example:
- Bundle "TOP5 Crypto" contains [BTC, ETH, SOL, ADA, DOT]
- Core-Satellite uses these 5 instruments as the universe
- Weights are optimized to target TE (may allocate more to BTC if momentum is strong, respecting max_weight_per_asset)

## Usage

### API Request

```json
{
  "name": "Core-Satellite Test",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "bundle_id": "1",
  "strategy": {
    "type": "CORE_SATELLITE",
    "params": {
      "core_yield": 0.035,
      "target_te": 0.10,
      "te_tolerance": 0.0025,
      "te_max_hard_mult": 1.10,
      "lookback_risk_days": 63,
      "lookback_return_days": 63,
      "day_count": 252,
      "core_min": 0.0,
      "max_weight_per_asset": 0.40,
      "core_grid_step": 0.01,
      "top_k_satellite": 10,
      "debug": false
    }
  },
  "rebalance": "weekly",
  "fees_bps": 0.0,
  "slippage_bps": 0.0,
  "allow_weekend_trading": true
}
```

### Manual Selection (without bundle)

```json
{
  "name": "Core-Satellite Manual",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "instrument_ids": [11, 27, 45],
  "strategy": {
    "type": "CORE_SATELLITE",
    "params": {
      "target_te": 0.10
    }
  },
  "rebalance": "weekly",
  "fees_bps": 0.0,
  "slippage_bps": 0.0,
  "allow_weekend_trading": true
}
```

## Output Metrics

Portfolio series contains:
- `_core_weight`: Core weight (0..1)
- `_te_realized`: Realized TE (annualized, if computed)
- `_te_pred`: Predicted TE (if available from last rebalance)

Metrics:
- `total_return`: Total return (%)
- `annualized_return`: Annualized return (%)
- `volatility`: Annualized volatility (%)
- `sharpe_ratio`: Sharpe ratio
- `max_drawdown`: Maximum drawdown (%)
- `realized_te`: Final realized TE (annualized)
- `avg_core_weight`: Average core weight (%)

## Differences from Other Strategies

### vs Bundle Strategy
- **Bundle Strategy**: Fixed allocations from bundle (e.g., 80% BTC, 20% ETH), no optimization
- **Core-Satellite**: Bundle defines universe, weights are optimized to target TE

### vs CPPI
- **CPPI**: Dynamic allocation based on cushion (floor protection), multiplier-based
- **Core-Satellite**: Optimization-based allocation to target TE, no floor protection

### vs Equal Weight / Momentum
- **Equal Weight / Momentum**: Simple weight rules, no core/satellite split
- **Core-Satellite**: Core/satellite split with TE targeting

## UI Notes

When bundle is selected and strategy == CORE_SATELLITE:
- Show note: "Bundle defines the universe. Weights are optimized (not fixed). Benchmark is CORE."
- Do NOT lock strategy to "Bundle allocation"

## Charts

- **Main chart**: Portfolio NAV + Core Benchmark NAV (core_nav_base100)
- **Core Weight chart**: Core Weight (%) over time (full width, large)
- **Optional**: Realized TE (%) vs target_te line (mini chart)

---

## V2.1 — EDHEC-style Allocation Modes

V2.1 introduces three EDHEC-style allocation modes that determine the scalar satellite weight `w` (overall allocation to the satellite sleeve) based on different criteria:

1. **TE-targeting** (`allocation_mode="te_target"`): Simple deterministic allocation based on target TE vs satellite TE
2. **Utility/risk-aversion** (`allocation_mode="utility_lambda"`): EDHEC utility form using Information Ratio and risk aversion
3. **Dynamic cushion** (`allocation_mode="dynamic_cushion"`): Dynamic allocation based on relative performance cushion

### Definitions

- **Core benchmark**: Synthetic fixed-yield accrual (same as V1/V2 simplification)
- **Satellite unit portfolio**: Portfolio of risky assets with weights summing to 1.0, optimized using V2 solver (quadratic or grid)
- **Scalar `w`**: Overall allocation to satellite (0 ≤ w ≤ 1), computed using EDHEC-style formulas
- **Final portfolio**: `w_core = 1 - w`, `w_sat_i = w * w_unit_i` where `w_unit_i` are unit portfolio weights

### Formulas

#### Tracking Error (TE)

- **Realized TE**: `TE_realized = std(active_returns) * sqrt(day_count)` where active_returns = portfolio_returns - core_returns
- **Predicted TE for unit satellite**: `TE_sat = sqrt(w_unit^T Σ w_unit) * sqrt(day_count)` where Σ is covariance matrix

#### Information Ratio (IR)

- **IR for unit satellite**: `IR_sat = (ER_sat) / (TE_sat + eps)` where:
  - `ER_sat = mu_sat^T w_unit - mu_core` (excess return proxy, annualized)
  - `mu_sat`: Expected returns vector (momentum: mean returns over `lookback_return_days`)
  - `mu_core`: Core daily return * day_count (annualized)

### Allocation Modes

#### 1. TE-Targeting (`te_target`)

**Formula**:
```
w = clamp(target_te / max(TE_sat, eps), sat_min, sat_max)
```

- If `TE_sat` is very small → use `sat_max`
- Enforce hard TE cap: `w * TE_sat <= target_te * te_max_hard_mult` (if `te_max_hard_mult` provided)

**Example JSON**:
```json
{
  "allocation_mode": "te_target",
  "target_te": 0.10,
  "sat_min": 0.0,
  "sat_max": 0.8,
  "core_min": 0.0,
  "core_yield": 0.035,
  "optimization_method": "quadratic"
}
```

#### 2. Utility/Risk-Aversion (`utility_lambda`)

**Formula**:
```
w* = clamp(IR_sat / (2 * lambda_risk * max(TE_sat, eps)), sat_min, sat_max)
```

- Higher `lambda_risk` → lower `w` (more risk-averse)
- If `IR_sat` is missing or `TE_sat` is 0 → fallback to `sat_min`
- Optional: enforce hard TE cap (same as `te_target`)

**Example JSON**:
```json
{
  "allocation_mode": "utility_lambda",
  "lambda_risk": 0.2,
  "target_te": 0.10,
  "te_max_hard_mult": 1.10,
  "sat_min": 0.0,
  "sat_max": 0.8,
  "core_yield": 0.035,
  "optimization_method": "quadratic"
}
```

#### 3. Dynamic Cushion (`dynamic_cushion`)

**State tracking**:
- **Relative index**: `rel_index(t) = rel_index(t-1) * (1 + r_p(t)) / (1 + r_c(t))` (starts at 1.0)
- **Relative floor**: 
  - If `floor_accrues_with_core=true`: `rel_floor(t) = rel_floor(t-1) * (1 + core_daily_return)^days` (starts at `floor_rel_ratio`)
  - Else: `rel_floor(t) = floor_rel_ratio` (constant)
- **Cushion**: `cushion = max(rel_index - rel_floor, 0)`

**Formula**:
```
w = clamp(multiplier * cushion, sat_min, sat_max)
```

**Example JSON**:
```json
{
  "allocation_mode": "dynamic_cushion",
  "multiplier": 4.0,
  "floor_rel_ratio": 0.95,
  "floor_accrues_with_core": true,
  "sat_min": 0.0,
  "sat_max": 0.8,
  "core_yield": 0.035,
  "optimization_method": "quadratic"
}
```

### weights_json Fields (V2.1)

Each `portfolio_series` bar contains `weights_json` with the following V2.1 fields:

**Obligatory fields** (always present):
- `_cs_alloc_mode` (string): Allocation mode used ("te_target", "utility_lambda", "dynamic_cushion")
- `_cs_sat_weight_scalar` (float 0..1): Scalar satellite weight `w`
- `_cs_te_sat` (float): Predicted TE for unit satellite portfolio (annualized)
- `_cs_ir_sat` (float|null): Information Ratio for unit satellite portfolio (can be null if undefined)

**Conditional fields** (only if `allocation_mode == "dynamic_cushion"`):
- `_cs_rel_index` (float): Relative performance index
- `_cs_rel_floor` (float): Relative floor
- `_cs_cushion` (float): Cushion (max(rel_index - rel_floor, 0))

**Existing V1/V2 fields** (still present):
- `_core_weight`: Core weight
- `_te_realized`: Realized TE (if computed)
- `_te_pred`: Predicted TE for final portfolio
- `_te_pred_shrunk`: Predicted TE with shrinkage (if shrinkage enabled)
- `_satellite_turnover`, `_portfolio_turnover`, `_optimization_score`: V2 metrics

### Charts Usage

The frontend `CoreSatelliteCharts` component uses these fields to display:
- **Core-Satellite Allocation chart**: `_cs_sat_weight_scalar` and `_core_weight` over time
- **Tracking Error chart**: `_te_realized` vs `target_te` (if available)
- **Dynamic Cushion chart**: `_cs_rel_index`, `_cs_rel_floor`, `_cs_cushion` (if `allocation_mode == "dynamic_cushion"`)

### Parameters Summary (V2.1)

All V1/V2 parameters remain valid. V2.1 adds:

- `allocation_mode` (str, default "te_target"): "te_target" | "utility_lambda" | "dynamic_cushion"
- `lambda_risk` (float, default 0.2): Risk aversion for `utility_lambda` mode
- `multiplier` (float, default 4.0): Multiplier for `dynamic_cushion` mode
- `floor_rel_ratio` (float, default 0.95): Relative floor ratio for `dynamic_cushion` mode
- `floor_accrues_with_core` (bool, default true): Whether floor accrues with core_yield
- `sat_max` (float, optional): Maximum satellite weight (default: 1 - core_min)

See V1/V2 documentation for all other parameters.
