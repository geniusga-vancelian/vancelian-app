# PRD — Vancelian Portfolio Engine

## Phase 4 — Position Engine

**Version:** v1.0
**Status:** Product Requirements Document
**Owner:** Vancelian Engineering
**Scope:** Portfolio Engine — Position Lifecycle

---

## 1. Purpose

The Vancelian portfolio engine already supports the following transaction pipeline:

```
Order → ExecutionInstruction → Trade → SettlementInstruction → LedgerEntry
```

This pipeline correctly records:
- client intent
- operational execution
- confirmed trades
- settlement obligations
- accounting ledger entries

However, the system currently lacks a mechanism to maintain client portfolio positions derived from those trades.

Phase 4 introduces the Position Engine, responsible for maintaining the economic state of client portfolios.

---

## 2. Goal of Phase 4

The goal is to implement a system that:
- derives portfolio positions from confirmed trades
- maintains current position quantity per instrument
- tracks average entry price
- calculates realized PnL when positions are reduced
- closes positions when quantity reaches zero

This module must operate without modifying existing accounting logic.

---

## 3. Architectural Principles

The following architectural rules must be respected.

### 3.1 Source of truth

Trades are the economic events.

```
Trade = economic fact
Position = derived state
```

Positions are derived and mutable.

Trades are immutable.

### 3.2 Accounting independence

Ledger entries represent accounting truth.

Position state represents economic exposure.

These must remain separate.

```
Ledger → accounting
Position → portfolio exposure
```

Ledger updates must never modify positions directly.

### 3.3 Single writer rule

Only the Position Engine may modify positions.

Positions must only be updated through:

```
PositionService.apply_trade()
```

---

## 4. Position Atom Concept

The smallest unit of a portfolio position is called a PositionAtom.

A PositionAtom represents:

```
Portfolio + Instrument
```

Example:

| Portfolio | Instrument | Quantity |
|-----------|------------|----------|
| P1        | BTC        | 0.75     |
| P1        | ETH        | 5        |
| P2        | BTC        | 0.3      |

A portfolio may have many PositionAtoms.

---

## 5. Table — pe_position_atoms

Proposed schema:

```
id UUID PK

portfolio_id UUID FK → pe_portfolios.id

instrument_id UUID FK → pe_instruments.id

quantity NUMERIC(30,10)

average_entry_price NUMERIC(30,10)

realized_pnl NUMERIC(30,10)

status VARCHAR(20)
    open
    closed

opened_at TIMESTAMPTZ
closed_at TIMESTAMPTZ

metadata JSONB

created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

---

## 6. Indexing

Required indexes:

- portfolio_id
- instrument_id
- status

Uniqueness constraint:

```
UNIQUE(portfolio_id, instrument_id, status='open')
```

Only one open position per instrument per portfolio.

---

## 7. Position Lifecycle

### Position creation

A position is created when the first BUY trade occurs.

Example:

```
BUY 0.5 BTC
```

Creates a PositionAtom.

### Position increase

Additional BUY trades increase quantity.

Example:

```
BUY 0.5 BTC
BUY 0.2 BTC
```

Result:

```
quantity = 0.7 BTC
```

Average price recalculated.

### Position reduction

SELL trades reduce quantity.

Example:

```
BUY 1 BTC
SELL 0.3 BTC
```

Result:

```
quantity = 0.7 BTC
```

Realized PnL calculated.

### Position closing

If quantity becomes zero:

```
status = closed
closed_at = timestamp
```

---

## 8. Average Price Calculation

Average entry price must be recalculated on BUY.

Formula:

```
new_avg =
(old_qty * old_avg + trade_qty * trade_price)
/
(old_qty + trade_qty)
```

---

## 9. Realized PnL

When SELL occurs:

```
realized_pnl =
trade_qty * (trade_price - avg_entry_price)
```

This amount is added to cumulative realized PnL.

---

## 10. Short Positions

Short positions are not supported in Phase 4.

If SELL quantity exceeds position quantity:

```
reject trade application
```

---

## 11. Cardinality

Relationships:

```
Portfolio → N PositionAtoms
PositionAtom → N Trades
```

Trades reference:
- portfolio_id
- instrument_id

---

## 12. PositionService

A new service must exist.

```
PositionService
```

Primary function:

```
apply_trade(trade)
```

Algorithm:

```
position = find_open_position(portfolio, instrument)

if position not exists:
    create position

if trade.side == BUY:
    increase position

if trade.side == SELL:
    decrease position
```

---

## 13. Integration in Transaction Flow

Position updates must occur after trade creation.

Final flow:

```
ExecutionService.process_fill()

→ TradeService.record_trade()

→ PositionService.apply_trade()

→ SettlementService.create_trade_settlements()
```

Settlement remains independent.

---

## 14. Trading Fees

Trading fees apply to every trade.

These fees represent revenue for Vancelian.

### Fee configuration

Trading fees must be configurable from the database.

A fee configuration model must exist.

Example table:

```
pe_trading_fee_configs

Fields:

id UUID PK

scope_type VARCHAR(30)
scope_id UUID

fee_rate NUMERIC(12,8)

status VARCHAR(20)

valid_from TIMESTAMPTZ
valid_to TIMESTAMPTZ

metadata JSONB

created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### Fee calculation

Trading fee is calculated as:

```
fee_amount = gross_trade_amount * fee_rate
```

Example:

```
BUY 0.5 BTC @ 68,000

gross = 34,000 EUR
fee_rate = 0.15%

fee = 51 EUR
```

### Fee accounting

Fees must be booked as company revenue.

Settlement example for BUY:

```
client EUR → R/L EUR : gross amount
client EUR → fee account : fee amount
treasury BTC → client BTC : quantity
```

The fee account represents Vancelian revenue.

---

## 15. Position Impact of Fees

Trading fees must not affect position quantity.

Example:

```
BUY 0.5 BTC

Position quantity remains:

0.5 BTC
```

Fees affect only cash balances.

---

## 16. Average Entry Price and Fees

In Phase 4:

Average entry price must exclude trading fees.

Fees remain accounted separately.

A fee-inclusive cost basis may be introduced in later phases.

---

## 17. Example Flows

### Example 1 — Simple Buy

```
BUY 0.5 BTC @ 68,000
fee = 51 EUR
```

Result:

```
position BTC = 0.5
avg price = 68,000
```

### Example 2 — Buy then Buy

```
BUY 0.5 BTC @ 68,000
BUY 0.3 BTC @ 70,000
```

New average price calculated.

### Example 3 — Partial Sell

```
BUY 1 BTC @ 50,000
SELL 0.3 BTC @ 60,000
```

Result:

```
quantity = 0.7 BTC
realized pnl = 0.3 * (60k - 50k)
```

### Example 4 — Full Close

```
BUY 1 BTC
SELL 1 BTC
```

Position closed.

---

## 18. Tests Required

The following tests must exist.

1. create position on first BUY
2. increase position on second BUY
3. partial SELL reduces quantity
4. full SELL closes position
5. SELL greater than quantity rejected
6. realized pnl calculated correctly
7. multiple trades update position correctly
8. trading fees calculated correctly
9. fees booked to revenue account
10. fees do not affect position quantity

---

End of PRD
