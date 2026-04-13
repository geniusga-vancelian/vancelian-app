# Lending Valuation, Visibility & Reporting Layer — Phase 2A.5 Report

## Date: 2026-03-21

---

## 1. Objectif

Ajouter une couche de valorisation et de visibilité pour les positions lending/borrowing, **sans modifier** le système existant spot. Passage d'un engine technique (Phase 2A) à un engine financier avec vue patrimoniale.

---

## 2. Logique de valorisation

### Règles de pricing

| Type | Formule | Nature |
|------|---------|--------|
| **Spot** | `value = +quantity × spot_price` | Actif liquide |
| **Lending** | `value = +quantity × spot_price` | Créance (même prix que spot) |
| **Borrowing** | `value = -quantity × spot_price` | Dette (valeur négative) |

### Source de prix unique

Toutes les positions (spot, lending, borrowing) utilisent la **même source** :
```
MarketDataLatestQuote → last_price (USDT) → usdt_to_eur(price, EURUSDT)
```

Résolu via `get_instrument_price()` → identique à `_compute_atoms_value` existant.

---

## 3. Fonctions créées

### `compute_position_market_value(db, atom)`
Valorise un `PositionAtom` individuel.
- Retourne prix USDT + EUR, valeur de marché signée (négatif pour borrowing)
- Inclut `loan_id`, `counterparty`, `status`

### `compute_total_portfolio_value_v2(db, client_id)`
Vue patrimoniale complète (wealth view).
- Agrège toutes les positions par type (spot / lending / borrowing)
- Formule : `net_value = spot + lending - borrowing`
- Retourne les positions détaillées

### `get_lending_positions(db, client_id)` / `get_borrowing_positions(db, client_id)`
Listes filtrées des positions ouvertes par type.

---

## 4. Fichiers créés

| Fichier | Description |
|---------|-------------|
| `api/services/lending/valuation.py` | Layer de valorisation lending (250 lignes) |
| `api/services/lending/wealth_router.py` | 3 endpoints API wealth |
| `api/tests/test_lending_valuation.py` | 9 tests (valuation, borrowing, net value, non-régression) |

---

## 5. Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/lending/__init__.py` | Export du wealth_router |
| `api/main.py` | Enregistrement du wealth_router |

---

## 6. API Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/app/portfolio/wealth?client_id=...` | Vue patrimoniale complète |
| `GET` | `/api/app/lending/positions?client_id=...` | Positions lending ouvertes |
| `GET` | `/api/app/borrowing/positions?client_id=...` | Positions borrowing ouvertes |

### Response `/api/app/portfolio/wealth`

```json
{
  "client_id": "uuid",
  "currency": "EUR",
  "spot": { "value": 12000, "count": 5 },
  "lending": {
    "value": 5000,
    "count": 2,
    "positions": [
      {
        "atom_id": "uuid",
        "asset": "BTC",
        "quantity": 0.5,
        "position_type": "lending",
        "price_eur": 72000.0,
        "market_value_eur": 36000.0,
        "loan_id": "uuid",
        "counterparty": "uuid"
      }
    ]
  },
  "borrowing": {
    "value": 2000,
    "count": 1,
    "positions": [...]
  },
  "net": { "value": 15000 }
}
```

---

## 7. Invariants respectés

### Invariant 1 — Séparation
- `crypto_positions` = spot uniquement (INCHANGÉ)
- `_compute_atoms_value` = spot uniquement (INCHANGÉ)
- Lending/borrowing = nouvelle couche parallèle

### Invariant 2 — Cohérence des prix
- Lending utilise **exactement le même prix** que spot
- Source unique : `MarketDataLatestQuote` via `get_instrument_price`
- Vérifié par test `test_lending_uses_same_price_as_spot`

### Invariant 3 — Borrowing négatif
- Toujours `value = -quantity × price` dans la wealth view
- Vérifié par test `test_borrowing_position_is_negative`
- Symétrie : `|lending| + borrowing ≈ 0` vérifié par `test_borrowing_absolute_equals_lending`

### Invariant 4 — Backward compatibility
- Aucune modification de :
  - `ExchangeService`
  - `wallet_history` / `wallet_statistics`
  - `_compute_atoms_value`
  - `get_portfolio_breakdown`
  - `CryptoPositionRepository`
- Vérifié par test `test_existing_valuation_unchanged`

---

## 8. Tests (9/9 PASSED)

| Test | Couverture |
|------|-----------|
| `test_lending_position_has_positive_value` | A. Lending valuation > 0 |
| `test_lending_uses_same_price_as_spot` | A. Prix identique au spot |
| `test_borrowing_position_is_negative` | B. Borrowing < 0 |
| `test_borrowing_absolute_equals_lending` | B. |lending| = |borrowing| |
| `test_net_value_formula` | C. net = spot + lending - borrowing |
| `test_wealth_with_no_lending` | C. Client sans prêt → lending=0 |
| `test_existing_valuation_unchanged` | D. _compute_atoms_value inchangé |
| `test_crypto_positions_untouched` | D. crypto_positions = spot only |
| `test_get_lending_positions_only` | E. Filtrage position_type correct |

### Non-régression globale
- 20 tests lending (Phase 2A + 2A.5) passent
- 1158 tests existants non impactés

---

## 9. Architecture résultante

```
                        ┌─────────────────────┐
                        │   Wealth View (V2)   │
                        │   /portfolio/wealth  │
                        └──────┬──────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
      ┌───────▼──────┐ ┌──────▼──────┐ ┌───────▼────────┐
      │  Spot atoms  │ │ Lending     │ │ Borrowing      │
      │  (existing)  │ │ atoms       │ │ atoms          │
      │              │ │ (Phase 2A)  │ │ (Phase 2A)     │
      └───────┬──────┘ └──────┬──────┘ └───────┬────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  pe_position_atoms   │
                    │  (single table)      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ MarketDataLatestQuote│
                    │ (single price source)│
                    └─────────────────────┘
```

### Vues existantes (INCHANGÉES)
- `_compute_atoms_value` → spot only
- `get_portfolio_breakdown` → spot only
- `crypto_positions` → spot only
- `wallet_history` → spot only

### Nouvelles vues (ADDITIVES)
- `compute_position_market_value` → any position type
- `compute_total_portfolio_value_v2` → wealth = spot + lending - borrowing
- `get_lending_positions` → lending only
- `get_borrowing_positions` → borrowing only

---

## 10. Prochaines phases

| Phase | Scope |
|-------|-------|
| **2B** | Collateral + Risk Engine |
| **3** | DeFi (Morpho) |
| **UI** | Dashboard wealth management (spot + yield + RWA + AI) |
