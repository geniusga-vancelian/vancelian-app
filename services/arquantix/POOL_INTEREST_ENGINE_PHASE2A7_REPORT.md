# Pool Interest Engine — Phase 2A.7 Report

## Architecture

```
         ┌─────────────────────────────────────┐
         │      Daily Accrual Engine           │
         │  run_daily_interest_accrual()       │
         └──────────┬──────────────────────────┘
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
   Snapshot    Lender Dist.    Borrower Accrual
   (audit)     (pro-rata)      (per position)
        │           │               │
        ▼           ▼               ▼
 pool_interest   lender_interest  borrower_interest
 _snapshots      _accruals        _accruals
                    │               │
                    └───────┬───────┘
                            ▼
                   PositionAtom.accrued_income
                            │
                            ▼
                    Wealth View (V2)
              value = (qty + accrued) × price
```

---

## Formules

### Taux journaliers

```
daily_borrow_rate = borrow_rate_bps / 10_000 / 365
daily_supply_rate = supply_rate_bps / 10_000 / 365
```

### Intérêts générés (par pool, par jour)

```
interest_generated    = total_borrowed × daily_borrow_rate
interest_to_lenders   = total_borrowed × daily_supply_rate
platform_fee          = interest_generated - interest_to_lenders
```

### Distribution lenders (pro-rata)

```
lender_share    = lender_allocated_amount / total_borrowed
lender_interest = interest_to_lenders × lender_share
```

### Intérêt emprunteur

```
borrower_interest = borrowed_amount × daily_borrow_rate
```

---

## Exemple chiffré

```
Pool USDC:
  total_borrowed = 10,000 USDC
  borrow_rate    = 500 bps (5.00% APR)
  supply_rate    = 300 bps (3.00% APR)
  spread         = 200 bps (2.00% — platform revenue)

Jour 1:
  daily_borrow = 500 / 10000 / 365 = 0.0001369863...
  daily_supply = 300 / 10000 / 365 = 0.0000821917...

  interest_generated  = 10,000 × 0.0001369863 = 1.3698630137 USDC
  interest_to_lenders = 10,000 × 0.0000821917 = 0.8219178082 USDC
  platform_fee        = 0.5479452055 USDC

  Lender A (allocated 6,000 / 10,000 = 60%):
    interest = 0.8219178082 × 0.60 = 0.4931506849 USDC

  Lender B (allocated 4,000 / 10,000 = 40%):
    interest = 0.8219178082 × 0.40 = 0.3287671233 USDC

  Annualisé:
    Borrower pays: 10,000 × 5.00% = 500 USDC/an
    Lenders earn:  10,000 × 3.00% = 300 USDC/an
    Platform:      10,000 × 2.00% = 200 USDC/an
```

---

## Modèle de données

### Colonnes ajoutées à `lending_pools`

| Colonne | Type | Default | Description |
|---|---|---|---|
| `borrow_rate_bps` | NUMERIC(10,2) | 500 | Taux emprunteur APR en bps |
| `supply_rate_bps` | NUMERIC(10,2) | 300 | Taux prêteur APR en bps |

### 3 nouvelles tables

| Table | Clé unique | Rôle |
|---|---|---|
| `pool_interest_snapshots` | (pool_id, date) | Snapshot journalier agrégé |
| `lender_interest_accruals` | (client_id, pool_id, date) | Intérêt quotidien par lender |
| `borrower_interest_accruals` | (client_id, pool_id, date) | Intérêt quotidien par borrower |

Les clés uniques composites empêchent le double accrual (idempotence).

---

## Impact valuation

### Avant Phase 2A.7

```
lending_value  =  quantity × spot_price
borrowing_value = -quantity × spot_price
```

### Après Phase 2A.7

```
lending_value  =  (quantity + accrued_income) × spot_price
borrowing_value = -(quantity + accrued_income) × spot_price
```

Le champ `PositionAtom.accrued_income` (déjà existant dans le schéma) est incrémenté à chaque accrual journalier.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/lending/interest/run-accrual` | Exécuter l'accrual journalier (idempotent) |
| GET | `/api/lending/interest/snapshots/{asset}` | Historique des snapshots (30j max) |
| GET | `/api/lending/interest/accrued` | Total intérêts accumulés par client |
| PUT | `/api/lending/interest/rates/{asset}` | Modifier les taux d'un pool |

---

## Invariants respectés

| # | Invariant | Vérifié |
|---|---|---|
| 1 | No fake yield (borrowed=0 → interest=0) | ✅ `TestNoBorrow` |
| 2 | Conservation: generated = to_lenders + fee | ✅ `TestConservation` |
| 3 | Allocation-only: intérêt basé sur allocations réelles | ✅ `TestMultiLenderProRata` |
| 4 | Deterministic: même input → même output | ✅ `TestDoubleAccrual` (idempotent) |
| 5 | Interest ≥ 0 | ✅ `TestRounding` |
| 6 | Borrower interest = interest_generated | ✅ `TestConservation` |

---

## Tests (15/15 passed)

### A. No Borrow (2 tests)
- Pas d'intérêt sans emprunt
- Pas de rows accrual créées

### B. Single Lender/Borrower (3 tests)
- Calcul exact avec formules vérifiées
- Lender reçoit 100% du supply interest
- Snapshot créé correctement

### C. Multi-lender Pro-rata (1 test)
- 3 lenders, distribution 25%/50%/25% vérifiée

### D. Multi-borrower (1 test)
- Intérêts proportionnels aux montants empruntés

### E. Conservation (2 tests)
- generated = to_lenders + fee (précision 10^-10)
- borrower_due = generated

### F. Double Accrual (2 tests)
- Idempotent (même date → skip)
- Dates différentes → cumul correct

### G. Rounding (1 test)
- Petits montants → intérêts ≥ 0

### H. Valuation Impact (2 tests)
- `accrued_income` > 0 sur PositionAtom après accrual
- Wealth view augmente après accrual

### I. Rate Update (1 test)
- Doubler les taux double les intérêts

---

## Non-régression complète

```
66 passed (test_p2p_lending + test_lending_valuation + test_lending_e2e + test_pool_lending + test_pool_interest)
```

---

## Fichiers créés/modifiés

| Fichier | Action |
|---|---|
| `api/services/lending/interest_models.py` | Créé — 3 modèles |
| `api/services/lending/interest_engine.py` | Créé — InterestEngine |
| `api/services/lending/interest_router.py` | Créé — 4 endpoints |
| `api/services/lending/pool_models.py` | Modifié — ajout borrow/supply_rate_bps |
| `api/services/lending/valuation.py` | Modifié — accrued_income dans calculs |
| `api/services/lending/__init__.py` | Modifié — export interest_router |
| `api/main.py` | Modifié — register interest router |
| `api/services/financial_reset/reset.py` | Modifié — 3 tables ajoutées |
| `api/alembic/versions/074_add_pool_interest_engine.py` | Créé — migration |
| `api/tests/test_pool_interest.py` | Créé — 15 tests |

---

## Next: Phase 2B

→ Collateral + Risk Engine (liquidation, margin calls, LTV monitoring)
