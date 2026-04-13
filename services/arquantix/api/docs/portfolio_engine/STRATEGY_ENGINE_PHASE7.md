# PRD — Vancelian Portfolio Engine Phase 7 — Strategy Engine

**Version:** v1.0
**Status:** Product Requirements Document
**Owner:** Vancelian Engineering
**Scope:** Portfolio Engine — Strategy Evaluation Layer

---

## 1. Purpose

The portfolio engine already supports:
- portfolio allocations
- valuation
- drift detection
- rebalance preview

However, the system lacks a decision layer.

Currently:
- rebalancing must be manually triggered
- no automated strategy evaluation exists
- portfolios cannot operate under configurable strategy logic

Phase 7 introduces the Strategy Engine, responsible for:
- evaluating portfolio strategies
- detecting signals
- generating recommended actions
- orchestrating portfolio decisions

The Strategy Engine does not execute trades directly.
It produces signals and actions for higher layers.

---

## 2. Objectives

The Strategy Engine must:
1. Evaluate strategy rules for a portfolio
2. Determine if a rebalance or other action is required
3. Generate strategy signals
4. Produce strategy actions
5. Maintain strategy evaluation logs

---

## 3. Strategy Concepts

### Strategy Definition

A Strategy Definition describes the logic of a strategy.

Examples:
- threshold_rebalance
- periodic_rebalance
- drift_guard
- risk_limit

These definitions are global templates.

### Strategy Instance

A Strategy Instance binds a strategy definition to a portfolio.

Example:
- Strategy: threshold_rebalance
- Portfolio: 123
- Threshold: 5%

Each portfolio may have multiple strategies active.

### Strategy Evaluation

Evaluation determines whether the strategy conditions are met.

Example:
```
drift > threshold → signal = rebalance
```

---

## 4. Strategy Types

Phase 7 supports four strategy types.

### 1. Threshold Rebalance

Trigger rebalance when drift exceeds threshold.

```
abs(drift) > threshold
```

Uses the Drift Engine (Phase 6).

### 2. Periodic Rebalance

Trigger rebalance periodically.

Example:
- monthly
- quarterly
- yearly

Evaluation compares:
```
now - last_rebalance_date
```

### 3. Drift Guard

Detect excessive drift even if rebalance not executed.

Example:
```
drift > warning_threshold
```

Produces warning signals.

### 4. Risk Limit

Evaluate risk constraints.

Example:
```
asset_weight > max_asset_weight
```

Uses the risk policy module.

---

## 5. Strategy Evaluation Flow

```
portfolio
    ↓
load active strategies
    ↓
evaluate strategies
    ↓
generate signals
    ↓
generate actions
```

---

## 6. Strategy Signals

Signals represent detected conditions.

| Signal | Description |
|--------|-------------|
| REBALANCE_REQUIRED | portfolio drift exceeded threshold |
| PERIODIC_REBALANCE | scheduled rebalance time reached |
| RISK_LIMIT_EXCEEDED | asset exceeds max weight |
| DRIFT_WARNING | drift approaching limit |

Signals do not trigger trades directly.

---

## 7. Strategy Actions

Actions represent recommended operations.

| Action | Description |
|--------|-------------|
| CREATE_REBALANCE_PREVIEW | generate rebalance plan |
| ALERT_RISK | notify risk system |
| NO_ACTION | no change required |

---

## 8. Strategy Engine Service

Create a new service:

**StrategyEngineService**

Main methods:
- `evaluate_portfolio_strategies(db, portfolio_id)`
- `evaluate_strategy(db, strategy_instance)`
- `generate_strategy_signal(...)`

---

## 9. Strategy Evaluation Result

Example response:

```json
{
  "portfolio_id": "...",
  "evaluated_at": "2026-03-20T10:00:00Z",
  "signals": [
    {
      "type": "REBALANCE_REQUIRED",
      "strategy": "threshold_rebalance",
      "severity": "medium"
    }
  ],
  "actions": [
    {
      "type": "CREATE_REBALANCE_PREVIEW"
    }
  ]
}
```

---

## 10. Strategy Logging

Strategy evaluations should be logged.

Create a table: **pe_strategy_evaluations**

Fields:
- id
- portfolio_id
- strategy_instance_id
- signal_type
- action_type
- evaluation_timestamp
- metadata

Append-only.

---

## 11. Strategy Engine Module

New module:

```
strategy_engine/
 ├── __init__.py
 ├── enums.py
 ├── schemas.py
 ├── service.py
 ├── repository.py
 └── router.py
```

---

## 12. Strategy Types Enum

**StrategyType**

Values:
- threshold_rebalance
- periodic_rebalance
- drift_guard
- risk_limit

---

## 13. Strategy Signal Enum

**StrategySignalType**

Values:
- REBALANCE_REQUIRED
- PERIODIC_REBALANCE
- DRIFT_WARNING
- RISK_LIMIT_EXCEEDED

---

## 14. Strategy Action Enum

**StrategyActionType**

Values:
- CREATE_REBALANCE_PREVIEW
- ALERT_RISK
- NO_ACTION

---

## 15. Evaluation Algorithm

```
load portfolio strategies

for each strategy:
    evaluate conditions

    if condition met:
        create signal
        create action
```

---

## 16. Integration With Existing Engines

Strategy Engine must reuse:

| Module | Purpose |
|--------|---------|
| drift engine | detect drift |
| valuations | portfolio NAV |
| allocations | target weights |
| risk policies | risk checks |
| rebalance_preview | plan persistence |

No duplication of logic.

---

## 17. API Endpoints

### Evaluate strategies

```
POST /portfolio-engine/portfolios/{id}/strategy-evaluation
```

Runs evaluation and returns signals.

### Get strategy signals

```
GET /portfolio-engine/portfolios/{id}/strategy-signals
```

Returns last evaluation signals.

### Trigger strategy action

```
POST /portfolio-engine/strategies/{id}/execute
```

Optional manual trigger.

---

## 18. Edge Cases

### Portfolio without strategies

Return:
```
signals = []
actions = []
```

### Missing valuation

Strategy evaluation fails gracefully.

### Conflicting strategies

Example:
- periodic rebalance
- threshold rebalance

Both may trigger simultaneously.

---

## 19. Tests Required

Tests must cover:
1. threshold rebalance detection
2. periodic rebalance detection
3. drift warning detection
4. risk limit detection
5. strategy evaluation with multiple strategies
6. no strategy case
7. evaluation logging
8. signal generation
9. action generation

---

## 20. What Phase 7 Must NOT Modify

The following modules must remain unchanged:
- orders
- executions
- trades
- settlement
- ledger
- positions
- valuation engine
- drift engine

Strategy Engine reads existing modules but does not alter them.
