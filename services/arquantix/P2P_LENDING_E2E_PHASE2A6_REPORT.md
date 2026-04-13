# P2P Lending Product Surface (E2E) — Phase 2A.6 Report

## Date: 2026-03-21

---

## 1. Objectif

Transformer le moteur lending (Phase 2A) en **feature produit testable de bout en bout** entre 2 clients réels, avec validation complète des balances, positions et wealth view.

---

## 2. Flow produit validé E2E

```
┌─────────────┐    POST /loans     ┌──────────────┐
│  Lender A   │ ─────────────────► │  Loan        │
│  (1000 USDC)│                    │  status=     │
└─────────────┘                    │  PENDING     │
                                   └──────┬───────┘
                                          │
┌─────────────┐  POST /loans/{id}/accept  │
│  Borrower B │ ◄─────────────────────────┘
│  (0 USDC)   │
└──────┬──────┘
       │          POST /loans/{id}/activate
       ▼          (ATOMIC TRANSACTION)
┌──────────────────────────────────────────┐
│  1. Debit lender crypto_positions        │
│  2. Credit borrower crypto_positions     │
│  3. Create lending PositionAtom          │
│  4. Create borrowing PositionAtom        │
│  5. Ledger entries (audit)               │
│  6. loan.status = ACTIVE                 │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐  ┌──────────────────┐
│  Lender A        │  │  Borrower B      │
│  spot: 0 USDC    │  │  spot: 1000 USDC │
│  lending: 1000   │  │  borrowing: 1000 │
│  net: ~1000      │  │  net: ~0         │
└──────────────────┘  └──────────────────┘
```

---

## 3. Preuves E2E (test_full_e2e_flow)

### Balances après activation
| Client | Spot USDC | Lending | Borrowing | Net wealth |
|--------|-----------|---------|-----------|------------|
| Lender A | 0 | 1000 | 0 | ~1000 EUR |
| Borrower B | 1000 | 0 | 1000 | ~0 EUR |

### Invariants vérifiés
- **Conservation** : total_spot(A+B) = 1000 avant ET après ✅
- **Symétrie** : lending_qty == borrowing_qty ✅
- **Séparation** : positions lending/borrowing exclus de crypto_positions ✅
- **Atomicité** : activation = transaction unique, double activation impossible ✅
- **Wealth** : net = spot + lending - borrowing ✅

---

## 4. Modifications apportées

### Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/lending/service.py` | Ajout `list_loans_by_role()`, `get_client_summary()` |
| `api/services/lending/router.py` | Ajout param `?role=`, endpoint `/summary` |
| `api/services/lending/schemas.py` | Ajout `LoanDetailResponse`, `LendingSummaryResponse`, defaults V1 |
| `api/services/lending/valuation.py` | Fix: spot source = crypto_positions (source de vérité) |

### Fichier créé

| Fichier | Description |
|---------|-------------|
| `api/tests/test_lending_e2e.py` | 9 scénarios E2E complets |

---

## 5. API Surface (Flutter-ready)

### Endpoints principaux

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/lending/loans` | Créer une offre (V1: sans intérêts) |
| `POST` | `/api/lending/loans/{id}/accept` | Borrower accepte |
| `POST` | `/api/lending/loans/{id}/activate` | Activation atomique |
| `GET` | `/api/lending/loans?role=lender&client_id=...` | Prêts émis |
| `GET` | `/api/lending/loans?role=borrower&client_id=...` | Emprunts reçus |
| `GET` | `/api/lending/summary?client_id=...` | Dashboard résumé |
| `POST` | `/api/lending/loans/{id}/reject` | Borrower refuse |
| `POST` | `/api/lending/loans/{id}/cancel` | Lender annule |

### Wealth endpoints (Phase 2A.5)

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/app/portfolio/wealth?client_id=...` | Vue patrimoine complète |
| `GET` | `/api/app/lending/positions?client_id=...` | Positions lending |
| `GET` | `/api/app/borrowing/positions?client_id=...` | Positions borrowing |

### Payload simplifié V1 (sans intérêts)

```json
{
  "lender_client_id": "uuid",
  "borrower_client_id": "uuid",
  "asset": "USDC",
  "principal": 1000
}
```

`interest_rate_bps`, `platform_fee_bps`, `duration_days` sont optionnels et défaut à 0/0/30.

### Response `/api/lending/summary`

```json
{
  "client_id": "uuid",
  "total_lent_count": 1,
  "total_borrowed_count": 0,
  "total_lent_value_eur": 864.63,
  "total_borrowed_value_eur": 0.0,
  "active_loans_as_lender": [
    {
      "id": "uuid",
      "role": "lender",
      "counterparty_id": "uuid",
      "counterparty_email": "borrower@example.com",
      "asset": "USDC",
      "principal": 1000,
      "market_value_eur": 864.63,
      "status": "active",
      "start_at": "2026-03-21T...",
      "created_at": "2026-03-21T..."
    }
  ],
  "active_loans_as_borrower": [],
  "pending_offers_received": []
}
```

---

## 6. Tests E2E (9/9 PASSED)

| Test | Scénario |
|------|----------|
| `test_full_e2e_flow` | **Principal** : create→accept→activate, balances, positions, wealth |
| `test_role_based_listing` | ?role=lender et ?role=borrower filtrage correct |
| `test_lending_summary` | Dashboard summary avec counterparty et market values |
| `test_rejection_changes_nothing` | Refus : rien ne change (balances, positions) |
| `test_double_activation_blocked` | Double activation interdite |
| `test_activation_rejected_if_insufficient` | Balance insuffisante → rejeté |
| `test_lend_btc_and_usdc` | Multi-asset lending simultané |
| `test_lender_can_cancel_before_activation` | Annulation avant acceptation |
| `test_lender_can_cancel_accepted_loan` | Annulation après acceptation |

### Total lending tests : **29/29 passent** (Phase 2A + 2A.5 + 2A.6)

---

## 7. Fix important : Wealth View source de vérité

### Problème détecté
`compute_total_portfolio_value_v2` utilisait `pe_position_atoms` pour le spot, mais la source de vérité du spot est `crypto_positions` (pas d'atoms spot créés lors du lending transfer).

### Correction
- **Spot** : lu depuis `crypto_positions` via `get_crypto_value_eur()` (identique à `get_portfolio_breakdown`)
- **Lending/Borrowing** : lu depuis `pe_position_atoms` filtrés par type
- Formule : `net = spot(crypto_positions) + lending(atoms) - borrowing(atoms)`

---

## 8. Scope V1 appliqué

### Inclus ✅
- Création d'offre P2P
- Acceptation / refus / annulation
- Activation atomique
- Transfert custody interne
- Positions lending / borrowing
- Role-based listing
- Dashboard summary avec market values
- Wealth view intégrée

### Exclus ❌
- Intérêts
- Remboursement
- Défaut
- Collateral
- Multi-lender
- Matching automatique

---

## 9. Prochaines phases

| Phase | Scope |
|-------|-------|
| **2A.7** | Intérêts + remboursement |
| **2B** | Collateral + Risk Engine |
| **3** | DeFi (Morpho) |
| **UI** | Flutter lending screens |
