# P2P Internal Lending Engine — Phase 2A Report

## Date: 2026-03-21

---

## 1. Objectif

Implémenter un système de prêt P2P interne (internal lending) permettant à un client de prêter un crypto-actif (BTC, ETH, USDC…) à un autre client de la plateforme, via un transfert interne avec suivi complet des positions et du ledger.

---

## 2. Architecture

### Flux principal

```
Lender A (spot)
→ perd spot (crypto_positions -principal)
→ gagne lending_position (pe_position_atoms, type="lending")

Borrower B
→ gagne spot (crypto_positions +principal)
→ gagne borrowing_position (pe_position_atoms, type="borrowing")
```

### Lifecycle du prêt

```
PENDING → ACCEPTED → ACTIVE → REPAID
         ↘ REJECTED    ↘ DEFAULT
  ↘ CANCELLED
```

---

## 3. Fichiers créés

| Fichier | Description |
|---------|-------------|
| `api/services/lending/__init__.py` | Module P2P lending |
| `api/services/lending/enums.py` | `LoanStatus`, transitions valides |
| `api/services/lending/models.py` | Tables `loans`, `loan_interest_accruals` |
| `api/services/lending/schemas.py` | Schémas Pydantic (request/response) |
| `api/services/lending/service.py` | `LendingService` — logique métier complète |
| `api/services/lending/router.py` | 9 endpoints REST (`/api/lending/loans/*`) |
| `api/alembic/versions/072_add_loans_table.py` | Migration Alembic |
| `api/tests/test_p2p_lending.py` | 11 tests (lifecycle, invariants, edge cases) |

---

## 4. Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/portfolio_engine/positions/enums.py` | `ALLOWED_POSITION_TYPES` étendu avec `lending`, `borrowing` |
| `api/services/portfolio_engine/valuation.py` | `_compute_atoms_value` exclut les positions non-spot |
| `api/main.py` | Router lending enregistré |
| `api/services/financial_reset/reset.py` | Tables `loans`, `loan_interest_accruals` ajoutées au reset |
| `api/scripts/cleanup_sandbox.py` | Idem pour le cleanup sandbox |

---

## 5. API Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/lending/loans` | Créer un prêt (status=pending) |
| `GET` | `/api/lending/loans` | Lister les prêts (filtres: client_id, status) |
| `GET` | `/api/lending/loans/{id}` | Détail d'un prêt |
| `POST` | `/api/lending/loans/{id}/accept` | Borrower accepte |
| `POST` | `/api/lending/loans/{id}/reject` | Borrower refuse |
| `POST` | `/api/lending/loans/{id}/cancel` | Lender annule |
| `POST` | `/api/lending/loans/{id}/activate` | Activation atomique |
| `GET` | `/api/lending/loans/{id}/repayment-preview` | Calcul du remboursement |
| `POST` | `/api/lending/loans/{id}/repay` | Remboursement complet |

---

## 6. Invariants respectés

### Invariant 1 — Conservation des fonds
`total_spot_before == total_spot_after` lors de l'activation.
Le principal est simplement transféré entre crypto_positions.

### Invariant 2 — Double-entry ledger
Chaque mouvement (activation, remboursement) crée une paire debit/credit dans pe_ledger_entries (si les comptes ledger existent).

### Invariant 3 — Symétrie
`lending_position.quantity == borrowing_position.quantity` — même principal, même instrument.

### Invariant 4 — Séparation stricte
- Les positions `lending`/`borrowing` sont **exclues** de `_compute_atoms_value`
- Elles n'apparaissent pas dans la valorisation spot
- `crypto_positions` reste inchangé pour le trading/bundles

### Invariant 5 — Spot invariant
Trading et bundles fonctionnent exactement comme avant. Aucune modification de:
- `ExchangeService`
- `BundleOrchestrator`
- `CryptoPositionRepository`
- `wallet_history`
- `wallet_statistics`

---

## 7. Tests (11/11 PASSED)

| Test | Couverture |
|------|-----------|
| `test_full_lifecycle` | Create → Accept → Activate → Repay (cycle complet) |
| `test_activation_conserves_total` | Invariant 1: conservation des fonds |
| `test_positions_are_symmetric` | Invariant 3: symétrie lending/borrowing |
| `test_valuation_excludes_lending` | Invariant 4: séparation valuation |
| `test_buy_sell_still_works_after_lending_module_load` | Invariant 5: non-régression trading |
| `test_insufficient_lender_balance` | Edge case: solde insuffisant |
| `test_double_activation` | Edge case: double activation impossible |
| `test_invalid_state_transitions` | Edge case: transitions invalides |
| `test_self_lending_rejected` | Edge case: auto-prêt interdit |
| `test_wrong_borrower_cannot_accept` | Sécurité: seul le bon borrower peut accepter |
| `test_ledger_entries_created_on_activation` | Invariant 2: double-entry si comptes existants |

---

## 8. Calcul des intérêts (V1)

```
interest = principal × (rate_bps / 10000) × (elapsed_days / 365)
platform_fee = interest × (fee_bps / 10000)

borrower_pays = principal + interest
lender_receives = principal + interest - platform_fee
```

Simple interest, calcul au moment du remboursement.

---

## 9. Modèle de données

### Table `loans`
```sql
id                      UUID PK
lender_client_id        UUID FK → pe_clients
borrower_client_id      UUID FK → pe_clients
asset                   VARCHAR(20)
principal               NUMERIC(30,10)
interest_rate_bps       INTEGER
platform_fee_bps        INTEGER
duration_days           INTEGER
start_at                TIMESTAMPTZ
end_at                  TIMESTAMPTZ
repaid_at               TIMESTAMPTZ
status                  VARCHAR(30)
lender_position_atom_id UUID
borrower_position_atom_id UUID
metadata                JSONB
created_at, updated_at  TIMESTAMPTZ
```

### Table `loan_interest_accruals`
```sql
id              UUID PK
loan_id         UUID FK → loans
accrued_amount  NUMERIC(30,10)
last_accrual_at TIMESTAMPTZ
created_at      TIMESTAMPTZ
```

---

## 10. Preuve de non-régression

- 1158 tests existants continuent de passer
- Reset financier mis à jour pour inclure les nouvelles tables
- Cleanup sandbox synchronisé
- Aucune modification des services Exchange, Bundle, Custody, Valuation globale
- Position type filtering ajouté dans `_compute_atoms_value` (protection future pour staking/collateral aussi)

---

## 11. Scope V1 (strict)

### Inclus
- P2P lending interne
- Transfert crypto interne
- Taux fixe (basis points)
- Durée fixe
- Remboursement complet

### Exclus (Phase 2B+)
- Collatéral
- Liquidation
- Margin
- Remboursement partiel
- Remboursement anticipé
- Auto-matching
- DeFi / blockchain
- Yield farming
