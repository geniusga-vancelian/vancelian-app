# Phase 2A.11.5 — Project-driven Lending Provisioning + Custody Visibility

## Objectif

Permettre :
1. Depuis l'admin **Project** → transformer un projet en offre exclusive investissable (création automatique pool + product + lien)
2. Depuis l'admin **Custody** → visualiser et auditer toutes les pools "Exclusive Offers" avec lenders, borrower, flux financiers

---

## Architecture

```
┌─────────────────────┐
│  Admin: Project      │
│  [Create Lending     │ ─── POST /create-from-project ───┐
│   Product]           │                                   │
└─────────────────────┘                                   │
                                                          ▼
┌─────────────────────┐        ┌──────────────────────────┐
│  Admin: Exclusive    │        │  OfferService             │
│  Offers (Custody)    │◄──────│  create_from_project()    │
│                      │  GET   │  get_admin_pool_list()    │
│  - Pool list         │  ───►  │  get_admin_pool_detail()  │
│  - Lenders table     │        │                          │
│  - Borrower table    │        │  ↓ delegates to          │
│  - Allocation audit  │        │  PoolLendingService       │
└─────────────────────┘        └──────────────────────────┘
```

---

## Ce qui a été implémenté

### 1. Backend — `create_from_project`

**Endpoint :** `POST /api/lending/products/create-from-project`

**Input :**
```json
{
  "project_id": "abc123",
  "borrower_client_id": "uuid",
  "asset": "USDC",
  "target_size": 2000000,
  "title": "Solar Project UAE",
  "supply_apr_bps": 800,
  "borrow_apr_bps": 1000
}
```

**Flow atomique :**
1. Vérifie que `project_id` n'est pas déjà lié (guard anti-duplication)
2. Crée `lending_pool` avec les rates
3. Crée `lending_pool_product` avec `project_id` + `borrower_client_id`
4. Retourne le product detail complet

### 2. Backend — Admin Custody Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/lending/products/admin/pools` | Liste de toutes les exclusive offers |
| `GET /api/lending/products/admin/pools/{pool_id}` | Détail complet d'une pool |

**Admin Pool Detail retourne :**

| Section | Contenu |
|---------|---------|
| `overview` | total_committed, total_borrowed, available_liquidity, utilization_rate |
| `product` | title, status, target, raised, progress, borrower_client_id, APR |
| `lenders[]` | client_id, committed, allocated, available, accrued_interest, status |
| `borrowers[]` | client_id, borrowed, accrued_interest_due, total_due, status |
| `allocations[]` | supply → borrow mapping, amount, date |
| `summary` | total_lenders, total_borrowed_positions, total_allocations |

### 3. Admin Project UI — "Exclusive Lending Offer"

Section interactive dans l'éditeur de projet :

**Si non activé :**
- Formulaire compact : Borrower ID, Asset, Target Size, APR
- Bouton "Create Lending Product"
- Appel `POST /create-from-project` directement

**Si activé :**
- Cartes métriques : APY, Progress, Investors, Status
- Product ID + Asset affichés

### 4. Admin Custody — Exclusive Offers

**Page `/admin/exclusive-offers`** (nouvel onglet sidebar) :

**Vue liste :**
- Summary cards : Total Offers, Active, Fundraising, Total Investors
- Table : Title, Asset, Raised, Target, Progress bar, Investors, APR, Status
- Lien "View →" vers le détail

**Vue détail `/admin/exclusive-offers/[poolId]`** :
- Product Overview (status, asset, APR, progress, borrower)
- Pool Liquidity (committed, borrowed, available, utilization)
- Lenders table (committed, allocated, available, accrued interest)
- Borrower table (borrowed, interest due, total due)
- Allocation Audit Trail (supply → borrow mapping)

---

## Endpoints créés

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/lending/products/create-from-project` | One-click provisioning |
| GET | `/api/lending/products/admin/pools` | Liste admin custody |
| GET | `/api/lending/products/admin/pools/{pool_id}` | Détail complet pool |

---

## Tests

### `test_project_lending_provisioning.py` — 11 tests

| Test | Description |
|------|-------------|
| `test_create_from_project_success` | Création avec titre, asset, borrower |
| `test_create_from_project_auto_title` | Auto-titre quand non fourni |
| `test_create_from_project_sets_pool` | Pool créée avec les rates corrects |
| `test_duplicate_project_rejected` | Double création → OfferError |
| `test_admin_pool_list_includes_created` | Pool visible dans la liste admin |
| `test_admin_pool_list_has_required_fields` | Tous les champs requis présents |
| `test_admin_pool_detail_empty_pool` | Pool vide : lenders=[], borrowers=[] |
| `test_admin_pool_detail_with_lenders` | 2 lenders visibles avec commitments |
| `test_admin_pool_detail_with_active_borrow` | After activation : borrower + allocations |
| `test_nonexistent_pool_raises` | Pool inexistante → 404 |
| `test_product_detail_after_provisioning` | product_id, title, investors_count OK |

### Non-régression

- **73 tests passés** (exclusive offer + product surface + project link + provisioning)
- Zéro régression sur tout le stack lending

---

## Safety / Guards

| # | Guard | Implémenté |
|---|-------|-----------|
| 1 | Double création project → rejeté | ✅ `OfferError` |
| 2 | Project sans borrower → erreur | ✅ Champ requis |
| 3 | Pool vide → visible dans admin | ✅ Sections vides affichées |
| 4 | Moteur lending non modifié | ✅ Couche au-dessus |
| 5 | Système Projects non modifié | ✅ Couche au-dessus |

---

## Fichiers modifiés / créés

| Fichier | Action |
|---------|--------|
| `api/services/lending/offer_service.py` | `create_from_project`, `get_admin_pool_list`, `get_admin_pool_detail` |
| `api/services/lending/offer_router.py` | Endpoints `create-from-project`, `admin/pools`, `admin/pools/{id}` |
| `web/src/components/admin/AdminSidebar.tsx` | Ajout "Exclusive Offers" dans la navigation |
| `web/src/app/admin/projects/[id]/page.tsx` | Section "Exclusive Lending Offer" interactive |
| `web/src/app/admin/exclusive-offers/page.tsx` | **Nouveau** — Liste admin custody |
| `web/src/app/admin/exclusive-offers/[poolId]/page.tsx` | **Nouveau** — Détail pool admin |
| `api/tests/test_project_lending_provisioning.py` | **Nouveau** — 11 tests |

---

## Impact

Cette phase transforme :
- **Feature technique** → **Machine opérationnelle**
- Admin peut créer une offre investissable en 1 clic depuis un projet
- Ops peut auditer chaque pool avec visibilité complète (lenders, borrower, allocations)
- Aucun impact sur le moteur lending ni sur le CMS Projects
