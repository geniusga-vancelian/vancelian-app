# Root Cause Analysis and Fix

## Date: 2024-12-XX

## Summary

Fixed two critical runtime errors in Arquantix CMS:
1. **500 error on GET `/api/bundles/asset-classes/{asset_class}/instruments`** - Missing error handling in backend route
2. **"Invalid request data" on POST `/api/backtests/run` with bundle** - Schema validation requiring `instrument_ids` even when `bundle_id` is provided

---

## Issue 1: 500 Error on Bundle Instruments Endpoint

### Root Cause

The backend route `GET /api/bundles/asset-classes/{asset_class}/instruments` in `api/services/bundles/routes.py` lacked proper error handling. When the database query for `MarketDataBarD1` failed (e.g., table missing, connection issue), the exception was not caught, resulting in a 500 Internal Server Error.

Additionally, the Next.js proxy route did not log backend errors, making debugging difficult.

### Files Changed

1. **`api/services/bundles/routes.py`**:
   - Added try/except block around database queries
   - Added logging for errors
   - Improved error messages with context

2. **`web/src/app/api/bundles/asset-classes/[asset_class]/instruments/route.ts`**:
   - Added error logging (first 500 chars of error response)
   - Improved error handling for connection errors
   - Better error messages forwarded to frontend

3. **`web/src/app/admin/bundles/new/page.tsx`**:
   - Improved error handling in `loadInstruments()`
   - Better error messages displayed to user

### Key Changes

```python
# Backend: Added error handling
try:
    instrument_ids_with_bars = set(
        row[0] for row in db.query(MarketDataBarD1.instrument_id)
        .distinct()
        .all()
    )
except Exception as e:
    logging.warning(f"Failed to query bars for asset_class={asset_class}: {e}")
    instrument_ids_with_bars = set()
```

```typescript
// Next.js proxy: Added error logging
const errorPreview = JSON.stringify(errorData).substring(0, 500)
console.error(`[Bundles Instruments] Backend error (${response.status}):`, errorPreview)
```

### Testing

1. Open `/admin/bundles/new`
2. Select an asset class (e.g., "crypto")
3. Verify instruments load without errors
4. Check browser console and server logs for any errors

---

## Issue 2: "Invalid request data" on Backtest Run with Bundle

### Root Cause

The validation schemas (both Zod in Next.js and Pydantic in FastAPI) required `instrument_ids` to be present with at least one ID, even when `bundle_id` was provided. When a bundle was selected, the frontend sent `bundle_id` but `instrument_ids` could be empty or missing, causing validation to fail.

### Files Changed

1. **`api/services/backtest/schemas.py`**:
   - Changed `instrument_ids` from required (`Field(...)`) to optional (`Field(None)`)
   - Added `@model_validator` to ensure either `bundle_id` OR `instrument_ids` (with at least one) is provided
   - Removed `min_length=1` constraint from `instrument_ids` field definition

2. **`web/src/app/api/backtests/run/route.ts`**:
   - Updated Zod schema: `instrument_ids` is now optional
   - Added `.refine()` to validate that either `bundle_id` or `instrument_ids` (with at least one) is provided
   - Improved error logging for 422 validation errors
   - Better error message forwarding to frontend

3. **`web/src/components/backtests/BacktestBuilder.tsx`**:
   - Updated `handleRun()` to send either `bundle_id` OR `instrument_ids` (not both)
   - Changed strategy type from 'bundle' to 'equal_weight' when sending to backend (backend expects 'equal_weight'/'momentum')
   - Improved validation message

4. **`web/src/components/backtests/api.ts`**:
   - Enhanced error message extraction from backend responses
   - Better handling of Pydantic validation errors (array format)

5. **`api/services/backtest/routes.py`**:
   - Added explicit validation check at route level
   - Improved error message when neither `bundle_id` nor `instrument_ids` provided

### Key Changes

```python
# Backend schema: instrument_ids is now optional
instrument_ids: Optional[List[int]] = Field(None, max_length=50, ...)

# Model validator ensures either bundle_id or instrument_ids
@model_validator(mode='after')
def validate_bundle_or_instruments(self):
    if self.bundle_id is None:
        if not self.instrument_ids or len(self.instrument_ids) == 0:
            raise ValueError("Either bundle_id or instrument_ids (with at least one ID) must be provided")
    return self
```

```typescript
// Next.js schema: instrument_ids is optional, refine ensures either/or
instrument_ids: z.array(z.number().int().positive()).max(50).optional(),
bundle_id: z.number().int().positive().optional(),
}).refine(
  (data) => data.bundle_id !== undefined || (data.instrument_ids !== undefined && data.instrument_ids.length > 0),
  { message: "Either bundle_id or instrument_ids (with at least one ID) must be provided" }
)
```

```typescript
// Frontend: Send either bundle_id OR instrument_ids
const request: BacktestCreateRequest = {
  start_date: startDate,
  end_date: endDate,
  ...(selectedBundleId 
    ? { bundle_id: selectedBundleId } 
    : { instrument_ids: selectedInstrumentIds }
  ),
  // ...
}
```

### Testing

1. Open `/admin/backtests`
2. Select an asset class and a bundle
3. Set start/end dates
4. Click "Run Backtest"
5. Verify backtest runs successfully
6. Test without bundle (select instruments manually) - should also work
7. Test with neither bundle nor instruments - should show validation error

---

## Additional Improvements

### Logging

- Added structured logging in Next.js proxy routes with prefixes: `[Bundles Instruments]`, `[Backtest Run]`
- Backend errors are logged with first 500 chars for debugging
- Connection errors are detected and reported clearly

### Error Handling

- 422 validation errors are now properly forwarded from backend to frontend
- Error messages are more descriptive and actionable
- Frontend displays detailed validation errors instead of generic "Invalid request data"

### Tests

- Added `api/tests/test_backtest_with_bundle.py` with integration tests:
  - `test_backtest_create_request_with_bundle_id`
  - `test_backtest_create_request_with_instrument_ids`
  - `test_backtest_create_request_rejects_missing_both`
  - `test_backtest_create_request_accepts_both`

---

## Manual Testing Checklist

### Bundle Instruments Endpoint

- [ ] Open `/admin/bundles/new`
- [ ] Select asset class "crypto"
- [ ] Verify instruments load (no toast error)
- [ ] Switch to "etf" asset class
- [ ] Verify instruments reload correctly
- [ ] Check browser console for any errors
- [ ] Check server logs for any warnings

### Backtest with Bundle

- [ ] Open `/admin/backtests`
- [ ] Select asset class "crypto"
- [ ] Select a bundle
- [ ] Set start date: `2024-01-01`
- [ ] Set end date: `2024-12-31`
- [ ] Click "Run Backtest"
- [ ] Verify backtest completes successfully
- [ ] Check that results are displayed

### Backtest without Bundle

- [ ] Open `/admin/backtests`
- [ ] Select asset class "crypto"
- [ ] Select individual instruments (no bundle)
- [ ] Set dates and run backtest
- [ ] Verify it works

### Error Cases

- [ ] Try to run backtest with no bundle and no instruments selected
- [ ] Verify clear error message is shown
- [ ] Try to load instruments for invalid asset class
- [ ] Verify error is handled gracefully

---

## Files Modified

### Backend (FastAPI)

- `api/services/bundles/routes.py` - Added error handling to instruments endpoint
- `api/services/backtest/schemas.py` - Made `instrument_ids` optional, added model validator
- `api/services/backtest/routes.py` - Added explicit validation check

### Frontend (Next.js)

- `web/src/app/api/bundles/asset-classes/[asset_class]/instruments/route.ts` - Improved error handling and logging
- `web/src/app/api/backtests/run/route.ts` - Updated schema, improved error forwarding
- `web/src/components/backtests/BacktestBuilder.tsx` - Fixed request payload construction
- `web/src/components/backtests/api.ts` - Enhanced error message extraction
- `web/src/app/admin/bundles/new/page.tsx` - Improved error handling

### Tests

- `api/tests/test_backtest_with_bundle.py` - New integration tests

---

## Notes

- All changes are backward compatible
- Existing backtests without bundles continue to work
- No database migrations required
- No breaking changes to API contracts (only validation improvements)

