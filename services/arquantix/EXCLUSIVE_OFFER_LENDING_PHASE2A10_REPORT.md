# Phase 2A.10 — Exclusive Offer Lending Pool

## Objectif

Ajouter une couche **produit financier structuré** au-dessus du moteur de lending pool existant, permettant de créer des "offres exclusives" avec :
- **1 borrower unique** (client partenaire)
- **N lenders** (clients app)
- **Pool dédiée** à un projet spécifique
- **Lifecycle complet** : draft → fundraising → funded → active → repaid → closed

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Flutter App                          │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Offer List  │  │Subscribe │  │  My Positions    │  │
│  │  (market)    │  │  (lender)│  │  (portfolio)     │  │
│  └──────┬───────┘  └────┬─────┘  └────────┬─────────┘  │
└─────────┼───────────────┼─────────────────┼──────────────┘
          │               │                 │
          ▼               ▼                 ▼
┌─────────────────────────────────────────────────────────┐
│              offer_router.py (FastAPI)                    │
│  POST /products         — create                         │
│  POST /{id}/open-fundraising                             │
│  POST /{id}/subscribe   — lender subscribes              │
│  POST /{id}/activate    — auto borrow                    │
│  POST /{id}/mark-repaid                                  │
│  POST /{id}/close                                        │
│  GET  /products         — list                           │
│  GET  /{id}             — detail                         │
│  GET  /my-positions/list                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              offer_service.py (business logic)           │
│  create_product()                                        │
│  open_fundraising()                                      │
│  subscribe()           ← delegates to pool_supply        │
│  activate_product()    ← delegates to borrow_from_pool   │
│  check_borrow_allowed()← guard in pool_service           │
│  mark_repaid() / close_product()                         │
└────────────────────┬────────────────────────────────────┘
                     │ DELEGATES (never touches atoms/ledger)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Moteur existant (INCHANGÉ)                   │
│  PoolLendingService │ InterestEngine │ RepaymentEngine   │
│  PositionAtom │ LendingPool │ CryptoPosition │ Ledger   │
└─────────────────────────────────────────────────────────┘
```

---

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `api/services/lending/offer_models.py` | Modèle `LendingPoolProduct` |
| `api/services/lending/offer_service.py` | Service métier (create, subscribe, activate, lifecycle) |
| `api/services/lending/offer_router.py` | 9 endpoints API |
| `api/alembic/versions/075_add_lending_pool_products.py` | Migration Alembic |
| `api/tests/test_exclusive_offer.py` | 23 tests |

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/lending/pool_service.py` | Guard `check_borrow_allowed()` dans `borrow_from_pool()` |
| `api/services/lending/__init__.py` | Export `offer_router` |
| `api/main.py` | Registration du router |
| `api/services/financial_reset/reset.py` | Ajout `lending_pool_products` au cleanup |

---

## Modèle de données

### `lending_pool_products`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID PK | |
| `lending_pool_id` | UUID FK UNIQUE | Pool dédiée |
| `product_type` | VARCHAR(50) | `exclusive_offer` |
| `title` | VARCHAR(200) | "Solar Project UAE" |
| `description` | TEXT | Description du projet |
| `borrower_client_id` | UUID FK | Borrower unique |
| `asset` | VARCHAR(20) | USDC, BTC, ETH |
| `target_size` | NUMERIC | Objectif de levée |
| `current_raised` | NUMERIC | Montant souscrit |
| `min_ticket` | NUMERIC | Ticket minimum |
| `max_ticket` | NUMERIC | Ticket maximum |
| `supply_apr_bps` | NUMERIC | Taux lender (bps) |
| `borrow_apr_bps` | NUMERIC | Taux borrower (bps) |
| `use_of_funds` | TEXT | Utilisation des fonds |
| `start_date` | DATE | Date d'activation |
| `maturity_date` | DATE | Date d'échéance |
| `status` | VARCHAR(30) | Lifecycle status |

---

## Lifecycle

```
draft → fundraising → funded → active → repaid → closed
  │         │            │         │        │
  │    subscribe()   auto when   activate   repay
  │                  target met             engine
  open_fundraising()
```

---

## Flux métier

### 1. Création

```
POST /api/lending/products
→ Crée une LendingPool dédiée
→ Crée le LendingPoolProduct (status: draft)
```

### 2. Souscription

```
POST /api/lending/products/{id}/subscribe
→ Vérifie: status == fundraising
→ Vérifie: min_ticket <= amount <= max_ticket
→ Vérifie: current_raised + amount <= target_size
→ Vérifie: lender != borrower
→ Délègue à pool_supply (réserve les fonds)
→ Met à jour current_raised
→ Auto-transition vers "funded" si target atteint
```

### 3. Activation

```
POST /api/lending/products/{id}/activate
→ Vérifie: status == funded (ou fundraising + target atteint)
→ Appelle borrow_from_pool(borrower_client_id, raised_amount)
→ Crée positions lending (lenders) + borrowing (borrower)
→ Transfère les fonds (spot)
→ status → active
```

### 4. Guard borrow

```python
# Dans pool_service.borrow_from_pool():
OfferService.check_borrow_allowed(db, pool.id, borrower_client_id)
# → Rejette si pool liée à un produit et borrower != borrower_client_id
```

---

## Invariants

| # | Invariant | Vérifié |
|---|-----------|---------|
| 1 | Borrower unique par pool produit | ✅ |
| 2 | Pas de souscription hors fundraising | ✅ |
| 3 | Pas d'overfunding (cap respecté) | ✅ |
| 4 | min/max ticket enforced | ✅ |
| 5 | Borrower ne peut pas se prêter à lui-même | ✅ |
| 6 | Lifecycle strict (transitions invalides rejetées) | ✅ |
| 7 | Moteur lending inchangé (atoms, ledger, custody) | ✅ |
| 8 | crypto_positions non touché | ✅ |

---

## Endpoints API

| Méthode | Route | Description |
|---------|-------|-------------|
| POST | `/api/lending/products` | Créer une offre |
| POST | `/{id}/open-fundraising` | Ouvrir la levée |
| POST | `/{id}/subscribe` | Souscrire (lender) |
| POST | `/{id}/activate` | Activer (auto borrow) |
| POST | `/{id}/mark-repaid` | Marquer remboursé |
| POST | `/{id}/close` | Clôturer |
| GET | `/api/lending/products` | Lister les offres |
| GET | `/{id}` | Détail d'une offre |
| GET | `/my-positions/list` | Positions d'un lender |

---

## Data contract (frontend)

### Product listing

```json
{
  "product_id": "uuid",
  "title": "Solar Project UAE",
  "asset": "USDC",
  "target_size": 100000.0,
  "current_raised": 75000.0,
  "remaining": 25000.0,
  "progress_pct": 75.0,
  "supply_apr": 8.0,
  "borrow_apr": 10.0,
  "status": "fundraising",
  "borrower_client_id": "uuid",
  "use_of_funds": "Equipment purchase",
  "maturity_date": "2028-06-01"
}
```

### User subscription

```json
{
  "product_id": "uuid",
  "title": "Solar Project UAE",
  "asset": "USDC",
  "committed": 50000.0,
  "status": "active",
  "supply_apr": 8.0,
  "value_eur": 46000.0,
  "commitment_status": "fully_used"
}
```

---

## Tests

### Résultats

```
23 passed — test_exclusive_offer.py

129 passed — full regression (all suites)
```

### Couverture

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Création de produit | 4 | ✅ |
| Souscription (success, min, max, cap, self, auto-fund, wrong status) | 7 | ✅ |
| Activation (borrow, positions, unfunded) | 3 | ✅ |
| Restriction borrower (external rejected) | 1 | ✅ |
| Cycle E2E complet (create → close) | 1 | ✅ |
| Edge cases (draft activate, multi-lender, invalid transitions) | 3 | ✅ |
| Listing et positions utilisateur | 4 | ✅ |

---

## Non-régression

129 tests passés incluant toutes les suites :
- Phase 2A → 2A.8 (moteur lending)
- Phase 2A.9 (product surface)
- Phase 2A.10 (exclusive offers)

**Zéro régression. Moteur lending intact.**
