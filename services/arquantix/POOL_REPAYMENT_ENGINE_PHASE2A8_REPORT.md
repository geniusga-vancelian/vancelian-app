# Pool Repayment & Settlement Engine — Phase 2A.8 Report

## Cycle crédit complet

```
Supply → Borrow → Accrue → REPAY
  ✅       ✅       ✅      ✅ (this phase)
```

---

## Architecture

```
POST /api/lending/pool/repay
  │
  ▼
┌─────────────────────────────────────────────┐
│           RepaymentEngine                   │
│  repay_borrow_position(borrow_position_id)  │
└─────────────┬───────────────────────────────┘
              │
    ┌─────────┼──────────────┐
    ▼         ▼              ▼
 Compute    Split          Settle
 total_due  interest       positions
    │         │              │
    ▼         ▼              ▼
 principal  to_lenders    close atoms
 + accrued  + platform    update pool
```

---

## Flux de remboursement (transaction atomique)

### Input

```json
{ "borrow_position_id": "uuid" }
```

### Étapes

```
1. Fetch borrow_position → verify status == "active"
2. Compute:
   principal = borrow_position.borrowed_amount
   accrued   = borrowing_atom.accrued_income × (principal / atom.quantity)
   total_due = principal + accrued

3. Verify: borrower.balance >= total_due
4. Debit borrower spot: balance -= total_due

5. Interest split:
   interest_to_lenders = accrued × (supply_rate / borrow_rate)
   platform_fee        = accrued - interest_to_lenders

6. For each allocation:
   lender_principal = allocation.amount
   lender_interest  = interest_to_lenders × (allocation / principal)
   → credit lender: balance += lender_principal + lender_interest
   → reduce lending_atom (close if qty → 0)

7. Reduce borrowing_atom (close if qty → 0)
8. Mark borrow_position.status = "repaid"
9. Update pool stats (total_borrowed, utilization_rate)
```

---

## Exemple chiffré

```
Setup:
  Lender A commits 600 USDC
  Lender B commits 400 USDC
  Borrower takes 1000 USDC from pool
  Pool rates: borrow=500bps (5%), supply=300bps (3%)

After 10 days of accrual:
  daily_borrow = 500/10000/365 = 0.000136986
  accrued_interest = 1000 × 0.000136986 × 10 = 1.36986 USDC

Repayment:
  total_due = 1000 + 1.36986 = 1001.36986 USDC

  Interest split:
    interest_to_lenders = 1.36986 × 300/500 = 0.82191 USDC
    platform_fee        = 1.36986 - 0.82191 = 0.54794 USDC

  Lender A (60%):
    principal = 600
    interest  = 0.82191 × 0.60 = 0.49315
    total     = 600.49315 USDC

  Lender B (40%):
    principal = 400
    interest  = 0.82191 × 0.40 = 0.32877
    total     = 400.32877 USDC

Verification:
  1001.36986 = 600.49315 + 400.32877 + 0.54794 ✅
```

---

## Gestion des PositionAtom partagés

Les `PositionAtom` sont mergés (un seul atom par portfolio+instrument) grâce à la contrainte unique `ix_pe_position_atoms_unique_open`. Un emprunteur ayant plusieurs borrows actifs n'a qu'un seul borrowing atom.

**Solution : pro-rata**

```
Si borrowing_atom.quantity = 3000 et borrow_position.borrowed_amount = 1000:
  share = 1000 / 3000 = 33.3%
  borrower_interest = atom.accrued_income × 33.3%
  → atom.quantity -= 1000
  → atom.accrued_income -= interest portion
  → atom stays open if quantity > 0
```

---

## Invariants respectés

| # | Invariant | Vérifié |
|---|---|---|
| 1 | Conservation: borrower_paid = lenders + fee | ✅ `TestRepaymentConservation` |
| 2 | Symétrie: lending == borrowing == 0 post-repay | ✅ `TestPositionClosure` |
| 3 | No active allocations post-repay | ✅ `TestPositionClosure` |
| 4 | Pool total_borrowed accurate | ✅ `TestPoolStateAfterRepay` |
| 5 | Idempotent (no double repay) | ✅ `TestDoubleRepay` |
| 6 | Wealth clean post-repay | ✅ `TestWealthAfterRepay` |

---

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/lending/pool/repay` | Full repayment d'un borrow position |

Response :

```json
{
  "borrow_position_id": "uuid",
  "asset": "USDC",
  "principal": 1000.0,
  "accrued_interest": 1.37,
  "total_paid": 1001.37,
  "interest_to_lenders": 0.82,
  "platform_fee": 0.55,
  "lenders_settled": 2,
  "lender_details": [
    { "client_id": "...", "principal_returned": 600, "interest_earned": 0.49, "total_received": 600.49 },
    { "client_id": "...", "principal_returned": 400, "interest_earned": 0.33, "total_received": 400.33 }
  ],
  "pool_total_borrowed_after": 0.0
}
```

---

## Tests (13/13 passed)

### A. Full Repayment (3 tests)
- Repay with accrued interest
- Lender receives principal + interest
- Borrower balance decreases by total_due

### B. Multi-lender Settlement (1 test)
- Pro-rata distribution (60/40 split verified)

### C. Conservation (1 test)
- borrower_paid == sum(lender_received) + platform_fee

### D. Position Closure (2 tests)
- Lending + borrowing atoms → status "closed"
- PoolBorrowPosition → status "repaid"

### E. Insufficient Balance (1 test)
- Reject if borrower can't cover total_due

### F. Double Repay (1 test)
- Second repay → error "not active"

### G. No Interest (1 test)
- Immediate repay → 0 interest, exact principal returned

### H. Pool State (2 tests)
- total_borrowed drops to 0
- utilization_rate decreases

### I. Wealth View (1 test)
- 0 lending/borrowing in wealth after repay

---

## Non-régression complète

```
79 passed (p2p_lending + valuation + e2e + pool + interest + repayment)
```

---

## Fichiers créés/modifiés

| Fichier | Action |
|---|---|
| `api/services/lending/repayment_engine.py` | Créé — RepaymentEngine |
| `api/services/lending/pool_router.py` | Modifié — ajout endpoint repay |
| `api/tests/test_pool_repayment.py` | Créé — 13 tests |

---

## Cycle crédit complet — récapitulatif

| Phase | Feature | Status |
|---|---|---|
| 2A | Loan direct (P2P) | ✅ |
| 2A.5 | Valuation layer (wealth view) | ✅ |
| 2A.6 | E2E product surface | ✅ |
| 2A.6bis | Pool-based lending | ✅ |
| 2A.7 | Interest engine (daily accrual) | ✅ |
| **2A.8** | **Repayment & settlement** | **✅** |

Le cycle supply → borrow → accrue → repay est fermé.

---

## Next: Phase 2B

→ Collateral + Risk Engine (LTV monitoring, margin calls, liquidation)
