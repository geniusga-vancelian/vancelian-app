# Admin Project — Create Lending Product Fix Report

## Symptôme
Le bouton "Create Lending Product" dans l'admin Projects semblait ne rien faire :
- Aucun feedback visuel
- Aucun produit créé en base
- Après refresh, les valeurs saisies disparaissent
- L'UI reste sur le formulaire vide

## Root Causes identifiées (3)

### 1. `db.commit()` MANQUANT — `offer_router.py` (CRITIQUE)

**Sévérité : CRITIQUE — aucune donnée n'était persistée.**

`offer_router.py` ne faisait aucun `db.commit()` dans aucun de ses 9 endpoints d'écriture.  
Le service faisait `db.flush()` (écriture transactionnelle en mémoire), la réponse HTTP 200 repartait avec les données correctes, mais `get_db()` fermait la session sans commit → les données étaient perdues.

**Tous les autres routers lending** (`pool_router.py`, `interest_router.py`, `router.py`) faisaient correctement `db.commit()`.

**Endpoints corrigés :**
- `POST /` (create_product)
- `POST /{id}/open-fundraising`
- `POST /{id}/subscribe`
- `POST /{id}/activate`
- `POST /{id}/mark-repaid`
- `POST /{id}/close`
- `POST /{id}/link-project`
- `DELETE /{id}/link-project`
- `POST /create-from-project`

### 2. Appels directs au backend Python depuis le client (404)

Le code admin appelait `process.env.NEXT_PUBLIC_BACKEND_API_URL` côté client, mais cette variable n'était pas définie → les requêtes tombaient sur `localhost:3000` (Next.js) → 404.

**Correction :** Création de 4 routes proxy Next.js côté serveur :

| Route proxy | Backend Python |
|---|---|
| `POST /api/admin/lending/create-from-project` | `POST /api/lending/products/create-from-project` |
| `GET /api/admin/lending/product-data` | `GET /api/lending/products` (filtré par project_id) |
| `GET /api/admin/lending/pools` | `GET /api/lending/products/admin/pools` |
| `GET /api/admin/lending/pools/[poolId]` | `GET /api/lending/products/admin/pools/{pool_id}` |

### 3. `get_lending_data_for_projects()` exclut les drafts

Après création (status=`draft`), `fetchLendingProductData()` appelait `get_lending_data_for_projects()` qui filtre `status.notin_(["draft", "closed"])` → le produit fraîchement créé n'apparaissait jamais.

**Correction :** Le proxy `product-data` utilise maintenant `GET /api/lending/products` (listing complet sans filtre de status) au lieu de `GET /api/lending/products/projects/lending-data`.

## Corrections UX

### Inputs React contrôlés
- Remplacement de `document.getElementById()` par des `useState` contrôlés
- Les valeurs persistent entre les re-renders

### Validation frontend
- UUID format validation (regex)
- Target size > 0
- Supply APR > 0
- Erreurs inline par champ (bordure rouge + message)

### Feedback pendant le submit
- Bouton disabled + spinner SVG animé + label "Creating..."
- Aucun double-clic possible

### Feedback après succès
- Toast "Lending product created successfully!"
- Mise à jour d'état immédiate avec les données de la réponse (pas de refetch nécessaire pour l'affichage instantané)
- Refetch asynchrone 1s plus tard pour synchroniser avec le backend

### Feedback après erreur
- Toast rouge avec le message backend exact
- Messages clairs : "Borrower client xxx not found in pe_clients", "Backend unavailable", etc.
- Aucun échec silencieux possible

### Loading state
- Spinner "Loading lending data..." pendant le chargement initial
- Différentiation visuelle du status `draft` (couleur amber)

### Données affichées post-création
- Product ID, Pool ID, Borrower, Asset, APY, Progress, Investors, Status

## Logging structuré
- Frontend : `[LendingProduct] Creating with payload:`, `[LendingProduct] Response:`, `[LendingProduct] Error:`
- Proxy : `[lending/create-from-project] Proxying to backend:`, `[lending/create-from-project] Backend responded:`
- Protection contre les réponses non-JSON du backend

## Fichiers modifiés

### Backend Python
- `api/services/lending/offer_router.py` — ajout `db.commit()` dans 9 endpoints
- `api/services/lending/offer_service.py` — validation `borrower_client_id` avant création

### Frontend Next.js
- `web/src/app/admin/projects/[id]/page.tsx` — refonte section Exclusive Lending Offer
- `web/src/app/api/admin/lending/create-from-project/route.ts` — proxy avec logging
- `web/src/app/api/admin/lending/product-data/route.ts` — proxy sans filtre draft
- `web/src/app/api/admin/lending/pools/route.ts` — proxy admin pools
- `web/src/app/api/admin/lending/pools/[poolId]/route.ts` — proxy admin pool detail
- `web/src/app/admin/exclusive-offers/page.tsx` — fix appel via proxy
- `web/src/app/admin/exclusive-offers/[poolId]/page.tsx` — fix appel via proxy
- `web/.env` — ajout `BACKEND_API_URL=http://localhost:8000`

## Tests
- **152/152 tests passés** — zéro régression sur tout le stack lending
- Tests couverts : exclusive offer, project linking, provisioning, pools, interest, repayment, product surface, P2P, valuation, E2E

## Before / After

### Before
1. Click "Create Lending Product" → rien ne se passe visuellement
2. Backend retourne 200 avec les données mais ne commit pas → données perdues
3. Refetch cherche le produit via un endpoint qui exclut les drafts → ne le trouve pas
4. UI reste sur le formulaire vide → impression que le bouton ne marche pas

### After
1. Click → spinner + "Creating..." + bouton disabled
2. Backend commit les données en base → produit persisté
3. Réponse utilisée directement pour mettre à jour l'UI → affichage instantané
4. Toast success + métriques affichées (APY, status draft, borrower, pool ID)
5. En cas d'erreur : toast rouge + message clair + pas de perte de données du formulaire
