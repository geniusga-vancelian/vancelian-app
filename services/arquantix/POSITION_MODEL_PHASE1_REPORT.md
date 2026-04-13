# Position Model Phase 1 — Report

## Objective

Formalize the position model so that the system becomes **SPOT-COMPATIBLE + EXTENSIBLE** without changing current behavior. All existing flows must continue to produce only `spot` and `cash` atoms. Future position types (lending, staking, borrowing, collateral) are defined in the enum but blocked by guards.

## Changes

### 1. Centralized `PositionType` enum

**File**: `api/services/portfolio_engine/positions/enums.py`

Replaced the original 10-member enum (SPOT, STAKED, COLLATERAL, DEBT, VAULT, PRIVATE_DEAL, REWARD, FEE, OPTION, DERIVATIVE) with a clean, forward-compatible enum:

```python
class PositionType(str, Enum):
    SPOT = "spot"
    CASH = "cash"
    # Phase 2+ — defined for forward-compatibility, NOT to be used yet.
    LENDING = "lending"
    STAKING = "staking"
    BORROWING = "borrowing"
    COLLATERAL = "collateral"

ALLOWED_POSITION_TYPES = frozenset({PositionType.SPOT, PositionType.CASH})
```

Key decisions:
- `CASH` was missing — now explicit (used by bundle cash legs)
- Future types are declared but guards prevent their use
- `ALLOWED_POSITION_TYPES` is the single source of truth for what's currently allowed

### 2. Replaced local constants with enum imports

| File | Before | After |
|------|--------|-------|
| `direct_overlay.py` | `POSITION_TYPE_SPOT = "spot"` | `POSITION_TYPE_SPOT = PositionType.SPOT` |
| `bundles/orchestrator.py` | `POSITION_TYPE_CASH = "cash"` / `POSITION_TYPE_SPOT = "spot"` | Both use `PositionType.CASH` / `PositionType.SPOT` |
| `bundles/rebalance.py` | Imports from `orchestrator` | No change needed — inherits from orchestrator |
| `positions/service.py` | `"spot"` string literal in `_apply_buy` | `PositionType.SPOT` |

### 3. Validation guards

Guards are implemented at two layers:

**Repository layer** (`positions/repository.py`) — last defense:
- `create()`: validates `position_type` is in `ALLOWED_POSITION_TYPES`
- `update()`: validates `position_type` if present in update data

**Service layer** (`positions/service.py`) — business validation:
- `create_position()`: validates before reference checks
- `update_position()`: validates before delegation to repository

All guards raise `ValueError` with descriptive message.

### 4. Pydantic schemas

`PositionCreate.position_type` and `PositionUpdate.position_type` already reference the `PositionType` enum — they now inherit `CASH` and future types automatically. Business-level restriction to `spot`/`cash` is enforced by guards, not by schema.

### 5. Test adaptation

`test_portfolio_engine_positions.py::test_create_position_with_parent`: changed `position_type="collateral"` to `"spot"` since this test verifies parent position linkage, not position types.

## Invariants

| ID | Rule | Enforced by |
|----|------|------------|
| A | All existing flows only produce `spot` or `cash` atoms | Guards in repository + service |
| B | `crypto_positions = Σ atoms WHERE position_type = "spot"` | Direct overlay + bundle orchestrator |
| C | Valuation is spot-only | No change needed (inherent) |
| D | History/statistics are spot-only | No change needed (inherent) |
| F | `direct_atoms + bundle_atoms ≈ crypto_positions` | Tested explicitly |

## Tests

### New test files

| File | Tests | Purpose |
|------|-------|---------|
| `test_position_type_spot_only.py` | 9 tests | Verify all flows produce only spot/cash |
| `test_reject_non_spot_positions.py` | 20 tests | Verify guards reject non-allowed types |

### `test_position_type_spot_only.py` — 9/9 PASSED

- `TestSyncDirectAtomBuy::test_creates_spot_atom` — sync_direct_atom creates type=spot
- `TestSyncDirectAtomBuy::test_updates_existing_spot_atom` — update preserves type=spot
- `TestSyncDirectAtomSell::test_sell_keeps_spot_type` — negative delta preserves type=spot
- `TestBundleCashLeg::test_cash_leg_creates_cash_atom` — _credit_cash_leg creates type=cash
- `TestBundleCashLeg::test_cash_leg_updates_existing` — update preserves type=cash
- `TestBundleSpotPosition::test_sync_pe_position_creates_spot` — _sync_pe_position creates type=spot
- `TestBackfillDirectAtoms::test_backfill_creates_only_spot` — all backfilled atoms are spot
- `TestServiceApplyBuySpot::test_apply_buy_creates_spot` — _apply_buy creates type=spot
- `TestInvariantF::test_direct_plus_bundle_equals_crypto` — direct + bundle = total

### `test_reject_non_spot_positions.py` — 20/20 PASSED

- 8 parametrized tests for repository.create() rejection (lending, staking, borrowing, collateral, foo_bar, SPOT, Spot, empty)
- 2 tests for repository.create() allowing spot and cash
- 2 tests for repository.update() (rejection + passthrough)
- 4 tests for service.create_position() rejection (lending, staking, borrowing, collateral)
- 2 tests for service.create_position() allowing spot and cash
- 2 tests for service.update_position() (rejection + allowed)

### Regression — 0 regressions introduced

| Test suite | Result | Notes |
|-----------|--------|-------|
| `test_bundle_orchestrator.py` | 15/15 PASSED | Bundle invest + rebalance unaffected |
| `test_exchange_engine.py` | 12/14 PASSED, 2 FAILED (pre-existing) | Pre-existing failures unrelated to position_type |
| `test_exchange_sell.py` | 5/6 PASSED, 1 FAILED (pre-existing) | Pre-existing failure unrelated to position_type |
| `test_swap_crypto.py` | 6/6 PASSED | Swap flows unaffected |
| `test_price_alert_cross_logic.py` | 20/20 PASSED | Alert engine unaffected |
| `test_auto_execution_engine.py` | 26/26 PASSED | Auto-execution unaffected |
| `test_auto_execution_concurrency.py` | 7/7 PASSED | Concurrency logic unaffected |
| `test_auto_execution_resilience.py` | 23/23 PASSED | Resilience logic unaffected |

## Files modified

| File | Nature |
|------|--------|
| `positions/enums.py` | Enum refactored + `ALLOWED_POSITION_TYPES` |
| `positions/repository.py` | Guard in `create()` and `update()` |
| `positions/service.py` | Guard in `create_position()`, `update_position()`, enum import |
| `direct_overlay.py` | Local constant replaced by enum import |
| `bundles/orchestrator.py` | Local constants replaced by enum imports |
| `tests/test_portfolio_engine_positions.py` | Fixed position_type in parent test |
| `tests/test_position_type_spot_only.py` | **New** — 9 tests |
| `tests/test_reject_non_spot_positions.py` | **New** — 20 tests |

## What was NOT modified

- Trading flows (exchange service, buy/sell/swap)
- Custody/ledger
- Valuation engine
- Wallet history/statistics
- Bundle invest/rebalance logic (only constant source changed)
- Admin/backoffice
- UI (Flutter/Next.js)
- Database schema (no migration needed — `position_type` is `String(50)`)

## Ready for Phase 2

The system is now prepared for future extension:
1. `PositionType` enum already contains `LENDING`, `STAKING`, `BORROWING`, `COLLATERAL`
2. To enable a new type, add it to `ALLOWED_POSITION_TYPES`
3. Guards will automatically allow the new type through repository and service layers
4. Valuation, history, and statistics will need specific handling for non-spot types
