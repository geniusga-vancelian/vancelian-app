# Phase 2A.11 — Project ↔ Lending Product Integration

## Objectif

Lier le CMS **Projects** existant (Prisma) aux **lending_pool_products** (SQLAlchemy) pour enrichir les données des offres exclusives visibles dans Flutter, **sans créer de nouveau CMS** et **sans dupliquer le contenu marketing**.

---

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│  CMS Projects       │        │  lending_pool_products    │
│  (Prisma / Next.js) │◄──────►│  (SQLAlchemy / Python)   │
│                     │  1:1   │                          │
│  - title, i18n      │  FK    │  - project_id (unique)   │
│  - images, gallery  │        │  - apy, raised, target   │
│  - description      │        │  - investors_count       │
│  - FAQ, etc.        │        │  - status, asset         │
└─────────────────────┘        └──────────────────────────┘
         │                                │
         ▼                                ▼
┌────────────────────────────────────────────┐
│  GET /api/projects (Next.js)               │
│  ┌───────────────┐  ┌──────────────────┐   │
│  │ CMS content   │ +│ lending data     │   │
│  │ (title, img)  │  │ (apy, progress)  │   │
│  └───────────────┘  └──────────────────┘   │
└────────────────────────────────────────────┘
         │
         ▼
┌──────────────┐
│  Flutter App │
│  OfferProject│
└──────────────┘
```

---

## Modifications effectuées

### 1. Database — `lending_pool_products`

Ajout colonne `project_id` (VARCHAR(30), UNIQUE, nullable) :
- Lien 1-to-1 avec les `projects` Prisma
- Index `ix_lpp_project_id` pour les lookups rapides
- Migration Alembic `076_add_project_id_to_lending_products.py`

### 2. Backend Service — `offer_service.py`

Nouvelles méthodes :

| Méthode | Description |
|---------|-------------|
| `link_project(db, product_id, project_id)` | Lie un produit à un project CMS (1-to-1) |
| `unlink_project(db, product_id)` | Retire le lien |
| `get_lending_data_for_projects(db)` | Retourne `{ project_id: { apy, raised, target, progress, investorsCount, ... } }` |
| `_get_investors_count(db, pool_id)` | Count distinct lenders |

Mises à jour :
- `create_product()` accepte `project_id` optionnel
- `_product_to_dict()` expose `project_id` et `investors_count`

### 3. API Endpoints — `offer_router.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lending/products/{id}/link-project` | POST | Lier un product à un project |
| `/api/lending/products/{id}/link-project` | DELETE | Retirer le lien |
| `/api/lending/products/projects/lending-data` | GET | Données lending pour tous les projects liés |

### 4. API Publique — `GET /api/projects` (Next.js)

Enrichissement automatique via `fetchLendingDataForProjects()` :
- Appel parallèle au backend Python (`/api/lending/products/projects/lending-data`)
- LEFT JOIN logique : chaque project reçoit ses données lending si liées
- Fallback silencieux si backend indisponible

#### JSON enrichi (backward compatible)

```json
{
  "id": "abc123",
  "slug": "solar-project-uae",
  "title": "Solar Project UAE",
  "coverUrl": "https://...",
  "category": "Energy",
  "description": "...",
  
  "apy": 8.0,
  "raised": 1200000,
  "target": 2000000,
  "progress": 60.0,
  "investorsCount": 42,
  "durationMonths": 18,
  "lendingAsset": "USDC",
  "lendingStatus": "fundraising",
  "isInvestable": true
}
```

#### Fallback (project sans lending)

```json
{
  "id": "xyz789",
  "title": "Art Collection",
  
  "apy": null,
  "raised": null,
  "target": null,
  "progress": null,
  "investorsCount": null,
  "durationMonths": null,
  "lendingAsset": null,
  "lendingStatus": null,
  "isInvestable": false
}
```

### 5. Admin — Project Editor

Section "Linked Lending Product" ajoutée dans la page d'édition :
- Affichage read-only des métriques lending (APY, progress, investors, status)
- Cartes colorées avec indicateurs visuels
- Données chargées depuis l'endpoint `/api/lending/products/projects/lending-data`

---

## Tests

### `test_project_lending_link.py` — 12 tests

| Test | Description |
|------|-------------|
| `test_link_project_to_product` | Liaison basique fonctionne |
| `test_unlink_project` | Retrait du lien |
| `test_create_product_with_project_id` | Création directe avec project_id |
| `test_double_link_rejected` | Même project → 2 produits interdit |
| `test_enrichment_basic` | Données APY, target, status correctes |
| `test_enrichment_with_subscribers` | Investors count et progress corrects |
| `test_unlinked_project_not_in_data` | Produit sans project_id exclu |
| `test_draft_product_not_in_data` | Produit "draft" exclu |
| `test_multiple_projects_with_lending` | 3 projets indépendants enrichis |
| `test_product_detail_includes_project_id` | Dict expose project_id |
| `test_product_detail_includes_investors_count` | Dict expose investors_count |
| `test_product_detail_no_project_id` | project_id = null si non lié |

### Non-régression

- **62 tests passés** (exclusive offer + product surface + project link)
- Zéro régression sur le moteur lending existant

---

## Invariants

| # | Invariant | Vérifié |
|---|-----------|---------|
| 1 | 1 project ↔ 1 lending product (unique constraint) | ✅ |
| 2 | Project sans lending → null data (backward compat) | ✅ |
| 3 | Backend indisponible → API retourne CMS seul | ✅ |
| 4 | Division par zéro évitée (target = 0 → progress = 0) | ✅ |
| 5 | Produits "draft" et "closed" exclus de l'enrichissement | ✅ |
| 6 | Moteur lending non modifié | ✅ |
| 7 | CMS Projects non modifié | ✅ |

---

## Mapping CMS → Lending

| Champ Flutter (OfferProject) | Source CMS | Source Lending |
|------------------------------|------------|----------------|
| `title` | `project_i18n.title` | — |
| `imageUrl` | `project.coverMedia` | — |
| `category` | `project.investmentCategory` | — |
| `description` | `project_i18n.description` | — |
| `howItWorks` | `project_i18n.howItWorks` | — |
| `keyInformation` | `project_i18n.keyInformation` | — |
| `faq` | `project_i18n.faq` | — |
| `gallery` | `project_media` | — |
| `apy` | — | `supply_apr_bps / 100` |
| `raised` | — | `current_raised` |
| `target` | — | `target_size` |
| `progress` | — | `raised / target × 100` |
| `investorsCount` | — | `COUNT(DISTINCT lenders)` |
| `durationMonths` | — | `maturity_date - start_date` |
| `isInvestable` | — | `status == "fundraising"` |

---

## Fichiers modifiés / créés

| Fichier | Action |
|---------|--------|
| `api/services/lending/offer_models.py` | Ajout `project_id` column + index |
| `api/services/lending/offer_service.py` | Ajout `link_project`, `unlink_project`, `get_lending_data_for_projects`, `_get_investors_count` ; mise à jour `create_product`, `_product_to_dict` |
| `api/services/lending/offer_router.py` | Ajout endpoints link/unlink/lending-data |
| `api/alembic/versions/076_add_project_id_to_lending_products.py` | Migration Alembic |
| `web/src/app/api/projects/route.ts` | Enrichissement lending dans GET /api/projects |
| `web/src/app/admin/projects/[id]/page.tsx` | Section "Linked Lending Product" |
| `api/tests/test_project_lending_link.py` | 12 nouveaux tests |
