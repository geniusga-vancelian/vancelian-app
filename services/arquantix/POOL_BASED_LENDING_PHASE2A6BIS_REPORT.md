# Pool-based P2P Lending — Phase 2A.6bis Report

## Architecture

```
Lenders ──supply──→ POOL ←──borrow── Borrowers
              │                  │
              │   FIFO alloc     │
              ▼                  ▼
        lending atoms      borrowing atom
        (per lender)       (per borrower)
```

**Pivot:** du modèle `1 lender ↔ 1 borrower` (loan direct) vers `lenders → POOL ← borrowers`.

Le modèle Phase 2A (loan direct) est **conservé intact** — le pool est une couche additionnelle.

---

## Modèle de données

### 4 nouvelles tables

| Table | Rôle |
|---|---|
| `lending_pools` | 1 pool par asset (auto-créée) |
| `pool_supply_commitments` | Engagement lender — réservation spot |
| `pool_borrow_positions` | Position emprunteur active |
| `pool_allocations` | Audit trail: qui finance qui (FIFO) |

### Concept clé: Supply Commitment

```
AVANT borrow:
  lender.balance      = 5000 (inchangé)
  lender.available    = 2000 (réservé 3000)
  lending positions   = 0

APRÈS borrow (3000):
  lender.balance      = 2000 (débité)
  lender.available    = 2000
  lending positions   = 3000
```

Fonds restent en spot mais `available_balance` réduit → pas d'utilisation pour trading.

---

## Flux métier

### 1. Supply Commitment (Lender)
```
POST /api/lending/pool/supply
{ "client_id": "...", "asset": "USDC", "amount": 3000 }

→ funds stay in spot
→ available_balance -= 3000
→ commitment.status = "active"
→ NO lending position yet
```

### 2. Borrow from Pool (Borrower)
```
POST /api/lending/pool/borrow
{ "client_id": "...", "asset": "USDC", "amount": 2500 }

Transaction atomique:
  1. Sélection commitments disponibles (FIFO par created_at)
  2. Allocation répartie:
     - L1: 1000 (fully_used)
     - L2: 1000 (fully_used)
     - L3: 500  (partially_used)
  3. Débit spot lenders (balance -= alloc)
  4. Crédit spot borrower (balance += 2500)
  5. Création lending atoms (1 par lender, ou merge si existant)
  6. Création borrowing atom (1 par borrower, ou merge si existant)
  7. Audit trail (pool_allocations)
  8. Update pool stats (utilization_rate)
```

### 3. Annulation (si non utilisé)
```
DELETE /api/lending/pool/supply/{commitment_id}
→ available_balance restauré
→ commitment.status = "cancelled"
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/lending/pool/supply` | Lender commit liquidity |
| POST | `/api/lending/pool/borrow` | Borrower takes from pool |
| DELETE | `/api/lending/pool/supply/{id}` | Cancel unused commitment |
| GET | `/api/lending/pool/status/{asset}` | Pool stats + utilization |
| GET | `/api/lending/pool/commitments` | List commitments (by client/asset) |
| GET | `/api/lending/pool/borrows` | List borrow positions |

---

## Invariants respectés

| # | Invariant | Vérifié |
|---|---|---|
| 1 | Pas de rendement sans borrow | ✅ Commitment seul = 0 lending positions |
| 2 | Conservation: total_spot constant | ✅ Test `test_conservation_total_assets` |
| 3 | Séparation: commitment ≠ lending ≠ spot | ✅ Tests séparation |
| 4 | Allocation traçable (FIFO) | ✅ `pool_allocations` + test audit trail |
| 5 | Symétrie: Σ lending == Σ borrowing | ✅ Test `test_position_symmetry` |

---

## Intégration Wealth View

Les positions `lending` et `borrowing` créées par le pool sont identiques aux atoms Phase 2A → **aucune modification** de la valuation Phase 2A.5 nécessaire.

```
GET /api/app/portfolio/wealth?client_id=...
→ spot + lending - borrowing = net_value
```

---

## Tests (22/22 passed)

### A. Supply Commitment (5 tests)
- Création OK
- Réservation available_balance
- Rejet si balance insuffisante
- Pas de lending position avant borrow
- Annulation libère balance

### B. Borrow from Pool (3 tests)
- Single lender full borrow
- Création positions lending + borrowing
- Mise à jour status commitment (fully_used)

### C. Partial Allocation (2 tests)
- Multi-lender FIFO (3 lenders, allocation 1000/1000/500)
- Audit trail (pool_allocations) correct

### D. Invariants (3 tests)
- Conservation total assets
- Symétrie lending == borrowing
- Pool stats accuracy (utilization_rate = 40%)

### E. Edge Cases (4 tests)
- Borrow > liquidity → rejeté
- Self-borrow → exclu (commitment propre filtrée)
- Cancel commitment fully_used → rejeté
- Sequential borrows → pool dépletée correctement

### F. Wealth Integration (3 tests)
- Lender wealth: lending apparaît
- Borrower wealth: spot + borrowing
- No borrow = no positions

### G. Non-Regression (2 tests)
- crypto_positions inchangé par commitment
- Multi-asset pools isolés

---

## Non-régression complète

```
51 passed (test_p2p_lending + test_lending_valuation + test_lending_e2e + test_pool_lending)
```

Phase 2A (loan direct) + Phase 2A.5 (valuation) + Phase 2A.6 (E2E) = **inchangés**.

---

## Fichiers créés/modifiés

| Fichier | Action |
|---|---|
| `api/services/lending/pool_models.py` | Créé — 4 modèles SQLAlchemy |
| `api/services/lending/pool_service.py` | Créé — PoolLendingService |
| `api/services/lending/pool_router.py` | Créé — 6 endpoints API |
| `api/services/lending/__init__.py` | Modifié — export pool_router |
| `api/main.py` | Modifié — register pool router |
| `api/services/financial_reset/reset.py` | Modifié — 4 tables ajoutées au reset |
| `api/alembic/versions/073_add_lending_pool_tables.py` | Créé — migration |
| `api/tests/test_pool_lending.py` | Créé — 22 tests |

---

## Design Decisions

1. **Soft Pool:** Les fonds restent en spot jusqu'au borrow réel → pas de risque custody pendant l'attente
2. **FIFO Allocation:** Priorité temporelle simple et prévisible
3. **Atom Merge:** Si un lender a déjà un atom ouvert pour le même instrument, on agrège la quantité au lieu de créer un doublon (contrainte unique `ix_pe_position_atoms_unique_open`)
4. **Auto-provisioning Pool:** Un pool est créé automatiquement par asset au premier commitment
5. **Self-borrow excluded:** Les commitments d'un client sont filtrés de ses propres borrows

---

## Next: Phase 2A.7

→ Intérêts dynamiques pool-based (taux fonction de l'utilization_rate)
