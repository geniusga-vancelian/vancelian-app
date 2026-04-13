# SELL_ALL_CRYPTO_FLOW_REPORT

## Executive Summary

Implemented a "Sell all my crypto" feature allowing clients to liquidate 100% of all crypto positions in a single controlled flow. The implementation reuses the existing SELL engine for each asset (WAC, realized P&L, ledger, audit) and executes sequentially with best-effort partial failure tolerance.

**Scope**: Backend service + endpoints, Next.js proxy, Flutter 3-step flow, 8 automated tests.

## Backend Preview

### Endpoint: `POST /api/app/exchange/sell-all/preview`

**Service method**: `ExchangeService.preview_sell_all(db, client_id)`

Behavior:
1. Loads all `CryptoPosition` rows for the client via `list_by_client`
2. Filters positions with `balance > 0`
3. Calls `preview_sell()` for each asset (same pricing logic as individual SELL)
4. If quote is stale/unavailable for an asset, marks it as `"status": "unavailable"` with error details — does NOT mask the asset
5. Sums estimated net EUR across all ready assets

Response structure:
```json
{
  "total_assets": 5,
  "estimated_total_eur": 8974.98,
  "items": [
    { "asset": "BTC", "amount_available": "0.05", "estimated_eur_net": 3169.40, "status": "ready" },
    { "asset": "SOL", "amount_available": "44.12", "estimated_eur_net": 3385.57, "status": "ready" },
    { "asset": "ADA", "amount_available": "427.19", "status": "unavailable", "error_code": "MarketQuoteStaleError" }
  ]
}
```

## Backend Execution

### Endpoint: `POST /api/app/exchange/sell-all`

**Service method**: `ExchangeService.sell_all(db, client_id, actor)`

Behavior:
1. Loads all positions with `balance > 0`
2. Generates a unique `batch_id` (UUID) for the entire operation
3. For each asset, sequentially:
   - Quantizes balance to asset precision
   - Calls `preview_sell()` to estimate (for reporting)
   - Builds an `ExchangeSellRequest` with `external_reference = sell-all-{batch_id}-{asset}`
   - Calls the real `sell()` method — full accounting pipeline (WAC, realized P&L, ledger, custody, audit)
4. Catches `ExchangeError` per-asset — failed assets do NOT abort the batch
5. Logs an audit event for the entire batch

**Idempotency**: Each asset's sell uses `sell-all-{batch_id}-{asset}` as external reference. A second call to sell-all will find 0 active positions (all balances are 0 after first call).

## Partial Failure Strategy

**Strategy: Sequential best-effort**

- Each asset is sold independently
- If asset N fails (stale quote, insufficient settlement, etc.), assets N+1..M still execute
- The batch result clearly reports per-asset status (`completed` / `failed`)
- Failed assets include `error_code` and `error_message`
- No rollback of previously successful sells
- Audit trail captures the full batch outcome

## Flutter Flow

### Entry Point
"Tout vendre" button added to `AllCryptoPositionsScreen` hero action bar (replaces "Dépenser" placeholder).

### STEP 1 — Confirmation (`SellAllConfirmationScreen`)
- Loads preview on screen open
- Displays:
  - Total estimated EUR (large prominent card)
  - List of positions to sell with amounts and estimated EUR
  - Unavailable positions clearly marked
  - Warning banner about price volatility
- Bottom bar with "Annuler" and "Confirmer la vente" (red button)
- If no positions or preview fails: error state with close button

### STEP 2 — Processing (`SellAllProcessingSheet`)
- Modal bottom sheet, non-dismissible during execution
- Shows spinner + "Liquidation en cours..." message
- Calls `exchangeApi.executeSellAll()`

### STEP 3 — Result (same sheet, state change)
- **Success**: Green checkmark, total received, assets sold/failed count, per-asset detail list
- **Partial failure**: Orange warning, same detail with failed assets in red
- **Error**: Red cross, error message, close button

### UX Safeguards
- Button disabled while executing (prevents double submit)
- Modal is non-dismissible during processing
- Button not accessible if no positions > 0
- Preview loaded fresh before each confirmation

## Tests Added

File: `api/tests/test_sell_all.py` — **8 tests, all passing**

| # | Test | Description |
|---|------|-------------|
| 1 | `test_sell_all_preview_multiple_assets` | Preview with 3 assets returns correct structure |
| 2 | `test_sell_all_executes_all` | Sells all held assets, 0 failures |
| 3 | `test_sell_all_ignores_zero_balance` | Only non-zero positions are processed |
| 4 | `test_sell_all_realized_pnl_coherent` | Each result includes realized P&L |
| 5 | `test_sell_all_eur_balance_increases` | EUR balance increases by exact total net |
| 6 | `test_sell_all_partial_failure_stale_quote` | Stale quote on ADA → partial failure reported |
| 7 | `test_sell_all_no_double_submit` | Second call finds 0 positions, sells nothing |
| 8 | `test_sell_all_invariants_hold` | Invariants A (NAV) and B (P&L) hold after full liquidation |

## Final Status

| Component | Status |
|-----------|--------|
| Backend `preview_sell_all` | DONE |
| Backend `sell_all` | DONE |
| Router endpoints | DONE |
| Next.js proxy routes | DONE |
| Flutter Config URLs | DONE |
| Flutter API client (models + methods) | DONE |
| Flutter confirmation screen | DONE |
| Flutter processing/result sheet | DONE |
| Button in AllCryptoPositionsScreen | DONE |
| Tests (8/8 passing) | DONE |
| Non-regression (swap, staleness) | PASS |
| Existing SELL/BUY/SWAP | NOT BROKEN |

### Files Modified
- `api/services/exchange/service.py` — Added `preview_sell_all()` and `sell_all()` methods
- `api/services/test_clients/router.py` — Added 2 endpoints
- `mobile/lib/core/config.dart` — Added 2 URLs
- `mobile/lib/features/wallet/data/exchange_api.dart` — Added models + extension methods
- `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` — Added button + navigation

### Files Created
- `api/tests/test_sell_all.py`
- `web/src/app/api/mobile/flutter/exchange/sell-all/preview/route.ts`
- `web/src/app/api/mobile/flutter/exchange/sell-all/route.ts`
- `mobile/lib/features/wallet/presentation/screens/sell_all_flow/sell_all_confirmation_screen.dart`
- `mobile/lib/features/wallet/presentation/screens/sell_all_flow/sell_all_processing_sheet.dart`
