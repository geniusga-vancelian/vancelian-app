# Bundles Feature Documentation

## Overview

Bundles are named allocation models with fixed weights (sum = 100%) scoped to a single Asset Class. They allow users to define reusable portfolio allocations and use them in backtests.

## Database Schema

### Tables

1. **`bundles`**
   - `id` (Integer, PK)
   - `name` (String, unique per asset_class)
   - `asset_class` (String: "crypto", "etf", "equity", "commodities", "index")
   - `type` (String, default: "FIXED_WEIGHT") - Future-proof for dynamic weights
   - `description` (Text, nullable)
   - `is_active` (String: "true"/"false")
   - `created_at`, `updated_at` (DateTime)
   - `created_by_email` (String, nullable)

2. **`bundle_allocations`**
   - `id` (Integer, PK)
   - `bundle_id` (FK -> bundles.id, CASCADE delete)
   - `instrument_id` (FK -> market_data_instruments.id, CASCADE delete)
   - `weight` (Numeric(10,4)) - Percentage (0-100)
   - `position_order` (Integer, nullable)
   - Unique constraint: (bundle_id, instrument_id)

### Migration

```bash
cd api
alembic upgrade head
```

Migration file: `api/alembic/versions/g2345678901b_add_bundles_tables.py`

## Backend API

### Endpoints

- `GET /api/bundles?asset_class=CRYPTO&active=true` - List bundles
- `GET /api/bundles/{bundle_id}` - Get bundle detail with allocations
- `POST /api/bundles` - Create bundle
- `PUT /api/bundles/{bundle_id}` - Update bundle
- `DELETE /api/bundles/{bundle_id}` - Soft delete (set is_active=false)
- `GET /api/bundles/asset-classes/{asset_class}/instruments` - Get instruments for asset class

### Validation Rules

1. **Weights must sum to 100%** (tolerance: 0.01 for rounding)
2. **No duplicate instrument codes** in allocations
3. **Instruments must exist** and be active
4. **Instruments must belong to same asset_class** as bundle
5. **Bundle name must be unique** per asset_class

### Backtest Integration

When `bundle_id` is provided in `BacktestCreateRequest`:
- Bundle allocations override `instrument_ids` and `initial_weights`
- Weights are converted from percentage (0-100) to fraction (0-1)
- Validation ensures bundle exists and is active

## Frontend Admin UI

### Pages

1. **`/admin/bundles`** - List all bundles with filtering
2. **`/admin/bundles/new`** - Create new bundle
3. **`/admin/bundles/[id]`** - Edit existing bundle

### Features

- Asset class selection
- Instrument picker (filtered by asset class, provider=yahoo, has_bars=true)
- Weight input with live total calculation
- "Normalize" button to rescale weights to 100%
- Validation prevents save if sum != 100%
- Bundle allocations displayed in read-only table

## Backtest Builder Integration

### Flow

1. User selects **Asset Class** (required)
2. User optionally selects **Bundle**
   - If bundle selected:
     - Instruments list is locked to bundle instruments
     - Allocations displayed in read-only table
     - Manual instrument selection disabled
   - If no bundle:
     - Manual instrument selection enabled (filtered by asset class)
3. Backtest payload includes `bundle_id` if bundle selected

### UI Changes

- Added Asset Class dropdown
- Added Bundle dropdown (optional)
- Bundle allocations display (read-only)
- Instrument checkboxes disabled when bundle selected

## Testing

### Manual Test Steps

1. **Create Bundle:**
   ```
   - Go to /admin/bundles/new
   - Select Asset Class: "crypto"
   - Name: "Crypto Equal Weight"
   - Add allocations: BTCUSD (33.33%), ETHUSD (33.33%), SOLUSD (33.34%)
   - Verify total = 100%
   - Save
   ```

2. **Use Bundle in Backtest:**
   ```
   - Go to /admin/backtests
   - Select Asset Class: "crypto"
   - Select Bundle: "Crypto Equal Weight"
   - Verify instruments are auto-selected
   - Verify allocations displayed
   - Run backtest
   ```

3. **Validation Tests:**
   - Try to save bundle with weights != 100% → Should fail
   - Try to add duplicate instrument → Should fail
   - Try to add instrument from different asset class → Should fail

## Files Changed

### Backend
- `api/database.py` - Added Bundle, BundleAllocation models
- `api/alembic/versions/g2345678901b_add_bundles_tables.py` - Migration
- `api/services/bundles/` - New module
  - `__init__.py`
  - `schemas.py` - Pydantic models
  - `routes.py` - FastAPI endpoints
- `api/main.py` - Include bundles router
- `api/services/backtest/schemas.py` - Added bundle_id to BacktestCreateRequest
- `api/services/backtest/routes.py` - Bundle resolution logic

### Frontend
- `web/src/app/admin/layout.tsx` - Added "Bundles" link
- `web/src/app/admin/bundles/page.tsx` - Bundle list page
- `web/src/app/admin/bundles/new/page.tsx` - Create bundle page
- `web/src/app/admin/bundles/[id]/page.tsx` - Edit bundle page
- `web/src/app/api/bundles/route.ts` - Proxy routes (GET, POST)
- `web/src/app/api/bundles/[id]/route.ts` - Proxy routes (GET, PUT, DELETE)
- `web/src/app/api/bundles/asset-classes/[asset_class]/instruments/route.ts` - Instruments endpoint
- `web/src/components/backtests/BacktestBuilder.tsx` - Bundle integration
- `web/src/components/backtests/types.ts` - Added bundle_id to BacktestCreateRequest

## Future Enhancements

The `type` field in bundles is designed to support future dynamic weight strategies:
- `RULE_BASED` - Rules-based allocation
- `MOMENTUM` - Momentum-based allocation
- `VOL_TARGET` - Volatility targeting

Current implementation only supports `FIXED_WEIGHT`.

