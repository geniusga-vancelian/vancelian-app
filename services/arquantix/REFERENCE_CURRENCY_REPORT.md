# Reference Currency Implementation Report

## 1. Executive Summary

- **Preference created**: YES — `reference_currency` field added to `pe_clients` (EUR/USD)
- **Backend wired**: YES — bootstrap enriched, PATCH endpoint created, positions/wallet enriched with dual-currency values
- **Flutter wired**: YES — `CurrencyPreference` singleton loaded from bootstrap, profile selector, all key screens adapted
- **Confidence level**: HIGH — 77 backend tests passing (12 for test_clients including 4 new reference_currency tests), zero regressions, Flutter compiles clean

## 2. Backend files modified

| File | Role |
|------|------|
| `api/alembic/versions/064_add_reference_currency_to_pe_clients.py` | Migration: adds `reference_currency VARCHAR(3) NOT NULL DEFAULT 'EUR'` to `pe_clients` |
| `api/services/portfolio_engine/clients/enums.py` | New `ReferenceCurrency` enum (EUR, USD) |
| `api/services/portfolio_engine/clients/models.py` | Added `reference_currency` column to `Client` model |
| `api/services/portfolio_engine/clients/schemas.py` | Added `reference_currency` to `ClientCreate`, `ClientUpdate`, `ClientRead` |
| `api/services/test_clients/schemas.py` | Added `reference_currency` to `BootstrapClientPayload`; added `price_usd`, `estimated_value_usd`, `total_value_usd` to crypto schemas |
| `api/services/test_clients/router.py` | New `PATCH /api/app/profile/reference-currency` endpoint |
| `api/services/test_clients/service.py` | `get_crypto_positions()` and `get_crypto_wallet_detail()` now return dual EUR/USD values |
| `api/tests/test_test_clients.py` | 4 new tests: default EUR, update to USD, update to EUR, invalid currency rejected |

## 3. Flutter files modified

| File | Role |
|------|------|
| `mobile/lib/core/config.dart` | Added `bootstrapUrl` and `referenceCurrencyUrl` |
| `mobile/lib/core/currency_preference.dart` | **NEW** — `ReferenceCurrency` enum + `CurrencyPreference` singleton (load from bootstrap, PATCH update, selectValue/selectString helpers) |
| `mobile/lib/features/profile/presentation/screens/profile_screen.dart` | Converted to StatefulWidget; added EUR/USD segmented selector |
| `mobile/lib/features/wallet/domain/models/crypto_positions_data.dart` | Added `totalValueUsd`, `priceUsd`, `estimatedValueUsd` fields |
| `mobile/lib/features/wallet/domain/models/crypto_wallet_detail.dart` | Added `currentPriceUsd`, `totalValueUsd` fields |
| `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` | Adapted to use `_activeFormatter` and `CurrencyPreference.selectValue` |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Adapted total value, gains, purchase price to use active currency |
| `mobile/lib/features/markets/data/all_crypto_api.dart` | `AllCryptoItem` stores `priceEur`/`priceUsd`; `formatPrice()` accepts currency parameter |
| `mobile/lib/features/markets/data/market_data_ws_service.dart` | `QuoteUpdate` now carries `priceEur` from WS broadcast |
| `mobile/lib/features/markets/presentation/screens/all_crypto_screen.dart` | WS quote handler selects display price by preference |
| `mobile/lib/features/markets/presentation/screens/crypto_detail_screen.dart` | Live price uses `selectValue` for correct currency |
| `mobile/lib/features/markets/presentation/widgets/chart_asset_module.dart` | Replaced hardcoded `€` with dynamic `_currencySymbol` |
| `mobile/lib/features/home/presentation/screens/home_screen.dart` | Bootstrap loads preference; crypto wallet card uses active formatter |

### Next.js proxy

| File | Role |
|------|------|
| `web/src/app/api/mobile/flutter/profile/reference-currency/route.ts` | **NEW** — PATCH proxy to backend |

## 4. Persistence model

- **Where**: `pe_clients.reference_currency` (VARCHAR(3), NOT NULL, DEFAULT 'EUR')
- **Default value**: `EUR`
- **Validation**: Backend enum `ReferenceCurrency` (EUR, USD only). Any other value returns HTTP 422.
- **Migration**: `064_add_reference_currency_to_pe_clients.py` — backward compatible (server_default ensures existing rows get EUR)

## 5. API changes

### Bootstrap enriched
`GET /api/app/bootstrap` now returns:
```json
{
  "client": {
    "id": "...",
    "email": "...",
    "status": "active",
    "kyc_status": "approved",
    "reference_currency": "EUR"
  }
}
```

### Update endpoint
`PATCH /api/app/profile/reference-currency`
```json
// Request
{ "reference_currency": "USD" }

// Response (200)
{ "reference_currency": "USD" }

// Invalid (422)
{ "reference_currency": "GBP" }
```

### Payloads enriched with EUR / USD

**Crypto positions** (`GET /api/app/crypto-positions`):
```json
{
  "summary": {
    "total_value_eur": "1234.56",
    "total_value_usd": "1345.67",
    "positions_count": 2
  },
  "positions": [
    {
      "asset": "BTC",
      "price_eur": "63000.00",
      "estimated_value_eur": "630.00",
      "price_usd": "72000.00",
      "estimated_value_usd": "720.00",
      ...
    }
  ]
}
```

**Crypto wallet detail** (`GET /api/app/crypto-positions/{asset}`):
```json
{
  "detail": {
    "current_price_eur": "63000.00",
    "current_price_usd": "72000.00",
    "total_value_eur": "630.00",
    "total_value_usd": "720.00",
    ...
  }
}
```

**Market data** (`all-crypto`, `market-summary`): already return `price` (USDT≈USD) and `price_eur`. No change needed.

**WebSocket broadcast**: already sends `price_eur` alongside `price` (USDT). Flutter now reads both.

## 6. Flutter integration

### Profile page
- EUR/USD segmented control with animated selection
- PATCH call on change → local state update → screens refresh on next load
- Loading indicator during update

### State
- `CurrencyPreference` singleton (`ChangeNotifier`)
- Loaded from bootstrap on app start (HomeScreen._loadBootstrap)
- `selectValue(eur:, usd:)` and `selectString(eur:, usd:)` helpers for clean field selection

### Screens impacted

| Screen | Adaptation |
|--------|-----------|
| **HomeScreen** (Dashboard) | Crypto wallet card displays total in active currency; `_activeFormatter` switches between EUR/USD |
| **AllCryptoPositionsScreen** | Total value and per-position values use active currency |
| **CryptoWalletDetailScreen** | Total value, gains, purchase price use active formatter |
| **AllCryptoScreen** (Markets) | Prices formatted with active currency symbol; WS updates select correct price |
| **CryptoDetailScreen** | Live price from WS uses `selectValue` |
| **ChartAssetModule** | Currency symbol in chart labels dynamic |

## 7. Fallback behavior

- If `price_usd` is unavailable but `price_eur` is available (or vice versa), `CurrencyPreference.selectValue` falls back to the available value.
- If both are null, displays `—`.
- If the bootstrap call fails, default remains EUR.
- If the PATCH update fails, the local state is not changed (no optimistic update).
- USDT prices are displayed as "USD" in the UX — USDT never appears in the client-facing UI.

**Documented approximation (v1)**: `price_usd` = USDT price from Binance. USDT ≈ USD (typically within 0.1%). For v1 this is acceptable. A future enhancement could introduce a true USD/USDT rate if needed.

## 8. Final status

**Can the app now let the user choose EUR or USD as reference currency and display values accordingly?**

**YES** — with the following coverage:
- Profile page allows EUR/USD selection (persisted to backend)
- Dashboard crypto card, All Crypto Positions, Crypto Wallet Detail, Markets list, Asset Detail, and Chart display all use the active currency
- WebSocket live updates respect the preference
- Backend returns both EUR and USD values for all crypto valuation endpoints
- 77 backend tests pass including 4 new reference currency tests
- Backward compatible: existing clients default to EUR, no existing endpoints broken
