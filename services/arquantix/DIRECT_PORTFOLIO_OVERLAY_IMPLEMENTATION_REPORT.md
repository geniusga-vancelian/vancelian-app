# Direct Portfolio Overlay — Implementation Report

## Executive Summary

Implemented a **structural separation** between direct holdings and bundle holdings using the Portfolio Engine overlay system. Every client now has a `direct_portfolio` alongside their existing `bundle_portfolio`(s), with real-time sync on every BUY/SELL/SWAP operation and historical backfill for existing positions.

Key outcomes:
- **"Mes crypto"** displays only direct (non-bundle) holdings
- **"Mes bundles"** continues to display only bundle portfolio positions
- **`crypto_positions`** remains the consolidated truth — untouched
- **Invariant F** guarantees: `Σ direct_atoms + Σ bundle_atoms = crypto_positions.balance` per asset
- **Zero breaking changes** to existing BUY/SELL/SWAP flows, Bundle Engine, or WAC/PnL accounting

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  crypto_positions (consolidated)             │
│        = direct holdings + bundle holdings + future scopes   │
└────────────────────┬────────────────────┬───────────────────┘
                     │                    │
    ┌────────────────▼────────┐  ┌───────▼──────────────────┐
    │   direct_portfolio       │  │  bundle_portfolio A/B     │
    │   pe_position_atoms      │  │  pe_position_atoms        │
    │   (position_type=spot)   │  │  (spot + cash)            │
    │                          │  │                           │
    │  → "Mes crypto" UI       │  │  → "Mes bundles" UI       │
    └──────────────────────────┘  └───────────────────────────┘
```

### Scope Attribution

| Operation | External Reference Pattern | Scope | Direct Atom Sync |
|-----------|---------------------------|-------|-----------------|
| Mobile BUY | `mobile-buy-{uuid}` | direct | ✅ Credit |
| Mobile SELL | `mobile-sell-{uuid}` | direct | ✅ Debit |
| Mobile SWAP | `mobile-swap-{uuid}` | direct | ✅ Debit source + Credit target |
| Sell-all | `sell-all-{batch}-{asset}` | direct | ✅ Debit |
| Bundle fund | `bundle-fund-{batch}` | bundle | ❌ Skipped (orchestrator handles) |
| Bundle alloc | `bundle-alloc-{batch}-{asset}` | bundle | ❌ Skipped (orchestrator handles) |

---

## Direct Portfolio Design

### New Module: `api/services/portfolio_engine/direct_overlay.py`

Core functions:

| Function | Purpose |
|----------|---------|
| `ensure_direct_portfolio(db, client_id)` | Auto-provision `direct_portfolio` for a client (idempotent) |
| `sync_direct_atom(db, portfolio_id, instrument_id, qty_delta, cost_delta)` | Create/update a direct PE atom (additive delta) |
| `backfill_direct_atoms(db, client_id)` | Backfill direct atoms from `crypto_positions - bundle_atoms` |
| `check_invariant_f(db, client_id)` | Verify `direct + bundle = crypto_positions` per asset |

### Portfolio Type Addition

Added `DIRECT_PORTFOLIO = "direct_portfolio"` to `PortfolioType` enum in `portfolios/enums.py`.

---

## Order Scope Attribution

Orders are now tagged in `metadata_` with:
- `portfolio_scope`: `"direct"` for non-bundle operations
- `portfolio_id`: UUID of the direct portfolio

Detection uses `external_reference` prefix:
- Starts with `bundle-` → bundle scope (PE sync handled by BundleOrchestrator)
- Otherwise → direct scope (PE sync in ExchangeService)

---

## Historical Backfill Strategy

The backfill computes direct quantities per asset:

```
direct_qty = crypto_positions.balance - Σ bundle_atom.quantity
```

Cost basis is computed via:
1. Global WAC price from `exchange_orders` (same as `wallet_statistics`)
2. Subtract bundle atoms' cost_basis from the total WAC cost

The backfill:
- Is idempotent (updates existing atoms, creates missing ones)
- Runs automatically on first access to `GET /api/app/crypto-positions/direct` if no direct atoms exist
- Can be triggered manually via `POST /api/app/direct-portfolio/backfill`

---

## Invariants Added

### Invariant F (NEW)

```
∀ asset:  Σ direct_atoms.quantity + Σ bundle_atoms.quantity = crypto_positions.balance
```

Tolerance: `0.000001` (rounding artefacts from bundle allocation SWAPs).

Endpoint: `GET /api/app/direct-portfolio/invariant-f`

### Existing Invariants (PRESERVED)

| Invariant | Description | Status |
|-----------|-------------|--------|
| A, B, C | Global accounting invariants | Unchanged |
| D | `Σ PE atoms ≤ crypto_positions.balance` | Unchanged (now naturally satisfied when F holds) |
| E | Bundle cash leg consistency | Unchanged |

---

## PnL / WAC / Chart Scope Changes

### Phase 1 (This Implementation)

- **Positions display**: Scoped via direct portfolio atoms (quantity, cost_basis, avg_entry_price)
- **Hero total**: Computed as `direct_total + bundle_total` for a complete portfolio view
- **Wallet statistics / history**: Currently unchanged — they still use global `exchange_orders` and `crypto_positions`. This is acceptable because:
  - WAC is a fungible average across all buy orders
  - Charts show global portfolio performance (which users expect on the hero)

### Phase 2 (Future)

To scope stats/history per portfolio:
- Filter `exchange_orders` by `metadata_.portfolio_id` for per-scope PnL
- Build `wallet_history` with scope parameter (direct vs bundle vs global)
- Per-scope WAC requires tracking buys by portfolio_id

---

## UI Impact

### "Mes crypto" (AllCryptoPositionsScreen)

- **Before**: `fetchPositions()` → ALL positions from `crypto_positions` (consolidated)
- **After**: `fetchDirectPositions()` → Only direct holdings from the direct portfolio overlay
- Fallback: If the direct endpoint fails, gracefully degrades to the consolidated endpoint

### "Mes bundles"

Unchanged — continues using `getMyBundles()` → bundle portfolio atoms with live valuation.

### Hero Section

Total value = direct positions value + active bundles market value. This gives an accurate consolidated view while the underlying data is structurally separated.

### Count Label

Updated from `"X crypto-actifs"` to `"X cryptos · Y bundles"` for clarity.

---

## New Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/app/crypto-positions/direct` | GET | Direct-only positions with prices (powers "Mes crypto") |
| `/api/app/direct-portfolio/backfill` | POST | Trigger backfill of direct atoms |
| `/api/app/direct-portfolio/invariant-f` | GET | Check invariant F |

### Next.js Proxies

| Flutter Route | Backend |
|---------------|---------|
| `/api/mobile/flutter/crypto-positions/direct` | `/api/app/crypto-positions/direct` |
| `/api/mobile/flutter/direct-portfolio/backfill` | `/api/app/direct-portfolio/backfill` |

---

## Tests Added

### Test 1: Client with existing holdings → backfill
- Backfill endpoint creates direct atoms matching `crypto_positions - bundle_atoms`
- Idempotent on re-run

### Test 2: Bundle investment after migration
- Bundle atoms go to bundle_portfolio
- Direct atoms untouched

### Test 3: BUY spot direct
- `crypto_positions.balance` increases
- Direct atom quantity increases by same amount
- `metadata_.portfolio_scope = "direct"` on the exchange_order

### Test 4: SELL spot direct
- `crypto_positions.balance` decreases
- Direct atom quantity decreases
- Cost basis consumed properly

### Test 5: SWAP spot direct
- Source direct atom debited
- Target direct atom credited
- `crypto_positions` reflects both changes

### Test 6: Invariant F
- After BUY: `direct_atoms + bundle_atoms = crypto_positions` ✓
- After SELL: still holds ✓
- After bundle invest: still holds ✓

### Test 7-8: Wallet stats / charts
- Unchanged (global view, not yet scoped per portfolio)

### Test 9: Non-regression bundle
- Bundle invest flow unchanged
- Bundle atoms unchanged
- Cash leg unchanged

### Test 10: Non-regression global
- `crypto_positions` consolidated view unchanged
- WAC computation unchanged
- All exchange operations unchanged

---

## Files Modified

### Backend

| File | Changes |
|------|---------|
| `api/services/portfolio_engine/portfolios/enums.py` | Added `DIRECT_PORTFOLIO` to `PortfolioType` |
| `api/services/portfolio_engine/direct_overlay.py` | **NEW** — core module: provisioning, sync, backfill, invariant F |
| `api/services/exchange/service.py` | BUY/SELL/SWAP now sync direct atoms + tag orders |
| `api/services/test_clients/router.py` | New endpoints: direct positions, backfill, invariant F |

### Frontend (Next.js Proxy)

| File | Changes |
|------|---------|
| `web/src/app/api/mobile/flutter/crypto-positions/direct/route.ts` | **NEW** — proxy for direct positions |
| `web/src/app/api/mobile/flutter/direct-portfolio/backfill/route.ts` | **NEW** — proxy for backfill |

### Mobile (Flutter)

| File | Changes |
|------|---------|
| `mobile/lib/core/config.dart` | Added `directCryptoPositionsUrl` |
| `mobile/lib/features/wallet/data/crypto_positions_api.dart` | Added `fetchDirectPositions()` method |
| `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` | "Mes crypto" now uses direct endpoint; hero total = direct + bundles |

---

## Final Status

| Component | Status |
|-----------|--------|
| Direct portfolio type | ✅ Added |
| Auto-provisioning | ✅ Implemented |
| Atom sync on BUY | ✅ Implemented |
| Atom sync on SELL | ✅ Implemented |
| Atom sync on SWAP | ✅ Implemented |
| Bundle detection (skip sync) | ✅ Via external_reference prefix |
| Backfill script | ✅ Implemented |
| Invariant F | ✅ Implemented |
| Direct positions endpoint | ✅ Implemented |
| Flutter UI adaptation | ✅ "Mes crypto" = direct only |
| Non-regression bundles | ✅ Preserved |
| Non-regression BUY/SELL/SWAP | ✅ Preserved |
| Non-regression crypto_positions | ✅ Untouched |
