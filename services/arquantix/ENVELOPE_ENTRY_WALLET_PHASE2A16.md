# Phase 2A.16 — Envelope Entry Wallet Abstraction

## Executive Summary

Investment flows now encapsulate conversion, fees, and allocation inside an **Investment Envelope** instead of polluting the user's crypto wallet with intermediate balances.

**Before (Phase 2A.14):**
```
EUR → ExchangeService.buy() → credit USDC wallet → supply pool
                                    ↑
                          USDC visible in Crypto section (pollution)
```

**After (Phase 2A.16):**
```
EUR → ExchangeService.buy() → credit USDC wallet → supply pool → debit USDC wallet
                                                                       ↑
                                              Intermediate balance neutralized (zero pollution)
                              + envelope entry created for clean tracking
```

---

## Architecture

### New Tables

#### `investment_envelopes`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Envelope identifier |
| `client_id` | UUID | Client who invested |
| `type` | VARCHAR(50) | `exclusive_offer` / `bundle` / `portfolio` |
| `reference_id` | VARCHAR(255) | `project_id` or `bundle_id` |
| `status` | VARCHAR(30) | `active` / `closed` |
| `metadata_` | JSONB | Additional context (product_id, pool_id) |
| `created_at` | TIMESTAMP | Creation time |

#### `investment_envelope_entries`
| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Entry identifier |
| `envelope_id` | UUID FK | Parent envelope |
| `commitment_id` | UUID | Linked pool supply commitment |
| `entry_asset` | VARCHAR(20) | Source asset (EUR, BTC, …) |
| `entry_amount` | NUMERIC(30,10) | Amount in source asset |
| `target_asset` | VARCHAR(20) | Pool asset (USDC) |
| `converted_amount` | NUMERIC(30,10) | Gross converted amount |
| `fx_rate` | NUMERIC(20,10) | Exchange rate used |
| `conversion_type` | VARCHAR(20) | `none` / `buy` / `swap` |
| `conversion_fee` | NUMERIC(30,10) | Fee charged for conversion |
| `platform_fee` | NUMERIC(30,10) | Platform fee |
| `net_allocated` | NUMERIC(30,10) | Amount actually supplied to pool |
| `external_reference` | VARCHAR(255) | Exchange order reference |
| `conversion_details` | JSONB | Raw conversion details |
| `created_at` | TIMESTAMP | Creation time |

### Modified Flow in `invest_orchestrator.py`

```
invest_into_product():
  1. Load & validate product
  2. Convert funding asset → pool asset (ExchangeService.buy/swap)
     → credits crypto_positions (accounting requirement)
  3. Supply to lending pool (OfferService.subscribe)
     → reduces available_balance
  4. [NEW] Debit crypto_positions.balance by supply_amount
     → neutralizes intermediate credit (ZERO wallet pollution)
  5. [NEW] Create InvestmentEnvelope + InvestmentEnvelopeEntry
     → clean tracking of full investment lifecycle
  6. Return result with envelope_id
```

### Key Invariant: Envelope Debit

```python
# Only when conversion happened (buy/swap)
if conversion_type != "none":
    pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, pool_asset)
    pos.balance = Decimal(str(pos.balance)) - supply_amount
    db.flush()
```

**Why only for conversions?** Direct USDC invest (conversion_type=none) uses existing wallet funds — the balance was already there and should remain tracked normally.

---

## Before / After Verification

### Test: 500 EUR → USDC Exclusive Offer

| Metric | Before | After |
|--------|--------|-------|
| USDC balance | 1155.07 | 1155.07 (unchanged!) |
| USDC available | 0 | 0 |
| Envelope entries | 0 | 1 |
| Earn positions | USDC 1155 supplied | USDC 1732 supplied |

**Balance unchanged** because:
- `buy()` credited +577 USDC to balance
- Envelope debit subtracted -577 USDC from balance
- Net change = **0** (zero pollution)

### Envelope Entry Created

```
envelope: type=exclusive_offer, ref=cmn1il8li0001ugmrz0rkgu4n, status=active
  entry: EUR 500.00 → USDC 577.44
    conversion=buy, fee=0.00, net_allocated=577.44
    commitment_id=00fba36c-fabb-48b2-b7b2-a99c431966bf
```

---

## Earn Positions Enrichment

`GET /api/lending/earn/positions` now includes envelope data:

```json
{
  "asset": "USDC",
  "total_supplied": 1732.51,
  "value_eur": 1500.16,
  "envelope": {
    "entry_asset": "EUR",
    "entry_amount": 500.0,
    "converted_amount": 577.44,
    "conversion_type": "buy",
    "conversion_fee": 0.0,
    "net_allocated": 577.44
  }
}
```

---

## Source of Truth

| Section | Source | Field |
|---------|--------|-------|
| **Crypto** | `crypto_positions` | `available_balance` (free funds only) |
| **Placements** | `pool_supply_commitments` + `envelope` | `net_allocated + accrued_interest` |
| **Total Wealth** | Sum of both | No double counting |

### P&L Calculation
```
P&L = current_value_eur - entry_amount (EUR)
```
Base EUR via envelope `entry_amount` — no ambiguity.

---

## Files Modified

| File | Change |
|------|--------|
| `api/alembic/versions/078_add_investment_envelopes.py` | **NEW** — Migration |
| `api/services/lending/envelope_models.py` | **NEW** — SQLAlchemy models |
| `api/services/lending/invest_orchestrator.py` | Steps 4-5 added (debit + envelope) |
| `api/services/lending/product_surface.py` | Envelope data in earn positions |

---

## Non-Regression

| Invariant | Status |
|-----------|--------|
| ExchangeService untouched | ✅ |
| PoolService untouched | ✅ |
| LendingService untouched | ✅ |
| crypto_positions schema untouched | ✅ |
| Ledger core untouched | ✅ |
| Exchange orders still created (audit trail) | ✅ |
| Existing investments unaffected (safe mode) | ✅ |
| Python imports OK | ✅ |

---

## Safe Mode Strategy

- **New investments**: Use envelope pattern (debit balance + create envelope)
- **Old investments**: Unchanged — already handled by `available_balance` UI fix
- **Migration path**: Retroactive envelopes can be created later if needed

---

## Conversion Scenarios

| Scenario | Conversion | Wallet Impact | Envelope |
|----------|------------|---------------|----------|
| EUR → USDC pool | buy | balance neutralized | ✅ entry_asset=EUR |
| BTC → USDC pool | swap | balance neutralized | ✅ entry_asset=BTC |
| USDC → USDC pool | none | available_balance reduced | ✅ entry_asset=USDC |
