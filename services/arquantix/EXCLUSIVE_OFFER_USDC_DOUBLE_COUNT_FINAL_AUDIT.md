# Exclusive Offer — USDC Double Count Final Audit

## Executive Summary

After investing EUR into an Exclusive Offer (lending product), the USDC amount appeared
in **both** Placements and the Crypto wallet, causing double counting.

**Root cause**: `ExchangeService.buy()` writes to TWO systems:
1. `crypto_positions` (balance + available_balance)
2. `pe_position_atoms` in the "Direct Holdings" portfolio

The Phase 2A.16 Envelope debit only neutralized `crypto_positions.balance` but
**never touched the PE position atom**. The `/crypto-positions/direct` endpoint
reads from PE atoms, so the phantom USDC remained visible in the Crypto screen.

**Fix**: The orchestrator now debits BOTH `crypto_positions.balance` AND the PE
direct portfolio atom after a conversion-based invest. The PE atom quantity is
reduced by the supplied amount, keeping the dual tracking system in sync.

---

## Real Invest Flow Used By UI

```
Flutter "Investir" button
  → LendingInvestProcessingSheet.executeInvest()
  → POST /api/mobile/flutter/lending/products/{id}/invest
  → BFF proxy: web/.../lending/products/[productId]/invest/route.ts
  → Backend: /api/app/lending/products/{id}/invest (bootstrap_router)
  → LendingInvestOrchestrator.invest_into_product()
```

The orchestrator calls:
1. `ExchangeService.buy()` → credits crypto_positions + creates PE atom
2. `OfferService.subscribe()` → reduces available_balance
3. Envelope debit → reduces crypto_positions.balance (FIXED: now also PE atom)
4. Creates InvestmentEnvelope + InvestmentEnvelopeEntry

---

## Write Path Audit

### A. buy() intermediate credit

| System | Field | Effect |
|--------|-------|--------|
| `crypto_positions` | `balance` | +X |
| `crypto_positions` | `available_balance` | +X |
| `pe_position_atoms` | `quantity` | +X |
| `pe_position_atoms` | `available_quantity` | +X |

Created via:
- `CryptoPositionRepository.credit()` → crypto_positions
- `sync_direct_atom()` → pe_position_atoms

### B. subscribe() → create_supply_commitment()

| System | Field | Effect |
|--------|-------|--------|
| `crypto_positions` | `available_balance` | -X |

### C. Envelope debit (BEFORE fix)

| System | Field | Effect |
|--------|-------|--------|
| `crypto_positions` | `balance` | -X |
| `pe_position_atoms` | `quantity` | ❌ NOT TOUCHED |

### C. Envelope debit (AFTER fix)

| System | Field | Effect |
|--------|-------|--------|
| `crypto_positions` | `balance` | -X |
| `pe_position_atoms` | `quantity` | -X ✅ |
| `pe_position_atoms` | `cost_basis` | proportional reduction ✅ |

### D. Net result after fix (EUR conversion invest, starting from 0)

| System | Field | Before | After |
|--------|-------|--------|-------|
| `crypto_positions` | `balance` | 0 | 0 |
| `crypto_positions` | `available_balance` | 0 | 0 |
| `pe_position_atoms` | `quantity` | 0 | 0 |
| `pool_supply_commitments` | `amount` | - | X |
| `investment_envelopes` | - | - | created |

---

## Read Path Audit

### Crypto Screen (AllCryptoPositionsScreen)

```
Flutter: _api.fetchDirectPositions() → fallback fetchPositions()
URL: GET /api/mobile/flutter/crypto-positions/direct
Backend: get_direct_crypto_positions() in router.py

Source: pe_position_atoms (Direct Holdings portfolio)
Adjustment: display_qty = atom.quantity - lending_reserved
lending_reserved = crypto_positions.balance - crypto_positions.available_balance
```

**Before fix**: `lending_reserved = 0 - 0 = 0` → `display_qty = 3464 - 0 = 3464` ❌
**After fix**: PE atom qty = 0 → position skipped (qty ≤ 0) ✅

### Dashboard

```
URL: GET /api/mobile/flutter/crypto-positions
Backend: get_crypto_positions() in service.py

Source: crypto_positions directly
Uses: display_balance = available_balance (if ≥ 0)
```

Dashboard was already correct (uses available_balance).

### Placements Screen

```
URL: GET /api/mobile/flutter/lending/earn/positions
Backend: get_earn_positions() in product_surface.py

Source: pool_supply_commitments + lending positions
```

Placements was already correct (reads from commitments, not crypto).

### Comparison Table

| Surface | Endpoint | Source | Field | Before fix | After fix |
|---------|----------|--------|-------|------------|-----------|
| Dashboard | /crypto-positions | crypto_positions | available_balance | 0 ✅ | 0 ✅ |
| Crypto screen | /crypto-positions/direct | pe_position_atoms | quantity - reserved | 3464 ❌ | 0 ✅ |
| Placements | /lending/earn/positions | pool_supply_commitments | amount | correct ✅ | correct ✅ |

---

## Database Verification

### After invest 500 EUR → USDC (from 0 balance)

```sql
-- crypto_positions
USDC: balance=0, available_balance=0  ✅

-- pe_position_atoms (Direct Holdings)
USDC: quantity=0  ✅ (was 577 before fix!)

-- pool_supply_commitments
577.39 USDC, status=active  ✅

-- investment_envelopes
type=exclusive_offer, status=active  ✅

-- investment_envelope_entries
EUR 500 → USDC 577.39, conversion_type=buy  ✅
```

### After invest 300 EUR → USDC (from 200 USDC pre-existing)

```sql
-- crypto_positions
USDC: balance=200, available_balance=200  ✅ (original preserved)

-- pe_position_atoms (Direct Holdings)
USDC: quantity=200  ✅ (only free USDC visible)
```

---

## Root Cause

**H1** ❌ Crypto screen does NOT read balance instead of available_balance (fixed in 2A.15)
**H2** ❌ The flow DOES use the correct orchestrator
**H3** ❌ Envelope debit IS executed
**H4** ❌ Envelope debit IS on the correct line/asset
**H5** ❌ No legacy endpoint bypass

**H6** ✅ **Dual source of truth**: `ExchangeService.buy()` writes to BOTH
`crypto_positions` AND `pe_position_atoms`. The envelope debit only neutralized
`crypto_positions` but NOT the PE atom. The `/crypto-positions/direct` endpoint
reads PE atoms and showed phantom USDC.

---

## Fix Applied

**File**: `api/services/lending/invest_orchestrator.py`

In `invest_into_product()`, Step 4 (envelope debit), added PE atom debit:

```python
# After crypto_positions.balance debit:
from services.portfolio_engine.direct_overlay import (
    ensure_direct_portfolio,
    sync_direct_atom,
    _resolve_or_create_instrument as _resolve_pe_instrument,
)
direct_pf = ensure_direct_portfolio(db, client_id)
pe_instr = _resolve_pe_instrument(db, pool_asset)

# Calculate proportional cost_basis to remove
existing_atom = db.query(PositionAtom).filter(...).first()
cost_delta = 0
if existing_atom and existing_atom.quantity > 0:
    ratio = supply_amount / existing_atom.quantity
    cost_delta = existing_atom.cost_basis * ratio

sync_direct_atom(db, direct_pf.id, pe_instr.id, -supply_amount, -cost_delta)
```

This ensures both tracking systems stay in sync after conversion-based investments.

---

## Tests

All 63 existing envelope hardening tests pass after the fix:

```
tests/test_envelope_accounting_invariants.py     13 passed
tests/test_envelope_zero_wallet_pollution.py      7 passed
tests/test_envelope_data_integrity.py            12 passed
tests/test_envelope_failure_rollback.py           8 passed
tests/test_envelope_concurrency.py                8 passed
tests/test_envelope_cross_surface_consistency.py  6 passed
tests/test_envelope_backward_compatibility.py     7 passed
tests/test_envelope_precision_rounding.py         6 passed
tests/test_reset_financial_test_state.py          3 passed + 1 skipped
```

### Real-world validation

| Scenario | crypto_positions | PE atom | Commitment | Double count? |
|----------|-----------------|---------|------------|---------------|
| 500 EUR → USDC (from 0) | balance=0, avail=0 | qty=0 | 577 USDC | ❌ No |
| 300 EUR → USDC (from 200 existing) | balance=200, avail=200 | qty=200 | 346 USDC | ❌ No |

---

## Final Verification

| Invariant | Status |
|-----------|--------|
| Crypto screen shows 0 USDC after full conversion invest | ✅ |
| Crypto screen preserves pre-existing free USDC | ✅ |
| Placements shows correct commitment value | ✅ |
| Dashboard uses available_balance | ✅ |
| No double counting Crypto + Placements | ✅ |
| Envelope entry created correctly | ✅ |
| commitment_id linked to envelope | ✅ |
| ExchangeService unchanged | ✅ |
| PoolService unchanged | ✅ |
| LendingService unchanged | ✅ |
| 63 existing tests pass | ✅ |
