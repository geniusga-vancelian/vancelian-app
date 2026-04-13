# Bundle Orchestrator — Phase 2: True Cash Leg Report

## Executive Summary

Phase 2 transforms the bundle engine from "EUR → direct buy each target" into a true entry-wallet model:

```
EUR → BUY entry_asset (USDC) → credit cash leg → SWAP to each target → debit cash leg
```

The cash leg is a persistent `PositionAtom` with `position_type='cash'`, living in the same PE portfolio overlay. No changes to `crypto_positions`, `WAC`, or `PnL` accounting. All 8 mandatory tests pass, and 85 non-regression tests confirm zero breakage.

## Why Phase 1 Was Not Yet a True Entry Wallet Model

Phase 1 implemented:
- `entry_asset_default` / `entry_assets_allowed` in `ProductDefinition.metadata_`
- `BundleOrchestrator.invest_into_bundle()` with best-effort allocation
- `pe_position_atoms` synchronization
- `exchange_orders` tagging with `bundle_id`
- Invariant D

However, Phase 1 had a critical architectural gap:

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| Funding path | EUR → BUY each target directly | EUR → BUY USDC → SWAP to targets |
| Cash leg | Implicit (computed from `remaining`) | Persistent `PositionAtom` type=cash |
| Partial failure remainder | Lost / ephemeral in return dict | Persisted in cash leg atom |
| Entry asset in Exchange | USDC not supported | USDC + EURC added to `SUPPORTED_ASSETS` |
| Retry / DCA capability | Not possible | Natural: top-up cash leg, re-allocate |
| Bundle status query | Not available | `GET /bundle/{id}/status` endpoint |

## Cash Leg Design

### Approach: PositionAtom with `position_type='cash'`

The lightest overlay-compatible solution. No new table, no schema migration.

```
PositionAtom (cash leg)
├── portfolio_id → bundle portfolio
├── instrument_id → USDC spot instrument (auto-resolved)
├── position_type = "cash"
├── quantity = remaining USDC balance
├── cost_basis = EUR equivalent funded
└── metadata_ = {"role": "bundle_cash_leg"}

PositionAtom (allocated position)
├── portfolio_id → same bundle portfolio
├── instrument_id → BTC/ETH/SOL instrument
├── position_type = "spot"
├── quantity = crypto received
└── cost_basis = reference value from swap
```

### Why This Works

- Same table, same queries, same PE overlay model
- `position_type` cleanly separates cash from allocations
- `_credit_cash_leg` / `_debit_cash_leg` are atomic operations
- Future retry/DCA simply credits the existing cash leg atom
- `get_bundle_status()` queries both types in a single pass

## Funding Flow

### Case 1: EUR Funding

```
Client sends: POST /api/app/bundle/invest
  { portfolio_id, funding_asset: "EUR", funding_amount: 2000 }

1. Validate portfolio (bundle_portfolio, active, client match)
2. Resolve entry_asset from ProductDefinition.metadata_ (default: USDC)
3. ExchangeService.buy(EUR → USDC, amount=2000€)
   → Creates exchange_order, credits crypto_positions.USDC
   → Tags order: bundle_action="funding"
4. Credit cash leg atom: quantity=USDC_received, cost_basis=2000€
5. For each target allocation:
   a. Compute alloc_amount = USDC_received × target_weight
   b. ExchangeService.swap(USDC → BTC/ETH, amount=alloc_amount)
      → Tags orders: bundle_action="allocation"
   c. Credit spot atom, debit cash leg
6. Cash leg retains any unallocated remainder
```

### Case 2: Direct Entry Asset Funding

```
Client sends: POST /api/app/bundle/invest
  { portfolio_id, funding_asset: "USDC", funding_amount: 1000 }

1. Skip BUY step (client already has USDC in crypto_positions)
2. Credit cash leg atom directly
3. Allocate from cash leg via SWAPs (same as above)
```

### Case 3: Partial Failure

```
Target allocation: BTC 50%, ETH 30%, SOL 20%
SOL quote is stale → swap fails

Result:
- BTC leg: completed ✓
- ETH leg: completed ✓
- SOL leg: failed ✗
- Cash leg: retains 20% of USDC (SOL's share)
- Status: "partial"
- No amount disappears
```

## Allocation From Cash Leg

Each allocation leg:

1. Computes `alloc_entry_amount = entry_qty_received × target_weight`
2. Executes `ExchangeService.swap(entry_asset → target_asset, alloc_entry_amount)`
3. On success:
   - `_sync_pe_position()` → credits/creates spot atom
   - `_debit_cash_leg()` → decrements cash leg quantity and cost_basis
4. On failure:
   - Cash leg untouched for this leg
   - Warning logged, execution continues with remaining legs

## PE ↔ Exchange Synchronization

### Order Tagging

All `exchange_orders` are tagged via `metadata_` JSONB:

| Field | Funding Order | Allocation Orders |
|-------|---------------|-------------------|
| `bundle_id` | portfolio UUID | portfolio UUID |
| `bundle_batch_id` | batch UUID | batch UUID |
| `bundle_action` | `"funding"` | `"allocation"` |

### Position Sync

| Layer | Updated By | Contains |
|-------|------------|----------|
| `crypto_positions` | Exchange Engine (unchanged) | Consolidated client balances |
| `pe_position_atoms` (cash) | `_credit_cash_leg` / `_debit_cash_leg` | Bundle entry-asset remainder |
| `pe_position_atoms` (spot) | `_sync_pe_position` | Bundle allocated positions |

## Bundle Invariants

### Invariant D (preserved from Phase 1)

```
∀ asset: Σ pe_position_atoms.quantity ≤ crypto_positions.balance
```

PE atoms are an overlay view; they must never exceed the consolidated Exchange position. Verified via `check_invariant_d()`.

### Invariant E (new in Phase 2)

```
cash_leg.cost_basis + Σ spot_atoms.cost_basis = total_cost_basis ≥ 0
```

The total cost basis across all atoms in a bundle portfolio must be non-negative and represent the net funding. Verified via `check_invariant_e()`.

API endpoints:
- `GET /api/app/bundle/invariant-d` — global PE vs Exchange check
- `GET /api/app/bundle/{portfolio_id}/invariant-e` — per-bundle cash accounting check

## Backward Compatibility

### USDC/EURC in Exchange Engine

Added to `services/exchange/assets.py`:
- `SUPPORTED_ASSETS`: `{"BTC", "ETH", "SOL", "XRP", "ADA", "USDC", "EURC"}`
- `ASSET_PRECISION`: USDC=6, EURC=6
- `ASSET_PROVIDER_SYMBOL_MAP`: USDCUSDT, EURCUSDT

Impact:
- Standard BUY/SELL/SWAP now work for USDC and EURC
- Settlement bootstrap creates custody accounts for all 7 assets
- Existing settlement test updated to zero all assets (not just original 5)

### Existing Bundles

Fallback chain:
1. `ProductDefinition.metadata_.entry_asset_default` → configured value
2. If absent → `"USDC"` (module-level fallback)

Bundles created before Phase 2 have no `entry_asset_default` in metadata → automatic fallback to USDC.

### Unchanged Components

- `ExchangeService.buy()` / `sell()` / `swap()` — no modifications
- WAC calculation — untouched
- PnL accounting (realized/unrealized) — untouched
- Invariants A/B/C — untouched
- `crypto_positions` schema — no segmentation by bundle
- Wallet statistics — unaffected
- Portfolio statistics — unaffected

## Tests Added

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_eur_funding_creates_cash_leg` | EUR → BUY USDC → cash leg atom created |
| 2 | `test_allocation_from_cash_leg` | USDC swapped to BTC + ETH per weights, spot atoms exist |
| 3 | `test_partial_failure_remainder_in_cash_leg` | SOL stale → 2 legs succeed, remainder in cash leg |
| 4 | `test_direct_entry_asset_funding` | Client pre-buys USDC → no BUY step, direct allocation |
| 5 | `test_sync_cash_leg_and_atoms` | Orders tagged funding/allocation, bundle status returns correctly |
| 6 | `test_invariant_d_holds` | PE atoms ≤ crypto_positions after investment |
| 7 | `test_invariant_e_holds` | Cash + allocated cost_basis = total cost_basis |
| 8 | `test_non_regression` | BUY/SELL BTC, BUY USDC, wallet stats, portfolio stats unchanged |

**Results**: 8/8 passed + 85 non-regression tests passed (0 failures).

## Final Status

| Item | Status |
|------|--------|
| USDC/EURC in SUPPORTED_ASSETS | ✅ Done |
| Cash leg as PositionAtom(type=cash) | ✅ Done |
| EUR → USDC → allocation flow | ✅ Done |
| Direct entry-asset flow | ✅ Done |
| Partial failure with remainder persistence | ✅ Done |
| Bundle status endpoint | ✅ Done |
| Invariant D preserved | ✅ Done |
| Invariant E implemented | ✅ Done |
| 8 mandatory tests | ✅ 8/8 passed |
| Non-regression | ✅ 85/85 passed |
| crypto_positions untouched | ✅ Verified |
| WAC/PnL untouched | ✅ Verified |

### Files Modified

| File | Change |
|------|--------|
| `api/services/exchange/assets.py` | Added USDC, EURC to supported assets |
| `api/services/portfolio_engine/bundles/orchestrator.py` | Full Phase 2 rewrite: cash leg, 2-step funding, allocation from cash leg, invariant E, bundle status |
| `api/services/test_clients/router.py` | Added `GET /bundle/{id}/status` and `GET /bundle/{id}/invariant-e` endpoints |
| `api/tests/test_bundle_orchestrator.py` | 8 Phase 2 tests |
| `api/tests/test_exchange_engine.py` | Fixed settlement test to use dynamic SUPPORTED_ASSETS |

### Ready for Phase 3

The architecture now supports:
- **Retry**: top up the cash leg, re-run failed allocation legs
- **Rebalance**: compare current vs target, generate SWAP orders from over/under-weighted positions
- **DCA**: periodic `invest_into_bundle` calls add to cash leg and allocate
- **Withdrawal**: reverse flow — sell allocations, credit cash leg, optionally sell entry asset back to EUR
