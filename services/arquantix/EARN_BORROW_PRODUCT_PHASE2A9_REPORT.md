# Phase 2A.9 — Earn / Borrow Product Surface V1

## Objectif

Exposer le moteur de lending pool (Phases 2A–2A.8) comme un **produit client** avec des endpoints d'agrégation optimisés pour le frontend Flutter, sans modifier le moteur sous-jacent.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│               Flutter App                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Earn    │  │  Borrow  │  │  Pools   │      │
│  │  Screen  │  │  Screen  │  │  Market  │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
└───────┼──────────────┼─────────────┼─────────────┘
        │              │             │
        ▼              ▼             ▼
┌─────────────────────────────────────────────────┐
│           product_router.py (FastAPI)            │
│  GET /earn/positions                             │
│  GET /borrow/positions                           │
│  GET /pools                                      │
│  GET /dashboard                                  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│           product_surface.py (service)           │
│  get_earn_positions()                            │
│  get_borrow_positions()                          │
│  get_pools_overview()                            │
│  get_earn_borrow_dashboard()                     │
└────────────────────┬────────────────────────────┘
                     │ READ-ONLY
                     ▼
┌─────────────────────────────────────────────────┐
│          Moteur existant (inchangé)              │
│  PositionAtom │ LendingPool │ CryptoPosition    │
│  PoolAllocation │ InterestEngine │ Repayment    │
└─────────────────────────────────────────────────┘
```

---

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `api/services/lending/product_surface.py` | Service d'agrégation (4 fonctions) |
| `api/services/lending/product_router.py` | Router FastAPI (4 endpoints) |
| `api/tests/test_product_surface.py` | 14 tests couvrant tous les cas |

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/lending/__init__.py` | Export `product_router` |
| `api/main.py` | Registration du `lending_product_router` |

---

## Endpoints API

### `GET /api/lending/pools`

Liste des pools actives avec rates, liquidité et utilisation.

```json
{
  "pools": [
    {
      "asset": "USDC",
      "pool_id": "uuid",
      "total_supplied": 3000.00,
      "total_borrowed": 1000.00,
      "available_liquidity": 2000.00,
      "utilization": 33.33,
      "supply_apr": 3.00,
      "borrow_apr": 5.00,
      "effective_apy": 1.00
    }
  ]
}
```

### `GET /api/lending/earn/positions?client_id=uuid`

Vue lender : positions actives + intérêts accumulés + commitments en attente.

```json
{
  "total_earn_value_eur": 1234.56,
  "total_accrued_interest_eur": 12.34,
  "positions_count": 1,
  "positions": [
    {
      "asset": "USDC",
      "supplied": 1000.0,
      "accrued_interest": 2.5,
      "total_value": 1002.5,
      "value_eur": 920.50,
      "accrued_interest_eur": 2.30,
      "apy": 1.5,
      "pool_utilization": 50.0
    }
  ],
  "pending_commitments_count": 0,
  "pending_commitments": []
}
```

### `GET /api/lending/borrow/positions?client_id=uuid`

Vue borrower : emprunts actifs + intérêts dus + total_due.

```json
{
  "total_borrowed_eur": 920.50,
  "total_interest_due_eur": 5.00,
  "total_due_eur": 925.50,
  "positions_count": 1,
  "positions": [
    {
      "borrow_position_id": "uuid",
      "asset": "USDC",
      "borrowed": 1000.0,
      "accrued_interest": 5.5,
      "total_due": 1005.5,
      "value_eur": 925.50,
      "accrued_interest_eur": 5.00,
      "apr": 5.0,
      "created_at": "2027-03-01T12:00:00"
    }
  ]
}
```

### `GET /api/lending/dashboard?client_id=uuid`

Vue combinée pour l'écran principal.

```json
{
  "earn": {
    "total_value_eur": 1234.56,
    "accrued_interest_eur": 12.34,
    "positions_count": 1,
    "pending_commitments_count": 0
  },
  "borrow": {
    "total_borrowed_eur": 920.50,
    "total_interest_due_eur": 5.00,
    "total_due_eur": 925.50,
    "positions_count": 1
  },
  "net_position_eur": 309.06
}
```

---

## Logique métier

### Effective APY (lender)

```
effective_apy = supply_rate × utilization_rate
```

Si `utilization = 0` → `effective_apy = 0` (pas de rendement sans emprunteur).

### Accrued interest (borrower)

Le `total_due` d'un `PoolBorrowPosition` est calculé pro-rata depuis l'atom `borrowing` partagé :

```
share = borrow_position.borrowed_amount / borrowing_atom.quantity
accrued_interest = borrowing_atom.accrued_income × share
total_due = borrowed_amount + accrued_interest
```

### Pending commitments

Les commitments avec `available_amount > 0` sont exposés séparément — ils représentent de la liquidité réservée mais pas encore prêtée.

---

## Invariants respectés

| # | Invariant | Vérifié |
|---|-----------|---------|
| 1 | Aucune mutation — module read-only | ✅ |
| 2 | No fake yield — APY = 0 si utilization = 0 | ✅ |
| 3 | Earn + Spot = Wealth global | ✅ |
| 4 | Positions disparaissent après repay | ✅ |
| 5 | Moteur existant inchangé | ✅ |
| 6 | crypto_positions non touché | ✅ |

---

## Tests

### Résultats

```
14 passed — test_product_surface.py

93 passed — full regression (all lending + product tests)
```

### Couverture

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Pools overview | 2 | ✅ |
| Earn positions (supply + accrued) | 3 | ✅ |
| Borrow positions (borrowed + due) | 2 | ✅ |
| Dashboard (combined) | 2 | ✅ |
| Edge cases (vide, commit-only, zero util) | 3 | ✅ |
| Post-repay (positions disparaissent) | 1 | ✅ |
| Multi-asset (USDC + BTC) | 1 | ✅ |

---

## Mapping Backend → Flutter

| Screen Flutter | Endpoint | Données clés |
|---------------|----------|-------------|
| Earn (liste) | `GET /earn/positions` | supplied, accrued, total_value, apy |
| Borrow (liste) | `GET /borrow/positions` | borrowed, accrued, total_due, apr |
| Pool Market | `GET /pools` | total_supplied, utilization, rates |
| Dashboard | `GET /dashboard` | earn/borrow summary, net_position |
| Supply action | `POST /pool/supply` | (existant) |
| Borrow action | `POST /pool/borrow` | (existant) |
| Repay action | `POST /pool/repay` | (existant) |

---

## Non-régression

93 tests passés incluant toutes les suites précédentes :
- `test_p2p_lending.py` (Phase 2A)
- `test_lending_valuation.py` (Phase 2A.5)
- `test_lending_e2e.py` (Phase 2A.6)
- `test_pool_lending.py` (Phase 2A.6bis)
- `test_pool_interest.py` (Phase 2A.7)
- `test_pool_repayment.py` (Phase 2A.8)
- `test_product_surface.py` (Phase 2A.9)

**Zéro régression.**
