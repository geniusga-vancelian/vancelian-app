# CPPI Strategy (Constant Proportion Portfolio Insurance)

## Overview

CPPI is a portfolio insurance strategy that dynamically allocates between a **risky sleeve** (market-priced instruments) and a **core sleeve** (synthetic fixed-yield accrual) to maintain a floor value while participating in upside.

## Formulas

### State Variables

- **V_t**: Total NAV at time t
- **F_t**: Floor at time t (indexed floor, grows daily with core_yield)
  - **F_0**: Initial floor = `floor_ratio * V_0`
  - **F_t**: Floor at time t = `F_{t-1} * (1 + core_yield * dt)`
    where `dt = days_between(prev_date, cur_date) / day_count`
- **K_t**: Cushion = `max(V_t - F_t, 0)`
- **R_t**: Risky sleeve value (market-priced)
- **C_t**: Core sleeve value (accrual-based)

### Floor Growth (CPPI v1.1)

The floor grows daily with the same annualized yield as the core sleeve:

```
F_0 = floor_ratio * V_0
F_t = F_{t-1} * (1 + core_yield * dt)
```

where `dt = days_between(prev_date, cur_date) / day_count`

**Example**: V_0=100, floor_ratio=0.9, core_yield=5%, 1 year
- F_0 = 0.9 * 100 = 90
- F_1y ≈ 90 * 1.05 = 94.5

The floor is updated on **every date** (daily), not only on rebalance dates, so it grows continuously.

### Target Allocation

On each rebalance date:

1. Compute cushion: `K_t = max(V_t - F_t, 0)`
2. Compute risky target: `RISKY_TARGET = min(multiplier * K_t, risky_cap * V_t)`
3. Compute core target: `CORE_TARGET = V_t - RISKY_TARGET`
4. Enforce core minimum: 
   - If `CORE_TARGET < core_min * V_t`:
     - `CORE_TARGET = core_min * V_t`
     - `RISKY_TARGET = V_t - CORE_TARGET`

### Rebalancing

- **Rebalance frequency**: daily, weekly, or monthly
- **Skip rebalance** if any required risky price is missing on rebalance date
- **Risky sleeve composition**: 
  - If bundle selected: uses bundle effective weights
  - Else: equal-weight across selected instruments
- **Core sleeve**: 
  - Accrues daily at constant yield: `core_value *= (1 + core_yield / day_count)`
  - Residual after risky allocation
- **Transaction costs**: Applied on risky trades only (fees_bps + slippage_bps)

## V1.1 Features (Current)

- **Single core yield**: Core sleeve uses one constant annual yield (default 3.5%)
- **No liquidity constraints**: Core is fully liquid (no lockups)
- **Indexed floor**: Floor grows daily with the same core_yield (CPPI v1.1)
  - Initial: `F_0 = floor_ratio * V_0`
  - Daily: `F_t = F_{t-1} * (1 + core_yield * dt)`
  - This ensures floor performance matches core performance, making NAV vs Floor comparisons meaningful
- **No core buckets**: Core is a single accrual asset, not multiple buckets with different yields/lockups

## V1.0 (Deprecated)

- **Static floor**: Floor was computed once at start (V_0 * floor_ratio), not dynamic

## Parameters

- `floor_ratio` (0-1): Floor as ratio of initial capital (default: 0.90)
- `multiplier` (>0): Multiplier for cushion (default: 4.0)
- `risky_cap` (0-1): Maximum risky weight (default: 1.0)
- `core_min` (0-1): Minimum core weight (default: 0.0)
- `core_yield` (0-1): Annual yield for core sleeve (default: 0.035 = 3.5%)
- `day_count` (int): Days per year for accrual (default: 365)

## Usage

### API Request

```json
{
  "name": "CPPI Test",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "bundle_id": "1",
  "strategy": {
    "type": "CPPI",
    "params": {
      "floor_ratio": 0.90,
      "multiplier": 4.0,
      "risky_cap": 1.0,
      "core_min": 0.0,
      "core_yield": 0.035,
      "day_count": 365
    }
  },
  "rebalance": "weekly",
  "fees_bps": 0.0,
  "slippage_bps": 0.0,
  "allow_weekend_trading": true
}
```

### UI

1. Select **Strategy**: "CPPI"
2. Configure CPPI parameters (floor ratio, multiplier, risky cap, core min)
3. Select instruments or bundle for risky sleeve
4. Run backtest

## Differences from "Bundle fixed target weights"

- **Bundle strategy**: Fixed allocations within risky sleeve (e.g., 80% BTC, 20% ETH), no floor protection
- **CPPI**: Dynamic allocation between risky and core sleeves based on cushion, with floor protection

## Output Metrics

- `_cppi_cushion`: Cushion value (V_t - F)
- `_cppi_risky_weight`: Risky weight (R_t / V_t)
- `_cppi_core_weight`: Core weight (C_t / V_t)
- `_cppi_floor`: Floor value (F)

Stored in `weights_json` field of portfolio series.

