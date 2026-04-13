# PRD — Vancelian Portfolio Engine

## Phase 6 — Drift Detection & Rebalance Engine

**Version:** v1.0
**Status:** Product Requirements Document
**Owner:** Vancelian Engineering
**Scope:** Portfolio Engine — Portfolio Rebalancing

---

## 1. Purpose

The Vancelian platform already supports:
- portfolio structure
- target allocations
- transaction engine
- position engine
- valuation engine

The system can compute:

```
current portfolio weights
target allocation weights
```

However, the system currently cannot detect portfolio drift or generate rebalance instructions.

Phase 6 introduces the Drift Detection and Rebalance Engine.

---

## 2. Goals

Phase 6 must allow the system to:
- detect when a portfolio drifts from its target allocation
- measure the magnitude of the drift
- determine whether rebalancing is required
- generate a rebalance preview
- compute the trades required to rebalance

This phase does not automatically execute trades.

It only generates a rebalance plan.

---

## 3. Key Concepts

### Target Allocation

Defined by the portfolio strategy.

Example:

| Asset | Target Weight |
|-------|--------------|
| BTC   | 50%          |
| ETH   | 30%          |
| SOL   | 20%          |

### Current Allocation

Derived from the Valuation Engine.

Example:

| Asset | Current Weight |
|-------|---------------|
| BTC   | 65%           |
| ETH   | 20%           |
| SOL   | 15%           |

### Drift

Drift represents the difference between target and current allocation.

Formula:

```
drift = current_weight - target_weight
```

Example:

| Asset | Target | Current | Drift |
|-------|--------|---------|-------|
| BTC   | 50%    | 65%     | +15%  |
| ETH   | 30%    | 20%     | -10%  |
| SOL   | 20%    | 15%     | -5%   |

---

## 4. Drift Threshold

Rebalancing should only occur if drift exceeds a threshold.

Example:

```
rebalance_threshold = 5%
```

If:

```
abs(drift) > threshold
```

then the asset requires rebalancing.

---

## 5. Portfolio Drift Calculation

Algorithm:

```
1. retrieve portfolio valuation
2. retrieve target allocation
3. compute current weights
4. compute drift
5. detect threshold violations
```

---

## 6. Rebalance Preview

The rebalance engine must compute the trades needed to restore target weights.

Steps:

```
target_value = portfolio_nav * target_weight
current_value = position.market_value

rebalance_delta = target_value - current_value
```

Interpretation:

| Delta    | Action |
|----------|--------|
| positive | BUY    |
| negative | SELL   |

---

## 7. Trade Quantity Calculation

To compute the trade quantity:

```
trade_qty = abs(rebalance_delta) / market_price
```

Example:

```
ETH current value = 20k
ETH target value = 30k

delta = +10k

price = 2000

trade_qty = 5 ETH
```

---

## 8. Rebalance Preview Model

Create a new structure.

Example response:

```json
{
  "portfolio_id": "...",
  "nav": "50000",
  "threshold": "0.05",
  "assets": [
    {
      "instrument": "BTC",
      "target_weight": "0.50",
      "current_weight": "0.65",
      "drift": "0.15",
      "action": "sell",
      "trade_value": "7500",
      "trade_quantity": "0.107"
    }
  ]
}
```

---

## 9. Rebalance Plan Table (Optional)

Optionally store rebalance plans.

Proposed table:

**pe_rebalance_plans**

Fields:

| Field        | Type       |
|-------------|------------|
| id          | UUID       |
| portfolio_id| UUID       |
| nav         | NUMERIC    |
| threshold   | NUMERIC    |
| status      | VARCHAR    |
| created_at  | TIMESTAMPTZ|
| metadata    | JSONB      |

---

## 10. Rebalance Trades Table

**pe_rebalance_trades**

Fields:

| Field          | Type       |
|---------------|------------|
| id            | UUID       |
| plan_id       | UUID       |
| instrument_id | UUID       |
| target_weight | NUMERIC    |
| current_weight| NUMERIC    |
| drift         | NUMERIC    |
| action        | VARCHAR    |
| trade_value   | NUMERIC    |
| trade_quantity | NUMERIC   |
| price         | NUMERIC    |
| created_at    | TIMESTAMPTZ|

---

## 11. RebalanceService

Create a new service.

**RebalanceService**

Functions:

```
detect_drift(portfolio_id)
generate_rebalance_preview(portfolio_id)
create_rebalance_plan(portfolio_id)
```

---

## 12. Rebalance Workflow

Typical flow:

```
portfolio valuation
↓
drift detection
↓
rebalance preview
↓
(optional) create rebalance plan
↓
user approval
↓
execution engine
```

---

## 13. Handling Small Positions

Positions below a minimum threshold may be ignored.

Example:

```
min_position_value = $50
```

---

## 14. Handling Missing Prices

If an asset cannot be priced:

```
asset excluded from rebalance calculation
```

---

## 15. Partial Rebalance

Rebalancing does not require full reset.

If drift is small:

```
no rebalance
```

---

## 16. API Endpoints

### Drift detection

```
GET /portfolio-engine/portfolios/{id}/drift
```

Returns drift metrics.

### Rebalance preview

```
GET /portfolio-engine/portfolios/{id}/rebalance-preview
```

Returns computed trades.

### Create rebalance plan

```
POST /portfolio-engine/portfolios/{id}/rebalance-plan
```

Creates a plan but does not execute.

---

## 17. Tests Required

Tests must include:
1. drift calculation correctness
2. threshold detection
3. rebalance preview calculation
4. trade quantity computation
5. handling missing prices
6. ignoring small positions
7. correct buy/sell detection

---

## 18. What Phase 6 Must NOT Change

The following modules must remain untouched:

- pe_orders
- pe_execution_instructions
- pe_trades
- pe_settlement_instructions
- pe_ledger_entries
- pe_position_atoms
- valuation engine

Phase 6 only generates rebalance suggestions.

Execution remains manual.

---

End of PRD — Phase 6
