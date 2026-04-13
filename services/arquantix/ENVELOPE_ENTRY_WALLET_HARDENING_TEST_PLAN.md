# Envelope Entry Wallet — Hardening Test Plan

## Architecture Recap

Phase 2A.16 introduces an **Investment Envelope** abstraction that encapsulates:
- Currency conversion (EUR→USDC, BTC→USDC)
- Fee tracking
- Pool allocation

**Key flow:**
```
User Wallet → ExchangeService.buy/swap() → crypto_positions credited
  → PoolService.create_supply_commitment() → available_balance reduced
  → [NEW] Envelope debit → crypto_positions.balance debited (neutralization)
  → [NEW] Envelope entry created (full audit trail)
```

**Tables:**
- `investment_envelopes` — one per investment operation
- `investment_envelope_entries` — detailed entry (amounts, fx, fees, commitment link)

---

## Business Invariants

| ID | Invariant | Risk Level |
|----|-----------|------------|
| INV-01 | After conversion invest, `crypto_positions.balance` net change = 0 | CRITICAL |
| INV-02 | `available_balance` correctly reflects committed funds | CRITICAL |
| INV-03 | Envelope `net_allocated` = commitment `amount` | CRITICAL |
| INV-04 | No artificial value creation: total wealth before = total wealth after | CRITICAL |
| INV-05 | Envelope debit ONLY occurs on conversion (buy/swap), NOT direct invest | HIGH |
| INV-06 | Direct USDC invest: `balance` decreases by 0, `available_balance` decreases by amount | HIGH |
| INV-07 | Envelope `entry_amount` matches original funding amount | MEDIUM |
| INV-08 | `conversion_type` matches actual conversion path | MEDIUM |
| INV-09 | `fx_rate` stored when conversion occurs, NULL when direct | MEDIUM |
| INV-10 | `commitment_id` on entry links to actual PoolSupplyCommitment | MEDIUM |
| INV-11 | Placements show committed funds, Crypto shows only free funds | CRITICAL |
| INV-12 | Concurrent invests do not create duplicate commitments | HIGH |
| INV-13 | Failed invest rolls back ALL changes (no orphan envelope/commitment) | CRITICAL |
| INV-14 | Rounding does not create or destroy value | HIGH |

---

## Test Scenario Matrix

| Family | File | Scenarios | Invariants Covered |
|--------|------|-----------|-------------------|
| Accounting | `test_envelope_accounting_invariants.py` | EUR→USDC, BTC→USDC, USDC direct | INV-01..07, INV-11 |
| Zero Pollution | `test_envelope_zero_wallet_pollution.py` | Intermediate credit invisible, display uses available_balance | INV-01, INV-05, INV-06, INV-11 |
| Data Integrity | `test_envelope_data_integrity.py` | All envelope fields correct, API↔DB consistency | INV-07..10 |
| Failure/Rollback | `test_envelope_failure_rollback.py` | Supply fails, envelope fails, DB error mid-flow | INV-13 |
| Concurrency | `test_envelope_concurrency.py` | Double tap, simultaneous invests, cap race | INV-12 |
| Cross-Surface | `test_envelope_cross_surface_consistency.py` | Dashboard, crypto, placements coherence | INV-04, INV-11 |
| Backward Compat | `test_envelope_backward_compatibility.py` | Old invests, direct USDC, lending operations | INV-05, INV-06 |
| Precision | `test_envelope_precision_rounding.py` | Small amounts, many decimals, near-peg | INV-14 |

---

## Risks Covered

- **Double counting**: Converted USDC appearing in both Crypto and Placements
- **Orphan records**: Envelope without commitment, commitment without envelope
- **Balance drift**: Rounding differences causing value leak
- **Concurrency bugs**: Race conditions on pool cap, double commitments
- **Rollback failures**: Partial state left after error mid-flow
- **Backward incompatibility**: Old investments breaking with new code

## Residual Risks

- **External exchange rate volatility** between preview and execution (by design, not a bug)
- **Database connection loss** during atomic transaction (handled by DB-level rollback)
- **Settlement reconciliation** with real exchange providers (out of scope — simulated environment)
- **Multi-region replication lag** (not applicable to current single-node deployment)
