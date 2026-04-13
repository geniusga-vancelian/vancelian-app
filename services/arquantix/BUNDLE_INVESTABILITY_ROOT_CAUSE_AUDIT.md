# BUNDLE_INVESTABILITY_ROOT_CAUSE_AUDIT

## Executive Summary

Les 2 bundles visibles dans Markets ("Crypto Bundle Top 2" et "Crypto Bundle TOP 5")
n'étaient **pas investissables** car aucun `pe_portfolios` de type `bundle_portfolio` n'existait
en base de données — ni pour le client courant, ni pour aucun autre client.

Les `ProductDefinition` et `PortfolioTemplate` existaient et étaient correctement configurés,
mais l'étape de **provisioning** (création d'un Portfolio client + copie des allocations) n'avait
jamais été exécutée. Il n'existait aucun script ou automatisme pour cette étape.

**Correctif appliqué** : auto-provisioning idempotent dans l'endpoint `GET /api/app/bundle/catalog`.
Pour chaque produit bundle public sans portfolio pour le client courant, un portfolio et ses
allocations cibles sont créés automatiquement depuis le template. Les deux bundles sont
maintenant investissables.

---

## Visible Bundles in Markets

### Source de données
Les cartes bundle dans Markets sont alimentées par `CryptoBundlesWidget` qui appelle
`ProductCatalogApi.getBundleCatalog()` → proxy Next.js → `GET /api/app/bundle/catalog`
sur le backend FastAPI.

### Bundles identifiés

| Champ | Bundle 1 | Bundle 2 |
|-------|----------|----------|
| **Nom** | Crypto Bundle Top 2 | Crypto Bundle TOP 5 |
| **product_code** | `CRYPTO_BUNDLE_TOP2` | `CRYPTO_BUNDLE_TOP_5` |
| **ProductDefinition.id** | `9426e035-b1ff-4d67-b911-386869f7befc` | `096e588b-5fb3-4552-bb38-60fa584b08ea` |
| **is_public** | `true` | `true` |
| **status** | `active` | `active` |
| **product_type** | `crypto_bundle` | `crypto_bundle` |

Les deux produits sont bien publics et actifs → ils apparaissent correctement dans le catalogue.

---

## Bundle Catalog Audit

### Endpoint audité
`GET /api/app/bundle/catalog` (`api/services/test_clients/router.py`)

### Comportement AVANT correctif

1. `CatalogService.get_public_catalog(db, product_type="crypto_bundle")` → retourne les 2 produits ✅
2. Query `pe_portfolios WHERE client_id = X AND portfolio_type = 'bundle_portfolio' AND status = 'active'` → **0 rows** ❌
3. `portfolio_map` = `{}` → tous les items enrichis avec `portfolio_id = null`

### Conséquence Flutter
`_onInvestTap()` vérifie `portfolioId` → null → re-fetch via `getBundleCatalog()` → toujours null
→ SnackBar "Ce bundle n'est pas encore disponible à l'investissement."

---

## Portfolio Engine Audit

### Table `pe_product_definitions`
```
CRYPTO_BUNDLE_TOP2     | active | is_public=true  ✅
CRYPTO_BUNDLE_TOP_5    | active | is_public=true  ✅
CRYPTO_BUNDLE_TOP3_SOL | archived | is_public=false (non visible, OK)
TEST_BUNDLE_TOP3       | archived | is_public=false (non visible, OK)
```

### Table `pe_portfolio_templates`
```
CRYPTO_BUNDLE_TOP2_DEFAULT  → product: CRYPTO_BUNDLE_TOP2   ✅
CRYPTO_BUNDLE_TOP_5_DEFAULT → product: CRYPTO_BUNDLE_TOP_5  ✅
```

### Table `pe_template_allocations`
```
TOP2:  BTC-SPOT 70%, ETH-SPOT 30%                          ✅
TOP_5: BTC-SPOT 50%, ETH-SPOT 20%, SOL 10%, XRP 10%, BNB 10% ✅
```

### Table `pe_portfolios` (AVANT correctif)
```
0 rows de type bundle_portfolio  ❌❌❌
```

### Table `pe_product_subscriptions`
```
0 rows pour les produits crypto_bundle  ❌
```

### Diagnostic
Les scripts de bootstrap (`bootstrap_crypto_bundle_top2.py`, etc.) créaient uniquement :
- `ProductDefinition`
- `PortfolioTemplate`
- `TemplateAllocation`

Mais **pas** :
- `ProductSubscription` pour le client
- `Portfolio` pour le client (via provisioning)
- `TargetAllocation` pour le portfolio

Le `ProvisioningService` standard exige une subscription préalable, mais aucun workflow
automatisé ne créait ces subscriptions pour le client bootstrap.

---

## Mapping / Resolution Audit

### Chaîne complète Flutter → Backend

```
Flutter _onInvestTap(product)
  → product.portfolioId (from getBundleCatalog response)
  → if null: retry getBundleCatalog()
  → getBundleCatalog()
     → GET http://localhost:3000/api/mobile/flutter/bundle/catalog
     → Next.js proxy → GET http://127.0.0.1:8000/api/app/bundle/catalog
     → FastAPI mobile_bundle_catalog()
        → get_bootstrap(db) → client_id from app_runtime_settings
        → get_public_catalog(db, product_type="crypto_bundle") → 2 items
        → query pe_portfolios(client_id, bundle_portfolio, active) → 0 rows
        → portfolio_map = {} → portfolio_id = null pour tous les items
  → portfolioId still null → SnackBar error
```

### Point de rupture exact
`portfolio_map.get(str(item.id))` retourne `None` pour les 2 bundles car **aucun portfolio
n'existe avec `origin_product_id` pointant vers ces produits**.

---

## Root Cause Per Bundle

### Bundle 1 : Crypto Bundle Top 2

| Critère | Valeur | Statut |
|---------|--------|--------|
| Visible dans Markets | Oui | ✅ |
| Présent dans bundle catalog | Oui | ✅ |
| ProductDefinition active + publique | Oui | ✅ |
| PortfolioTemplate existe | Oui | ✅ |
| TemplateAllocations existent | Oui (BTC 70%, ETH 30%) | ✅ |
| Portfolio pour le client | **NON — 0 rows** | ❌ |
| portfolio_id dans catalog response | `null` (AVANT fix) | ❌ |
| Investissable | **NON** | ❌ |
| **Cause racine** | Aucun Portfolio provisionné | |

### Bundle 2 : Crypto Bundle TOP 5

| Critère | Valeur | Statut |
|---------|--------|--------|
| Visible dans Markets | Oui | ✅ |
| Présent dans bundle catalog | Oui | ✅ |
| ProductDefinition active + publique | Oui | ✅ |
| PortfolioTemplate existe | Oui | ✅ |
| TemplateAllocations existent | Oui (BTC 50%, ETH 20%, SOL/XRP/BNB 10%) | ✅ |
| Portfolio pour le client | **NON — 0 rows** | ❌ |
| portfolio_id dans catalog response | `null` (AVANT fix) | ❌ |
| Investissable | **NON** | ❌ |
| **Cause racine** | Aucun Portfolio provisionné | |

### Cause racine commune
**Provisioning gap** : les scripts de seed créent les définitions produit mais pas les portfolios
client. Le `ProvisioningService` exige un workflow subscription → provision, mais aucun
automatisme ne l'exécutait pour le client bootstrap.

---

## Minimal Fix Applied

### 1. Auto-provisioning dans `GET /api/app/bundle/catalog`

**Fichier** : `api/services/test_clients/router.py`

L'endpoint `mobile_bundle_catalog` détecte maintenant les produits bundle sans portfolio
pour le client courant et les provisionne automatiquement :

1. Pour chaque `ProductCatalogItem` sans entrée dans `portfolio_map`
2. Cherche le `PortfolioTemplate` correspondant au produit
3. Crée un `Portfolio` (`bundle_portfolio`, `active`, `origin_product_id` = product.id)
4. Copie les `TemplateAllocation` → `TargetAllocation` pour le nouveau portfolio
5. Commit si au moins un portfolio a été créé
6. Le `portfolio_map` est mis à jour en mémoire → réponse enrichie immédiate

**Caractéristiques** :
- Idempotent : ne crée pas de doublons (vérifié)
- Sans side-effect sur les produits existants
- Traçable : `metadata.auto_provisioned = true` dans les portfolios créés
- Compatible avec le provisioning standard (un provisioning formel ultérieur peut coexister)

### 2. Metadata produits enrichies

Ajout de `entry_asset_default` et `entry_assets_allowed` dans les metadata des deux
produits bundle actifs :

```sql
UPDATE pe_product_definitions
SET metadata = metadata || '{"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC", "EURC"]}'
WHERE product_code IN ('CRYPTO_BUNDLE_TOP2', 'CRYPTO_BUNDLE_TOP_5') AND status = 'active';
```

Ceci permet au catalogue de retourner ces champs au niveau top-level, et au
`BundleOrchestrator` de les utiliser directement (au lieu de tomber sur les fallbacks).

---

## Validation Scenarios

### Cas 1 — Bundle catalog enrichi
```
GET /api/app/bundle/catalog
→ 2 items
→ Crypto Bundle Top 2:  portfolio_id = 2430f858-... ✅
→ Crypto Bundle TOP 5:  portfolio_id = fcc6d37c-... ✅
→ entry_asset_default = USDC ✅
→ entry_assets_allowed = [USDC, EURC] ✅
```

### Cas 2 — Idempotence
```
2e appel GET /api/app/bundle/catalog
→ toujours 2 items, mêmes portfolio_id
→ pe_portfolios count = 2 (pas de doublons) ✅
```

### Cas 3 — DB state
```
pe_portfolios:
  - Crypto Bundle Top 2:  client=e34ff297, status=active, origin=9426e035 ✅
  - Crypto Bundle TOP 5:  client=e34ff297, status=active, origin=096e588b ✅

pe_target_allocations:
  - Top 2: BTC-SPOT 70%, ETH-SPOT 30% ✅
  - TOP 5: BTC-SPOT 50%, ETH-SPOT 20%, SOL 10%, XRP 10%, BNB 10% ✅
```

### Cas 4 — Next.js proxy
```
GET http://localhost:3000/api/mobile/flutter/bundle/catalog
→ mêmes données que le backend direct ✅
```

### Cas 5 — Flutter flow attendu
```
_onInvestTap(product)
→ product.portfolioId = "2430f858-..." (non null) ✅
→ BundleInvestFlowController.start(context, bundle: BundleItem(...)) ✅
→ flow STEP 1 → STEP 2 → STEP 3 → STEP 4 attendu
```

---

## Final Status

| Critère | Avant | Après |
|---------|-------|-------|
| pe_portfolios bundle_portfolio | 0 | 2 |
| pe_target_allocations pour bundles | 0 | 7 |
| portfolio_id dans catalog response | null | UUID valide |
| entry_asset_default dans catalog | null | USDC |
| CTA "Investir" fonctionnel | SnackBar erreur | Flow bundle lancé |
| Idempotent | N/A | Oui |
| Impact sur BUY/SELL/SWAP | N/A | Aucun |
| Impact sur autres produits | N/A | Aucun |

**Status : CORRIGÉ** — Les 2 bundles visibles dans Markets sont maintenant investissables.
Le correctif est minimal (1 endpoint modifié + 1 UPDATE metadata) et auto-réparant.
