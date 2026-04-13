# PRD — Vancelian Portfolio Engine

## Phase 5 — Valuation & Performance Engine

**Version:** v1.0
**Status:** Product Requirements Document
**Owner:** Vancelian Engineering
**Scope:** Portfolio Engine — Portfolio Valuation

---

## 1. Purpose

The portfolio engine already maintains portfolio positions through the Position Engine (Phase 4).

Positions contain:
- quantity
- average entry price
- realized pnl

However, the system currently does not compute:
- current market value
- unrealized pnl
- portfolio NAV
- allocation weights
- portfolio performance

Phase 5 introduces the Valuation Engine responsible for deriving these metrics.

---

## 2. Goal of Phase 5

The Valuation Engine must allow the system to compute:
- current value of every position
- unrealized profit and loss
- total portfolio NAV
- allocation weight per asset
- portfolio performance summary

These values must be derived without modifying the ledger or trades.

---

## 3. Architectural Principles

### 3.1 Positions remain the economic base

Valuation is derived from positions.

```
PositionAtom → Valuation → Portfolio NAV
```

Positions are the state.

Valuation is a derived view.

### 3.2 Market price source

Market prices must come from the Market Data Bridge already implemented.

The valuation engine must use:

```
current_price(instrument_id)
```

This price source may come from:
- CoinGecko
- exchange price feeds
- internal price service

### 3.3 No accounting modification

The valuation engine must never modify:
- trades
- settlements
- ledger entries

Valuation is purely read-only derived data.

---

## 4. Position Valuation

For every open position:

```
market_value = quantity * current_price
```

Example:

```
BTC price = 70,000
position qty = 0.5

market_value = 35,000
```

---

## 5. Unrealized PnL

Unrealized PnL is calculated as:

```
unrealized_pnl = quantity * (current_price - average_entry_price)
```

Example:

```
BUY 0.5 BTC @ 68,000
current_price = 70,000

unrealized_pnl = 0.5 * (70k - 68k)
```

---

## 6. Portfolio NAV

NAV (Net Asset Value) represents the total value of a portfolio.

```
portfolio_nav = Σ position.market_value
```

Example:

| Asset | Value  |
|-------|--------|
| BTC   | 35,000 |
| ETH   | 12,000 |
| SOL   | 4,000  |

NAV = 51,000

---

## 7. Portfolio Allocation

Asset allocation weight must be calculated as:

```
weight = position.market_value / portfolio_nav
```

Example:

| Asset | Value | Weight |
|-------|-------|--------|
| BTC   | 35k   | 68%    |
| ETH   | 12k   | 23%    |
| SOL   | 4k    | 9%     |

---

## 8. Position Valuation Model

Valuation may be stored in a derived table.

Proposed table:

**pe_position_valuations**

Fields:

| Field                | Type              |
|----------------------|-------------------|
| id                   | UUID PK           |
| position_id          | UUID FK → pe_position_atoms |
| instrument_id        | UUID              |
| portfolio_id         | UUID              |
| price                | NUMERIC(30,10)    |
| market_value         | NUMERIC(30,10)    |
| unrealized_pnl       | NUMERIC(30,10)    |
| valuation_timestamp  | TIMESTAMPTZ       |
| created_at           | TIMESTAMPTZ       |

This table is optional but recommended for:
- historical valuation
- performance analysis
- analytics

---

## 9. Portfolio Valuation Table

Portfolio summary may also be stored.

Proposed table:

**pe_portfolio_valuations**

Fields:

| Field                  | Type              |
|------------------------|-------------------|
| id                     | UUID PK           |
| portfolio_id           | UUID              |
| nav                    | NUMERIC(30,10)    |
| total_unrealized_pnl   | NUMERIC(30,10)    |
| total_realized_pnl     | NUMERIC(30,10)    |
| valuation_timestamp    | TIMESTAMPTZ       |
| created_at             | TIMESTAMPTZ       |

---

## 10. Valuation Frequency

Valuation may occur in two ways.

### On-demand valuation

When the client opens the app:

```
GET /portfolio/summary
```

valuation is computed dynamically.

### Scheduled valuation

A background job runs every:
- 1 minute
- 5 minutes
- or configurable interval

and stores valuation snapshots.

---

## 11. ValuationService

A new service must be implemented.

**ValuationService**

Responsibilities:

```
value_position(position)
value_portfolio(portfolio_id)
```

### Algorithm

```
positions = get_open_positions(portfolio)

for position in positions:
    price = market_price(instrument)
    market_value = qty * price
    unrealized_pnl = qty * (price - avg_entry_price)

Aggregate NAV.
```

---

## 12. Handling Missing Prices

Some instruments may not have price feeds.

Example:
- private deals
- vault tokens
- locked assets

In this case:

```
price = NULL
market_value = NULL
unrealized_pnl = NULL
```

These positions must not break valuation.

---

## 13. Position Types

Valuation logic depends on position_type.

| Position Type  | Valuation       |
|---------------|-----------------|
| spot          | market price    |
| vault         | internal NAV    |
| private_deal  | manual valuation|
| staked        | market price    |

Phase 5 only implements spot valuation.

Other types will be added later.

---

## 14. Performance Summary

Portfolio performance must expose:

```
total_realized_pnl
total_unrealized_pnl
total_pnl
```

Where:

```
total_pnl = realized + unrealized
```

---

## 15. API Endpoints

New endpoints must be added.

### Portfolio summary

```
GET /portfolio-engine/portfolio/{id}/summary
```

Response:

```json
{
  "nav": "...",
  "realized_pnl": "...",
  "unrealized_pnl": "...",
  "positions": []
}
```

### Position valuation

```
GET /portfolio-engine/positions/{id}/valuation
```

---

## 16. Tests Required

Tests must include:
1. valuation of single position
2. unrealized pnl calculation
3. portfolio NAV aggregation
4. allocation weight calculation
5. missing price handling
6. multiple positions valuation
7. correct aggregation realized + unrealized pnl

---

## 17. What Phase 5 Must NOT Change

The following modules must not be modified:

- pe_orders
- pe_execution_instructions
- pe_trades
- pe_settlement_instructions
- pe_ledger_entries
- pe_ledger_accounts

Valuation is a derived layer only.

---

End of PRD — Phase 5
