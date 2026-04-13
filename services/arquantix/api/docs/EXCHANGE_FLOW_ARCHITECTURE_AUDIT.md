# Exchange Flow Architecture Audit

**PRD:** Exchange Engine Flow Hardening (EUR → Crypto) — v1.0  
**Date:** 2025-03  
**Scope:** Buy flow, internal transfer, crypto_positions, crypto_settlement_deltas, custody model, settlement.

---

## 1. Current Flow Analysis

### How the buy flow is executed

The EUR → Crypto buy is implemented in **`api/services/exchange/service.py`** (`ExchangeService.buy()`). The flow is **single-phase and atomic** within one DB transaction:

1. **Idempotency** — `exchange_orders` lookup by `external_reference`; duplicate → return `ignored`.
2. **Validation** — Asset in `SUPPORTED_ASSETS`, price resolved (override or market data).
3. **Amounts** — `volume_raw = fiat_amount / price` (quantized), fee from `exchange_fee_config`, `client_crypto = volume_raw - fee_crypto`.
4. **Accounts** — Client EUR account and settlement EUR account resolved via custody repositories; both must exist.
5. **Balance check** — `CustodyBalanceRepository.get_for_update()` on client and settlement (row-level lock); client `available_balance >= fiat_amount` or raise `InsufficientFundsError`.
6. **Order created** — `ExchangeOrder` with `status=processing`, `side=buy`, `amount_to=client_crypto`, `amount_from=fiat_amount`, metadata includes `volume_raw`, `fee_bps`.
7. **Custody transaction** — One `custody_transactions` row: debit client EUR, `transaction_kind=exchange_buy`, `amount=fiat_amount`.
8. **Ledger** — `LedgerEntryService.post_double_entry()`: debit client ledger account, credit settlement ledger account (if both have `ledger_account_id`).
9. **EUR balances** — `CustodyBalanceRepository.update_balance()`: client -= fiat_amount, settlement += fiat_amount.
10. **Crypto position** — `CryptoPositionRepository.get_or_create_for_update()` then `credit(position, client_crypto)` (post-fee amount).
11. **Settlement delta** — `CryptoSettlementDeltaRepository.get_or_create(asset, today)` then `increment(delta, volume_raw)` (raw volume; fees excluded).
12. **Order finalization** — `ExchangeOrder.status = completed`. On any exception after step 6, order is set to `failed` and exception re-raised.

Commit is performed in the **router** (`api/services/exchange/router.py`) after `buy()` returns, so all of the above share one transaction.

**Important:** The EUR move (client → settlement) is **not** implemented as a prior call to the Internal Transfer Engine. It is done **inline** inside `buy()` via custody transaction + ledger + balance updates. There is no separate “Step 1: Internal Transfer” before “Step 2: Exchange Execution” at API level.

---

## 2. Transfer Precondition

**PRD requirement:** *Exchange execution must only happen if internal transfer completed successfully.*

**Current state:**

- The system does **not** require a prior call to `POST /api/internal-transfer` before `POST /api/exchange/buy`.
- The **effect** of a transfer (client EUR debited, settlement EUR credited) is guaranteed only **within** the buy flow: same transaction, same balance checks, same custody/ledger/balance updates. So functionally, “transfer” and “exchange execution” succeed or fail together.
- The **Internal Transfer Engine** (`POST /api/internal-transfer`, `CustodyService.execute_internal_transfer`) exists and is used in tests and potentially by other flows, but the exchange buy does not call it. Tests (e.g. `test_exchange_engine.py`) call `_buy()` directly with no prior internal transfer.

**Conclusion:**  
- **Precondition in spirit:** Yes — the client cannot be debited and settlement credited without the rest of the buy (order, position, delta) being in the same transaction; if balance is insufficient, buy fails and nothing is written.  
- **Precondition as “mandatory separate step”:** No — there is no enforced sequence “internal transfer then exchange”. If the PRD requires that exchange must **only** execute after an explicit, separate internal transfer call, the current design does not satisfy that; it would require refactoring (e.g. buy only credits crypto when it finds sufficient settlement balance and a matching prior transfer, or a two-phase API).

---

## 3. Position Accounting

**PRD requirement:** *`crypto_positions` represents client entitlement only (what the platform owes to the client).*

**Current state:**

- **Table:** `crypto_positions` — `client_id`, `asset`, `balance`, `available_balance`, timestamps. One row per (client, asset).
- **Usage in buy:** Only `CryptoPositionRepository.credit(position, client_crypto)` is called, with `client_crypto = volume_raw - fee_crypto` (post-fee amount). No other source writes to this table in the buy flow.
- **Semantics:** The balance is increased by the amount the client receives; fees are not credited to the client. No “real” custody or Fireblocks balance is written here.

**Conclusion:**  
**Confirmed.** `crypto_positions` is used only as **client economic entitlement** (post-fee). It is not used to store actual custody or settlement wallet balances. Naming and usage are consistent with “client entitlement only”.

---

## 4. Custody Model

**PRD requirement:**  
- **Actual custody balance** — real crypto held (source: Fireblocks), stored e.g. in `crypto_custody_balances.actual_balance`.  
- **Expected balance** — from internal accounting; reconciliation via `expected vs actual`.

**Current state:**

- There are **no** tables `crypto_custody_accounts` or `crypto_custody_balances` in the schema (see `api/services/exchange/models.py` and `alembic/versions/061_add_exchange_engine_tables.py`). Only:
  - `crypto_positions` (client entitlement),
  - `exchange_orders`,
  - `crypto_settlement_deltas`.
- **“Clients pool” and “Settlement wallet”** in the admin UI (`GET /api/admin/exchange/crypto-custody`) are **derived**:
  - **Clients pool** — `CryptoPositionRepository.get_aggregate_balance(db, asset)` = sum of `crypto_positions.balance` for that asset.
  - **Settlement wallet** — `get_settlement_wallet_balance(asset)` from `api/services/exchange/assets.py`, which reads an **in-memory** dict `_settlement_wallet_reserves`. No DB persistence, no Fireblocks integration.
- The reconciliation module (`portfolio_engine/hardening/reconciliation`) uses “expected_balance” vs “actual_balance” in the context of **ledger accounts** (PE ledger), not crypto custody.

**Conclusion:**  
**Gap.** The system does **not** currently:
- Store **actual** crypto custody balances (e.g. from Fireblocks).
- Store **expected** crypto custody balances per wallet/pool.
- Expose a dedicated reconciliation path for “expected vs actual” for crypto custody.

To align with the PRD, the codebase would need at least:
- A notion of **crypto custody accounts** (e.g. clients_pool_btc, settlement_wallet_btc),
- A **crypto_custody_balances** (or equivalent) table with `actual_balance` and `expected_balance`, and a way to refresh `actual_balance` from Fireblocks.

---

## 5. Settlement Model

**PRD requirement:**  
- `crypto_settlement_deltas` represents **pending settlement obligations** (net delivery to/from client pool).  
- Settlement uses **raw volume** (before fees).  
- End-of-day settlement: run job, per asset compute net delta, execute Fireblocks transfer, update actual balance, mark delta settled.

**Current state:**

- **Table:** `crypto_settlement_deltas` — `asset`, `settlement_date`, `delta_amount`, `settled`, timestamps. One row per (asset, settlement_date).
- **Buy flow:** `CryptoSettlementDeltaRepository.get_or_create(asset, today)` then `increment(delta, volume_raw)`. So the **raw** (pre-fee) volume is used; fees are correctly excluded (test `test_settlement_delta_uses_raw_volume`).
- **Settlement job:** `ExchangeService.run_settlement(db, actor)`:
  - Lists unsettled deltas.
  - For each: if `delta_amount == 0`, mark settled; if `delta_amount > 0`, checks **in-memory** `get_settlement_wallet_balance(asset)`; if insufficient → blocked and not settled; if sufficient → mark settled; if `delta_amount < 0`, checks aggregate client positions (sum of `crypto_positions.balance`) and blocks if insufficient, else mark settled.
  - No Fireblocks call, no DB table update for “actual” custody balance; only `settled` is set to true and audit log written.

**Conclusion:**  
- **Delta semantics and raw volume:** Correct — deltas represent net obligation; buy correctly uses `volume_raw`.  
- **Settlement job behaviour:** Partially aligned — it decides what *would* be settled and marks deltas settled, but it does **not**:
  - Execute any real transfer (Fireblocks),
  - Update any persistent “actual” custody balance.

So the **obligation** side is in place; the **custody execution and actual balance** side is missing (and depends on the custody model in section 4).

---

## 6. Architecture Gaps

| PRD element | Status | Notes |
|------------|--------|--------|
| **Three-layer separation** (Client entitlement / Actual custody / Pending settlement) | **Partial** | Entitlement (positions) and pending (deltas) exist; actual custody layer does not. |
| **Internal transfer as mandatory Step 1** | **Not as separate step** | Transfer is inlined in buy(); no API-level “transfer then exchange” sequence. |
| **`crypto_positions` = client entitlement only** | **OK** | Implemented and used that way. |
| **`crypto_custody_accounts`** (e.g. clients_pool, settlement_wallet per asset) | **Missing** | No table or formal entity; only derived views (aggregate positions + in-memory wallet). |
| **`crypto_custody_balances`** (actual_balance, expected_balance, updated_from_provider_at) | **Missing** | No table; settlement wallet is in-memory only. |
| **Settlement delta = raw volume** | **OK** | Implemented and tested. |
| **End-of-day settlement: Fireblocks + update actual_balance** | **Missing** | Job only marks deltas settled; no Fireblocks, no actual balance persistence. |
| **Reconciliation formula** (Expected = Actual + Pending) | **Not possible** | No actual (or expected) custody balance stored; formula cannot be applied. |
| **Atomicity: order + position + delta** | **OK** | Single transaction in buy(); rollback on error. |

---

## 7. Proposed Fixes (minimal to align with PRD)

Constraints: no full refactor, no breaking existing tests, no removal of tables or working flows.

### 7.1 Documentation and semantics (no schema change)

- **Document** in code or ADR that:
  - `crypto_positions` = **client entitlement only** (never real custody).
  - `crypto_settlement_deltas` = **pending settlement obligation**; settlement uses **raw** volume.
- **Document** that the current buy flow performs the EUR transfer **inline** (no mandatory prior call to Internal Transfer). If product requires “internal transfer then exchange” as two calls, that is a separate design decision and change.

### 7.2 Optional: Two-phase flow (if product requires it)

- If “transfer precondition” must be an explicit previous step:
  - Option A: Introduce a “pre-funded” flow: client first calls `POST /api/internal-transfer`; then calls a new endpoint (e.g. `POST /api/exchange/buy-from-settlement`) that only checks settlement balance and creates order + position + delta (no EUR movement). Requires clear idempotency and reference linking.
  - Option B: Keep current single-phase buy but document that “transfer” is the first part of the same transaction (current behaviour).

### 7.3 Custody layer (for Fireblocks and reconciliation)

- **Add** (when ready for Fireblocks):
  - **`crypto_custody_accounts`** — e.g. one row per (asset, account_type) with `account_type` in `clients_pool` / `settlement_wallet`, plus identifiers for Fireblocks.
  - **`crypto_custody_balances`** — `account_id`, `asset`, `actual_balance`, `expected_balance`, `updated_from_provider_at`, `updated_at`.  
    - `actual_balance`: updated from Fireblocks (or from existing in-memory logic in v1).  
    - `expected_balance`: computed from internal accounting (e.g. prior expected + settlement deltas or equivalent).
- **Settlement job** (later): when marking a delta settled, (1) call Fireblocks to perform the transfer, (2) refresh `actual_balance` from provider, (3) optionally update `expected_balance` so that reconciliation (Expected = Actual + Pending) can be checked.

### 7.4 Persist settlement wallet balance (small step)

- Replace or back the in-memory `_settlement_wallet_reserves` with a **DB-backed** value (e.g. a single table or key-value by asset) so that:
  - Balance survives restarts.
  - It can later be replaced by “actual” balance from Fireblocks and aligned with `crypto_custody_balances` when that exists.

### 7.5 Reconciliation and admin UI

- Once `crypto_custody_balances` (or equivalent) exists:
  - Add a small reconciliation check or report: for each asset, compare `sum(crypto_positions.balance)` (entitlement) vs clients_pool `expected_balance` vs `actual_balance` and pending deltas (e.g. Expected = Actual + Pending).
  - Admin “crypto custody” UI can then show actual vs expected and highlight mismatches.

---

## Summary

- **Buy flow:** Single-phase, atomic; EUR transfer is done inside buy(), not via a prior Internal Transfer call. Order, custody tx, ledger, balances, position, and delta are updated in one transaction. Position uses post-fee amount; delta uses raw volume.  
- **Transfer precondition:** Satisfied “by construction” (same transaction); not satisfied as “mandatory separate internal transfer call”.  
- **Position accounting:** `crypto_positions` is client entitlement only; no mixing with custody.  
- **Custody model:** No `crypto_custody_accounts` / `crypto_custody_balances`; no actual vs expected balance; settlement wallet is in-memory only.  
- **Settlement model:** Deltas and raw volume are correct; settlement job does not call Fireblocks or persist actual balance.  
- **Gaps:** Explicit custody layer (accounts + balances, actual/expected), Fireblocks integration, and reconciliation formula support are missing.  
- **Proposed minimal steps:** Document current semantics; optionally persist settlement wallet in DB; when ready, add custody accounts/balances and wire Fireblocks and reconciliation.

This audit provides the basis for implementing the PRD’s three-layer separation and readiness for SELL and Fireblocks without refactoring the existing buy flow more than necessary.
