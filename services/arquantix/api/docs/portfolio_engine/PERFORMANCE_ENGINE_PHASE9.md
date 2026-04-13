# PRD — Vancelian Portfolio Engine Phase 9 — Performance & Benchmark Engine

**Version:** v1.0
**Status:** Product Requirements Document
**Owner:** Vancelian Engineering
**Scope:** Portfolio Engine — Performance Measurement

---

## 1. Purpose

The portfolio engine already provides:
- positions
- valuation
- drift detection
- rebalance orchestration

However, the system does not yet compute portfolio performance metrics.

Phase 9 introduces the Performance Engine, responsible for:
- computing portfolio returns
- calculating time series performance
- measuring realized vs unrealized profit
- comparing portfolio performance against benchmarks

---

## 2. Goals

Phase 9 must allow the system to:
- compute portfolio performance over time
- produce time-series returns
- calculate cumulative performance
- compute portfolio drawdown
- compare portfolio performance to benchmarks

The performance engine does not modify any existing financial state.
It only reads existing valuation and trade data.

---

## 3. Core Concepts

### Portfolio Value Series

Portfolio value history is derived from:

**pe_portfolio_valuations**

Snapshots created in Phase 5.

Each snapshot contains:
- portfolio_id
- nav
- valuation_timestamp

These snapshots form the time series of portfolio value.

---

## 4. Return Types

Phase 9 must support two return calculation methods.

### Time-Weighted Return (TWR)

Removes the impact of cash flows.

Formula:
```
R_t = (NAV_t / NAV_{t-1}) - 1
```

Total performance:
```
Π (1 + R_t) - 1
```

This is the standard portfolio manager metric.

### Money-Weighted Return (MWR / IRR)

Includes impact of cash flows.

Derived from:
- deposits
- withdrawals
- cash flows

IRR calculation:
```
NPV = Σ (CF_t / (1+r)^t) = 0
```

For Phase 9 v1:
- TWR is mandatory
- MWR optional (may be added later)

---

## 5. Performance Metrics

The system must compute:

| Metric | Description |
|--------|-------------|
| total_return | cumulative portfolio return |
| period_return | return over selected period |
| max_drawdown | largest portfolio decline |
| volatility | std deviation of returns |
| winning_days_ratio | percentage of positive days |

---

## 6. Drawdown Calculation

Drawdown measures the decline from peak.

Algorithm:
```
peak = max(previous_nav)
drawdown = (nav - peak) / peak
```

Track:
- max_drawdown

---

## 7. Benchmark Comparison

Each portfolio may have an optional benchmark.

Example:
- BTC
- SP500
- 60/40 index
- custom allocation

Benchmark price series may come from:
- market_data_latest_quotes
- or a future benchmark service

---

## 8. Benchmark Metrics

Calculate:

| Metric | Description |
|--------|-------------|
| portfolio_return | |
| benchmark_return | |
| alpha | portfolio − benchmark |
| tracking_error | |

---

## 9. Performance Engine Service

Create new service:

**PerformanceService**

Methods:
- `compute_portfolio_returns(db, portfolio_id)`
- `compute_drawdown(series)`
- `compute_volatility(series)`
- `compare_to_benchmark(db, portfolio_id)`

---

## 10. Time Series Generation

Algorithm:
```
load portfolio valuation snapshots
sort by valuation_timestamp
compute period returns
compute cumulative returns
```

Output example:
- date
- nav
- period_return
- cumulative_return

---

## 11. Performance Snapshot Table

Create new table: **pe_portfolio_performance**

Fields:
- id
- portfolio_id
- period_start
- period_end
- total_return
- max_drawdown
- volatility
- benchmark_return
- alpha
- created_at

Append-only.

---

## 12. Performance Time Series Table

Create: **pe_portfolio_return_series**

Fields:
- id
- portfolio_id
- timestamp
- nav
- period_return
- cumulative_return
- drawdown
- created_at

Append-only.

---

## 13. Performance Engine Module

Create module:

```
performance/
 ├── __init__.py
 ├── models.py
 ├── schemas.py
 ├── repository.py
 ├── service.py
 └── router.py
```

---

## 14. API Endpoints

### Portfolio performance summary

```
GET /portfolio-engine/portfolios/{id}/performance
```

Returns:
- total_return
- max_drawdown
- volatility
- benchmark_comparison

### Performance time series

```
GET /portfolio-engine/portfolios/{id}/performance-series
```

Returns NAV series and cumulative returns.

### Benchmark comparison

```
GET /portfolio-engine/portfolios/{id}/benchmark
```

Returns alpha and benchmark performance.

---

## 15. Edge Cases

### Not enough snapshots

If less than 2 valuation snapshots:
```
return empty performance
```

### Missing benchmark

If no benchmark configured:
```
skip comparison
```

### NAV = 0

Return:
```
performance undefined
```

---

## 16. Integration with Existing Modules

Performance engine reads from:

| Module | Purpose |
|--------|---------|
| valuations | NAV snapshots |
| positions | realized pnl |
| market data | benchmark pricing |

No writes to trading or ledger modules.

---

## 17. Tests Required

Tests must include:
1. time series generation
2. cumulative return calculation
3. drawdown detection
4. volatility calculation
5. insufficient data handling
6. benchmark comparison
7. portfolio without benchmark
8. performance API responses

---

## 18. What Phase 9 Must NOT Modify

The following modules must remain unchanged:
- orders
- executions
- trades
- settlement
- ledger
- positions
- valuation engine
- drift engine
- strategy engine
- orchestrator

The performance engine is purely analytical.
