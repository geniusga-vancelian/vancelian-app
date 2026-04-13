# Phase 1.5 — Test Framing for Future Non-Spot Positions

## Executive Summary

Phase 1 has formalized the position model: all atoms are explicitly `spot` or `cash`, guards block any other type, and 29 tests enforce these invariants.

Phase 1.5 does **NOT** enable lending. It defines, documents, and prepares the exact guarantees that the first non-spot position type must satisfy to avoid breaking the existing system.

This document is the **contract** for Phase 2: every assertion listed here must pass before lending can go live.

---

## Why Phase 1.5 Exists

The current system has **hidden spot-only assumptions** scattered across 7+ files. Introducing a lending position without a precise test plan would risk:

1. **Double-counting**: `valuation._compute_atoms_value` sums ALL open atoms regardless of type — lending atoms would inflate portfolio value if also reflected in `crypto_positions`
2. **Invariant F breakage**: `check_invariant_f` compares `Σ spot atoms` to `crypto_positions.balance` — lending atoms in the same balance would cause drift
3. **History corruption**: `wallet_history` reconstructs NAV from `ExchangeOrder` — lending movements don't create exchange orders
4. **Statistics leakage**: `_sum_portfolio_value` treats non-cash atoms as spot — lending atoms would be valued as spot

Phase 1.5 maps every risk and defines the test that will catch it.

---

## Compatibility Guarantees (Family A)

### Principle

After introducing lending, **every existing spot flow must produce identical results**.

### Invariants

| ID | Invariant | Current Source | Risk Level |
|----|-----------|---------------|------------|
| A1 | BUY crypto produces only `position_type=spot` atoms | `sync_direct_atom` | LOW — hardcoded |
| A2 | SELL crypto produces only `position_type=spot` atoms | `sync_direct_atom` | LOW — hardcoded |
| A3 | SWAP produces only `position_type=spot` atoms | `sync_direct_atom` (x2) | LOW — hardcoded |
| A4 | Bundle invest produces `spot` + `cash` atoms only | `_sync_pe_position`, `_credit_cash_leg` | LOW — hardcoded |
| A5 | Bundle rebalance preserves `spot` + `cash` only | `BundleRebalanceOrchestrator` | LOW — hardcoded |
| A6 | `crypto_positions.balance` is unchanged by lending | `CryptoPositionRepository.credit/debit` | MEDIUM — no filter |
| A7 | Valuation total_value is unchanged for a client with no lending | `get_portfolio_breakdown` | HIGH — no position_type filter in `_compute_atoms_value` |
| A8 | `wallet_statistics` for spot assets are unchanged | `build_wallet_statistics` | MEDIUM — scope global uses `crypto_positions` |
| A9 | `wallet_history` NAV curve is unchanged | `build_wallet_history` | LOW — uses `ExchangeOrder` only |
| A10 | `build_global_history` is unchanged for spot-only client | `build_global_history` | MEDIUM — delegates to wallet_history + fiat |

### Required Tests (Phase 2)

```
test_future_lending_compatibility.py

- test_buy_still_produces_spot_only
- test_sell_still_produces_spot_only
- test_swap_still_produces_spot_only
- test_bundle_invest_still_produces_spot_and_cash_only
- test_bundle_rebalance_still_produces_spot_and_cash_only
- test_crypto_positions_unchanged_by_lending_atom
- test_valuation_unchanged_for_spot_only_client
- test_wallet_statistics_unchanged_for_spot_only_client
- test_wallet_history_unchanged_for_spot_only_client
- test_global_history_unchanged_for_spot_only_client
```

---

## Separation Guarantees (Family B)

### Principle

A lending position must **never leak into spot views**.

### Component-by-Component Analysis

| Component | Current Behavior | Spot-Only Filter? | If Lending Exists | Required Adaptation |
|-----------|-----------------|-------------------|-------------------|---------------------|
| `crypto_positions` | 1 row per (client, asset) | NO `position_type` column | Lending must NOT be reflected here | Keep separate — lending lives only in `pe_position_atoms` |
| `pe_position_atoms` | atoms with `position_type` field | YES (guards) | Lending atoms coexist with spot atoms | No structural change needed |
| `valuation._compute_atoms_value` | Sums ALL open atoms | **NO** — no filter on `position_type` | Lending atoms would be summed into portfolio value | **MUST filter** or scope by `position_type` |
| `_sum_portfolio_value` (router) | Distinguishes `cash` vs else | **PARTIAL** — treats non-cash as spot | Lending would be valued as spot | **MUST add lending branch** |
| `wallet_history` | Uses `ExchangeOrder` | N/A (no atoms) | No impact (lending has no exchange orders) | Add lending events as separate data source in Phase 3+ |
| `wallet_statistics._get_scoped_position_size` | Filters `position_type == "spot"` | **YES** | Lending excluded from size | Safe — but lending stats need separate endpoint |
| `direct_overlay.check_invariant_f` | `Σ spot atoms ≈ crypto_positions` | **YES** — spot only | Safe if crypto_positions remains spot-only | Update invariant if crypto_positions evolves |
| `direct_overlay.backfill_direct_atoms` | `direct = total - bundle_spot` | **YES** — spot only | Safe if crypto_positions remains spot-only | Same as above |
| `mobile_my_bundles` | Counts atoms where `position_type == "spot"` for `assets_count` | **YES** | Lending not counted | Safe |
| `mobile_bundle_statistics` | All atoms, distinguishes cash vs else | **NO** on position_type | Lending would appear in bundle stats | **MUST filter** |
| `get_direct_crypto_positions` | `position_type == "spot"` | **YES** | Lending excluded | Safe |

### Critical Separation Rules

| ID | Rule | Enforcement Point |
|----|------|-------------------|
| B1 | Lending atoms MUST NOT appear in `crypto_positions` | `CryptoPositionRepository` — never called for lending |
| B2 | Lending atoms MUST NOT be reconstructed as spot in `wallet_history` | `build_wallet_history` — uses only `ExchangeOrder` |
| B3 | Lending atoms MUST NOT be valued as spot in `_compute_atoms_value` | **REQUIRES FIX**: add `position_type` filter |
| B4 | Lending atoms MUST NOT pollute direct portfolio wallets | `get_direct_crypto_positions` already filters spot |
| B5 | Lending atoms MUST NOT be counted as spot atoms | All spot queries already filter by type |
| B6 | Bundle/direct/global views MUST remain coherent | Depends on B3 fix |
| B7 | Lending atoms MUST NOT affect `_sum_portfolio_value` as spot | **REQUIRES FIX**: add position_type branch |

### Required Tests (Phase 2)

```
test_future_lending_separation.py

- test_lending_atom_not_in_crypto_positions
- test_lending_atom_not_in_wallet_history
- test_lending_atom_not_in_spot_valuation
- test_lending_atom_not_in_direct_wallet_view
- test_lending_atom_not_counted_as_spot
- test_bundle_views_coherent_with_lending_present
- test_portfolio_breakdown_excludes_lending_from_spot_value
- test_invariant_f_holds_with_lending_atoms_present
```

---

## Ledger / Custody Guarantees (Family C)

### Principle

A future `spot → lending` transfer must be **fully traceable, balanced, and reversible**.

### Current Ledger Architecture

```
pe_ledger_accounts (per client, per asset, per account_type)
    ↕ post_double_entry
pe_ledger_entries (append-only, debit/credit pairs linked by counterpart_entry_id)
```

Key properties:
- **Double-entry**: every movement creates exactly 2 entries (debit + credit)
- **Append-only**: no UPDATE/DELETE on entries
- **Balanced**: `account.balance = Σ(debits) - Σ(credits)` — verified by reconciliation
- **Typed references**: `reference_type` in (`custody_transaction`, `exchange_order`, `settlement`, `custody_reversal`)

### Future Lending Transfer Flow

```
1. Client requests: lock 0.5 BTC for lending strategy
2. System verifies: spot atom has sufficient available_quantity
3. Custody: create CustodyTransaction (kind="lending_deposit")
4. Ledger: post_double_entry(
     debit: client_spot_BTC account,
     credit: client_lending_BTC account,
     reference_type="lending_transfer",
     reference_id=<custody_tx_id>
   )
5. Atoms: spot atom.quantity -= 0.5, lending atom.quantity += 0.5
6. Audit: AuditEvent(action="lending_deposit", ...)
```

### Tables to Observe

| Table | What to Verify |
|-------|---------------|
| `pe_position_atoms` | Spot atom decremented, lending atom created/incremented |
| `pe_ledger_entries` | Double-entry pair with `reference_type="lending_transfer"` |
| `pe_ledger_accounts` | Balance updated for both spot and lending accounts |
| `custody_transactions` | Transaction of `kind="lending_deposit"` created |
| `crypto_positions` | **Unchanged** — lending does not affect spot balance |
| `audit_events` | Trail entry for the transfer |

### Ledger Invariants That Must Hold

| ID | Invariant | Verification |
|----|-----------|-------------|
| C1 | Double-entry: every lending transfer creates exactly 2 linked entries | `counterpart_entry_id IS NOT NULL` for both entries |
| C2 | Balance consistency: `account.balance = Σ(debits) - Σ(credits)` | `ReconciliationService._reconcile_ledger_entries_vs_balances` |
| C3 | Currency consistency: all entries in a transfer match the asset | `LedgerEntryService._validate_currency_chain` |
| C4 | `crypto_positions` unchanged after spot→lending transfer | Query before/after |
| C5 | Audit trail: transfer is logged | `AuditEvent` query |
| C6 | Reversibility: lending→spot produces symmetric entries | `reference_type="lending_withdrawal"` |
| C7 | Net zero: sum of all transfer entries between spot/lending accounts = 0 | Ledger query |

### Required Tests (Phase 2)

```
test_future_lending_ledger.py

- test_spot_to_lending_creates_double_entry
- test_spot_to_lending_preserves_custody_balance
- test_spot_to_lending_leaves_crypto_positions_unchanged
- test_spot_to_lending_ledger_balanced
- test_spot_to_lending_creates_audit_trail
- test_lending_to_spot_symmetric
- test_net_zero_after_round_trip
- test_insufficient_spot_rejects_lending_transfer
```

---

## Future Test Matrix

| Family | Test Scenario | Expected Result | Target Component | Priority |
|--------|---------------|-----------------|------------------|----------|
| A | BUY produces spot-only atoms | position_type == spot | `sync_direct_atom` | P0 |
| A | SELL produces spot-only atoms | position_type == spot | `sync_direct_atom` | P0 |
| A | SWAP produces spot-only atoms | position_type == spot | `sync_direct_atom` | P0 |
| A | Bundle invest produces spot+cash | spot/cash only | `BundleOrchestrator` | P0 |
| A | Bundle rebalance preserves spot+cash | spot/cash only | `BundleRebalanceOrchestrator` | P0 |
| A | crypto_positions unchanged by lending | balance identical | `CryptoPositionRepository` | P0 |
| A | Valuation unchanged for spot-only client | total_value identical | `get_portfolio_breakdown` | P0 |
| A | Wallet statistics unchanged | all metrics identical | `build_wallet_statistics` | P1 |
| A | Wallet history unchanged | NAV curve identical | `build_wallet_history` | P1 |
| A | Global history unchanged | timeline identical | `build_global_history` | P1 |
| B | Lending not in crypto_positions | no balance change | `CryptoPositionRepository` | P0 |
| B | Lending not in wallet_history | no NAV impact | `build_wallet_history` | P0 |
| B | Lending not valued as spot | excluded from _compute_atoms_value | `valuation.py` | P0 |
| B | Lending not in direct wallet view | excluded | `get_direct_crypto_positions` | P0 |
| B | Lending not counted as spot atom | excluded from Σ | `PositionAtom` queries | P0 |
| B | Bundle views coherent with lending present | no pollution | `mobile_bundle_statistics` | P1 |
| B | Portfolio breakdown excludes lending from spot | separate line | `get_portfolio_breakdown` | P0 |
| B | Invariant F holds with lending present | direct+bundle ≈ crypto | `check_invariant_f` | P0 |
| C | Spot→lending creates double entry | 2 linked entries | `LedgerEntryService` | P0 |
| C | Spot→lending preserves custody balance | unchanged | `CustodyAccountBalance` | P0 |
| C | Spot→lending leaves crypto_positions unchanged | unchanged | `CryptoPosition` | P0 |
| C | Ledger balanced after transfer | Σ=0 | `pe_ledger_entries` | P0 |
| C | Audit trail created | event logged | `audit_events` | P1 |
| C | Lending→spot symmetric | reverse entries | `LedgerEntryService` | P0 |
| C | Net zero after round trip | sum=0 | `pe_ledger_entries` | P0 |
| C | Insufficient spot rejects transfer | ValueError | spot atom check | P0 |

---

## Required Observability

### Metrics to Add in Phase 2

| Metric | Source | Purpose |
|--------|--------|---------|
| `position_atoms_by_type` | `pe_position_atoms GROUP BY position_type` | Monitor type distribution |
| `lending_transfer_count` | `pe_ledger_entries WHERE reference_type='lending_transfer'` | Track lending activity |
| `invariant_f_drift` | `check_invariant_f` | Detect spot/lending confusion |
| `lending_atoms_in_valuation` | `_compute_atoms_value` | Ensure no double-counting |

### Logs to Add in Phase 2

- Every `position_type` write: log `(atom_id, position_type, quantity, portfolio_id)`
- Every lending transfer: log `(client_id, asset, qty, from_type, to_type, ledger_entry_ids)`
- Invariant F check after any lending movement

---

## Recommended Phase 2 Test Strategy

### Pre-Flight (before writing any code)

1. Run all Phase 1 tests → must pass (29/29)
2. Run all existing regression tests → baseline failures documented
3. Create a test client with spot positions (BTC, ETH, USDC)
4. Record baseline: balances, valuations, history, statistics

### Implementation Order

1. Add `PositionType.LENDING` to `ALLOWED_POSITION_TYPES`
2. **IMMEDIATELY run** Family B separation tests → they should pass since no lending atoms exist yet
3. Create lending atom manually in test fixture
4. Run Family B → verify separation holds
5. Implement spot→lending transfer service
6. Run Family C → verify ledger integrity
7. Run Family A → verify no regression on spot flows

### Post-Flight

1. Re-run all Phase 1 tests (29/29)
2. Re-run all Phase 1.5 tests (A+B+C)
3. Run existing regression suite
4. Verify Invariant F holds
5. Verify reconciliation passes

---

## Answers to Key Questions

### 1. Which spot invariants must remain true after lending introduction?

- **Invariant A**: All trading flows produce only spot/cash atoms — enforced by guards
- **Invariant B**: `crypto_positions = Σ spot atoms` — must NOT include lending
- **Invariant F**: `direct_atoms + bundle_atoms ≈ crypto_positions` — spot only
- **Valuation**: `portfolio_value` for spot-only clients must not change
- **History**: NAV curves must not change for spot-only clients

### 2. Which components are safe to observe for lending separation?

- `crypto_positions` — must remain unchanged (no lending)
- `pe_position_atoms` — lending atoms must have `position_type="lending"` explicitly
- `wallet_statistics._get_scoped_position_size` — already filters spot
- `direct_overlay.check_invariant_f` — already filters spot

### 3. Which custody/ledger tables must be tracked for spot→lending transfer?

- `pe_ledger_entries` — double-entry verification
- `pe_ledger_accounts` — balance consistency
- `custody_transactions` — movement record with new `transaction_kind`
- `crypto_positions` — must remain unchanged

### 4. Which non-regression tests must be re-run at Phase 2?

| Test File | Tests | Relevance |
|-----------|-------|-----------|
| `test_position_type_spot_only.py` | 9 | Core — must still pass |
| `test_reject_non_spot_positions.py` | 20 | Update to allow lending |
| `test_bundle_orchestrator.py` | 15 | Bundle flows unaffected |
| `test_exchange_engine.py` | 14 | Trading flows unaffected |
| `test_exchange_sell.py` | 6 | Sell flows unaffected |
| `test_swap_crypto.py` | 6 | Swap flows unaffected |
| `test_auto_execution_engine.py` | 26 | Auto-execution unaffected |
| `test_auto_execution_concurrency.py` | 7 | Concurrency unaffected |
| `test_auto_execution_resilience.py` | 23 | Resilience unaffected |

### 5. Which components are most fragile when introducing the first non-spot type?

| Component | Fragility | Reason |
|-----------|-----------|--------|
| `valuation._compute_atoms_value` | **CRITICAL** | No position_type filter — lending atoms would inflate value |
| `_sum_portfolio_value` (router) | **HIGH** | Treats non-cash as spot — lending would leak |
| `mobile_bundle_statistics` (router) | **HIGH** | No position_type filter on atoms |
| `check_invariant_f` | **MEDIUM** | Safe if crypto_positions stays spot-only |
| `backfill_direct_atoms` | **MEDIUM** | Safe if crypto_positions stays spot-only |
| `accounting/invariants._get_crypto_value_eur` | **MEDIUM** | Uses crypto_positions, no type filter |
| `wallet_history` | **LOW** | Uses ExchangeOrder, not atoms |
| `wallet_statistics` scoped | **LOW** | Already filters position_type=spot |
