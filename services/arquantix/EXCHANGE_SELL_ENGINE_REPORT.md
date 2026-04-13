# Exchange Sell Engine v1 — Implementation Report

## Executive Summary

The Crypto -> EUR Sell Engine v1 has been successfully implemented as a symmetric mirror of the existing BUY engine. All 7 new SELL tests pass, and all 51 existing exchange + custody tests remain green (0 regressions).

The SELL flow follows the exact same architectural pattern as BUY:
- **Client Entitlement**: `crypto_positions.balance` is debited (virtual)
- **Settlement Obligation**: `crypto_settlement_deltas.delta_amount` receives a negative delta
- **Real Custody**: `crypto_custody_balances.actual_balance` is NEVER modified by trades

## Files Created

| File | Purpose |
|------|---------|
| `api/tests/test_exchange_sell.py` | 7 test cases covering SELL flow |
| `web/src/app/api/exchange/sell/route.ts` | Next.js API proxy for SELL endpoint |

## Files Modified

| File | Changes |
|------|---------|
| `api/services/exchange/repository.py` | Added `CryptoPositionRepository.debit()` with balance validation |
| `api/services/exchange/schemas.py` | Added `ExchangeSellRequest` and `ExchangeSellResponse` Pydantic models |
| `api/services/exchange/service.py` | Added `InsufficientCryptoBalanceError` exception + `ExchangeService.sell()` method (~160 lines) |
| `api/services/exchange/router.py` | Added `POST /api/exchange/sell` endpoint with error handling |
| `web/src/app/admin/exchange-test/page.tsx` | Added BUY/SELL tab toggle, SELL form, SELL preview (EUR-based), SELL result panel |

## New Endpoint

```
POST /api/exchange/sell
```

**Request:**
```json
{
  "client_id": "uuid",
  "asset": "BTC",
  "amount_crypto": "0.01",
  "currency": "EUR",
  "external_reference": "unique-ref",
  "price": 85000  // optional override
}
```

**Response:**
```json
{
  "status": "completed",
  "order_id": "uuid",
  "asset": "BTC",
  "from_asset": "BTC",
  "to_asset": "EUR",
  "amount_crypto": "0.01",
  "price_eur": "85000.00",
  "gross_eur": "850.00",
  "fee_eur": "8.50",
  "fee_bps": 100,
  "net_eur": "841.50",
  "client_eur_balance_after": "10841.50",
  "crypto_position_after": "0.10764705"
}
```

## Execution Flow (Atomic Transaction)

```
A. Idempotency check (external_reference)
B. Validate asset + precision
C. Resolve price (MarketData or override)
D. Compute: gross_eur, fee_eur (EUR!), net_eur
E. Lock crypto_position (SELECT FOR UPDATE) + validate balance
F. Lock EUR accounts (client + settlement)
G. Create exchange_order (side=sell, status=processing)
H. Atomic execution:
   H1. Custody transaction (EUR CREDIT to client)
   H2. Ledger double-entry (settlement DEBIT -> client CREDIT)
   H3. EUR balances: settlement -net_eur, client +net_eur
   H4. Debit crypto_position (virtual entitlement only)
   H5. Settlement delta: -amount_crypto (negative = must leave pool)
   H6. Finalize order -> completed
I. Audit log
```

## Key Architecture Differences: BUY vs SELL

| Aspect | BUY | SELL |
|--------|-----|------|
| Input | EUR amount | Crypto amount |
| Fee asset | Crypto | **EUR** |
| EUR movement | Client -> Settlement | **Settlement -> Client** |
| Crypto position | Credit (+) | **Debit (-)** |
| Settlement delta | Positive (+) | **Negative (-)** |
| Custody tx type | WITHDRAWAL (debit) | **DEPOSIT (credit)** |
| Transaction kind | EXCHANGE_BUY | **EXCHANGE_SELL** |

## Tests Added (7/7 passing)

| Test | Validates |
|------|-----------|
| `test_sell_success` | Full sell cycle: buy BTC, sell half, verify positions + EUR |
| `test_sell_insufficient_crypto` | Rejects sell when crypto balance insufficient |
| `test_sell_fee_calculation` | Fee in EUR: gross * bps / 10000, net = gross - fee |
| `test_sell_settlement_delta_created` | Negative delta created for the asset |
| `test_sell_unsupported_asset` | 400 error for unsupported assets |
| `test_sell_idempotency` | Duplicate external_reference returns "ignored" |
| `test_sell_insufficient_settlement_eur` | Full sell draining position to zero works |

## Edge Cases Handled

- **Precision validation**: Rejects amounts with more decimals than asset supports
- **Insufficient crypto**: Returns `{"status": "failed", "error": "insufficient_crypto_balance"}`
- **Insufficient settlement EUR**: Returns `{"status": "failed", "error": "insufficient_settlement_eur"}`
- **Duplicate reference**: Idempotent, returns existing order ID
- **Zero amount**: Rejected at schema level (`gt=0`)
- **Unsupported asset**: 400 with `unsupported_asset` detail
- **Transaction failure**: Order marked as "failed" with reason, exception re-raised for rollback

## Compatibility with BUY Engine

- BUY endpoint: **UNTOUCHED** (zero changes)
- BUY tests: **ALL PASSING** (51 tests + 1 skipped, 0 failures)
- Settlement engine: **UNTOUCHED** (already handles negative deltas)
- Crypto custody layer: **UNTOUCHED** (actual_balance never modified by SELL)
- Existing DB schema: **UNTOUCHED** (no migrations needed)

## Admin UI

The Exchange Test page now features:
- **BUY/SELL toggle** at the top of the page
- **Dynamic form**: EUR amount input for BUY, crypto amount input for SELL
- **Preview card**: Blue for BUY (crypto preview), orange for SELL (EUR preview with gross/fee/net)
- **Max button**: Uses EUR balance for BUY, crypto position for SELL
- **Result panel**: Adapts fields to show BUY-specific or SELL-specific data

## Final Status

**COMPLETED** — All requirements from the PRD have been implemented and verified.
