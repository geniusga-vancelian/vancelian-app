# PRD — Vancelian Portfolio Engine Phase 8 — Automated Rebalance Orchestrator

**Version:** v1.0
**Status:** Product Requirements Document
**Owner:** Vancelian Engineering
**Scope:** Portfolio Engine — Rebalance Orchestration

---

## 1. Purpose

The Strategy Engine (Phase 7) produces:
- signals
- actions

However, the system currently requires manual intervention to execute actions such as creating rebalance plans.

Phase 8 introduces the Rebalance Orchestrator, which automates the workflow between:
- Strategy Evaluation
- Rebalance Plan Creation
- Execution Instruction Generation

The orchestrator ensures that the portfolio engine can operate in manual, semi-automatic, or fully automated modes.

---

## 2. Goals

Phase 8 must allow the system to:
- automatically evaluate strategies
- automatically create rebalance plans
- optionally convert plans into execution instructions
- enforce operational safety rules
- maintain full auditability

---

## 3. Orchestration Modes

Each portfolio may operate under a specific orchestration mode.

Enum: **RebalanceExecutionMode**

Values:
- manual
- assisted
- automatic

### Manual

```
Strategy → Signal
Human triggers preview
Human triggers execution
```

### Assisted

```
Strategy → Signal
System creates preview
Human approves execution
```

### Automatic

```
Strategy → Signal
System creates preview
System creates execution instructions
```

Trades are still executed through the execution engine.

---

## 4. Orchestrator Responsibilities

The orchestrator must:
1. trigger strategy evaluation
2. collect strategy actions
3. resolve conflicts
4. create rebalance previews if required
5. optionally generate execution instructions

---

## 5. Rebalance Workflow

```
evaluate strategies
      ↓
collect signals/actions
      ↓
if CREATE_REBALANCE_PREVIEW
      ↓
generate rebalance plan
      ↓
depending on mode:
    manual → stop
    assisted → await approval
    automatic → generate executions
```

---

## 6. Conflict Resolution

Multiple strategies may trigger simultaneously.

Example:
- threshold_rebalance
- periodic_rebalance
- risk_limit

Rules:
1. risk_limit has highest priority
2. threshold_rebalance next
3. periodic_rebalance lowest

Only one rebalance plan should be generated per orchestration cycle.

---

## 7. Orchestrator Service

Create a new service:

**RebalanceOrchestratorService**

Main methods:
- `run_portfolio_cycle(db, portfolio_id)`
- `handle_strategy_actions(...)`
- `generate_execution_instructions(...)`

---

## 8. Orchestration Cycle

Algorithm:

```
load portfolio orchestration mode

evaluate strategies

collect actions

if CREATE_REBALANCE_PREVIEW:
    create rebalance plan

if mode == automatic:
    convert preview into execution instructions
```

---

## 9. Execution Instruction Generation

Execution instructions are derived from the rebalance preview.

For each preview item:
- trade_direction → BUY or SELL
- trade_quantity
- instrument_id

Create records in: **pe_execution_instructions**

Use existing ExecutionService.

---

## 10. Safety Rules

The orchestrator must enforce:

### Minimum trade size

Ignore trades below:
```
min_trade_size
```

### Max trade percentage

Optional safety rule:
```
max_trade_percent_of_nav
```

### NAV validation

If NAV is zero:
```
abort orchestration
```

---

## 11. Orchestrator Logging

Create a table: **pe_orchestration_runs**

Fields:
- id
- portfolio_id
- mode
- signals_detected
- actions_executed
- rebalance_preview_id
- execution_instructions_created
- status
- started_at
- completed_at
- metadata

Append-only.

---

## 12. Orchestrator Module

New module:

```
orchestrator/
 ├── __init__.py
 ├── enums.py
 ├── models.py
 ├── schemas.py
 ├── repository.py
 ├── service.py
 └── router.py
```

---

## 13. Orchestrator Status Enum

**OrchestrationStatus**

Values:
- started
- completed
- aborted
- failed

---

## 14. API Endpoints

### Run orchestration

```
POST /portfolio-engine/portfolios/{id}/orchestrate
```

Runs full orchestration cycle.

### Orchestration history

```
GET /portfolio-engine/portfolios/{id}/orchestration-runs
```

Returns past runs.

### Get run details

```
GET /portfolio-engine/orchestration-runs/{id}
```

---

## 15. Edge Cases

### Portfolio without strategies

Return:
```
status = completed
actions_executed = 0
```

### No signals

Return:
```
status = completed
```

### Execution generation disabled

If mode != automatic:
```
skip execution generation
```

---

## 16. Integration with Existing Engines

The orchestrator must reuse:

| Engine | Purpose |
|--------|---------|
| strategy engine | evaluate strategies |
| drift engine | drift detection |
| valuation engine | NAV |
| rebalance preview | trade plan |
| execution engine | execution instructions |

No duplicate logic.

---

## 17. Tests Required

Tests must include:
1. manual mode orchestration
2. assisted mode orchestration
3. automatic mode orchestration
4. strategy signals → preview creation
5. preview → execution instructions
6. conflict resolution
7. NAV = 0 abort
8. min trade filtering
9. orchestration logging
10. orchestration history retrieval

---

## 18. What Phase 8 Must NOT Modify

The following modules must remain unchanged:
- orders
- trades
- positions
- settlement
- ledger
- valuation engine
- drift engine
- strategy engine

Phase 8 only orchestrates existing services.
