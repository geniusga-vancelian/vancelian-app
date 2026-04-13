# Bundle Entrypoints Fix — Diagnostic & Correction Report

## Executive Summary

Les entry points bundle dans l'app ne fonctionnaient pas à cause d'un **mismatch entre la source de données utilisée pour afficher les bundles** (catalogue PE générique) **et les données nécessaires au flow d'investissement** (`portfolioId`, `status`, `entryAssetDefault`).

**Root cause** : l'endpoint catalogue PE (`/api/portfolio-engine/product-catalog`) ne retournait ni `status`, ni `portfolio_id`, ni `entry_asset_default` en top-level. Le Flutter parsait ces champs comme `null`, ce qui :
1. Rendait `_canInvest()` toujours `false` (pas de `portfolioId`) → CTA "Investir" inactif
2. Filtrait tous les bundles dans STEP 0 (`status == 'active'` sur `null`) → "Aucun bundle disponible"

**Correctifs appliqués** :
- Enrichissement du backend catalog avec `status`, `entry_asset_default`, `entry_assets_allowed`
- Nouvel endpoint `GET /api/app/bundle/catalog` enrichi avec le `portfolio_id` du client
- Suppression du bouton global "Investir dans un bundle" non désiré
- Harmonisation des sources de données Markets ↔ STEP 0

---

## Root Cause Analysis

### Le mismatch

| Champ | Retourné par le catalog | Nécessaire au flow | Conséquence |
|-------|------------------------|--------------------|-------------|
| `portfolio_id` | Non (client-specific) | Oui (BundleItem) | `_canInvest()` → `false` → CTA mort |
| `status` | Non (implicitement `active`) | Oui (filtre STEP 0) | `.where(status == 'active')` → 0 résultat |
| `entry_asset_default` | Dans `metadata{}` seulement | Oui (top-level) | Toujours `null` en Flutter |
| `entry_assets_allowed` | Dans `metadata{}` seulement | Oui (top-level) | Toujours `null` en Flutter |

### Pourquoi 2 bundles visibles mais 0 investissable

- **Markets** : filtre par `displayConfigs.containsKey(productCode)` → 2 bundles affichés
- **CTA "Investir"** : conditionné à `_canInvest(p)` = `product.portfolioId != null` → toujours `null` → **CTA jamais activé**
- **STEP 0** : filtre `items.where((i) => i.status == 'active')` → `status` toujours `null` → **liste vide**

---

## Markets Bundle Data Source

### Avant (cassé)

```
Flutter → GET http://localhost:8000/api/portfolio-engine/product-catalog?product_type=crypto_bundle
         → Réponse SANS portfolio_id, SANS status, SANS entry_asset_default top-level
         → _canInvest() = false → CTA inactif
```

### Après (corrigé)

```
Flutter → GET http://nextjs/api/mobile/flutter/bundle/catalog
         → Proxy → GET http://fastapi/api/app/bundle/catalog
         → Réponse AVEC portfolio_id, status, entry_asset_default, entry_assets_allowed
         → _canInvest() = true → CTA actif
         → Fallback sur l'ancien catalog si erreur réseau
```

---

## STEP 0 Data Source

### Avant (cassé)

```dart
final items = await _catalogApi.getCatalog(productType: 'crypto_bundle');
_bundles = items.where((i) => i.status == 'active').toList();
// status toujours null → filtre supprime tout → "Aucun bundle disponible"
```

### Après (corrigé)

```dart
List<ProductCatalogItem> items;
try {
  items = await _catalogApi.getBundleCatalog(); // enrichi
} catch (_) {
  items = await _catalogApi.getCatalog(productType: 'crypto_bundle'); // fallback
}
_bundles = items; // plus de filtre cassé, le backend filtre déjà par active
```

**Vérité unique** : Markets et STEP 0 appellent le même endpoint enrichi `getBundleCatalog()`.

---

## Removed Global CTA

Le bouton `OutlinedButton.icon("Investir dans un bundle")` sous la section Crypto Bundles dans `markets_screen.dart` a été entièrement supprimé :

- Bouton supprimé du `build()` method
- Méthode `_onInvestInBundle()` supprimée
- Import `BundleInvestFlowController` retiré de `markets_screen.dart`

Ce bouton n'avait jamais fonctionné correctement (lançait STEP 0 qui affichait "Aucun bundle disponible").

---

## Fixed Bundle Card Entrypoints

### Comment ça fonctionne maintenant

1. `CryptoBundlesWidget` appelle `getBundleCatalog()` (enrichi avec `portfolio_id`)
2. Pour chaque bundle avec `portfolioId` non-null, `_canInvest(p)` retourne `true`
3. Le CTA "Investir" sur la carte appelle `_onInvestTap(p)` qui construit un `BundleItem` complet
4. `BundleInvestFlowController.start(context, bundle: bundle)` lance le flow à STEP 1

### Fallback gracieux

Si l'endpoint enrichi échoue (réseau, etc.), le widget utilise le catalog générique en fallback. Dans ce cas, `portfolioId` reste `null` et le CTA "Investir" ne s'affiche pas — mais les cartes bundle restent visibles et cliquables pour naviguer vers le détail.

---

## Data Model / Mapping Adjustments

### Backend `catalog.py` — `ProductCatalogItem`

Ajout de 3 champs au schéma Pydantic :

```python
status: str = "active"
entry_asset_default: Optional[str] = None
entry_assets_allowed: list[str] = Field(default_factory=list)
```

Peuplés dans `get_public_catalog()` depuis `product.status` et `product.metadata_`.

### Backend `router.py` — Nouvel endpoint

```
GET /api/app/bundle/catalog
```

- Appelle `CatalogService.get_public_catalog(db, product_type="crypto_bundle")`
- Joint les portfolios du client bootstrap via `Portfolio.origin_product_id`
- Retourne un `portfolio_id` pour chaque produit ayant un portfolio actif

### Flutter `product_catalog_api.dart`

- `fromJson()` : lecture de `entry_asset_default` et `entry_assets_allowed` depuis `metadata` en fallback
- Ajout de `_nonEmpty()` helper pour simplifier le parsing nullable
- Ajout de `getBundleCatalog()` : appelle le nouvel endpoint enrichi

### Flutter `config.dart`

- Ajout de `bundleCatalogUrl`

### Proxy Next.js

- `web/src/app/api/mobile/flutter/bundle/catalog/route.ts` → proxy GET vers `/api/app/bundle/catalog`

---

## Validation Scenarios

### Cas 1 — Bundle card dans Markets ✅
- 2 bundles visibles
- CTA "Investir" actif sur chaque carte (si `portfolioId` présent)
- Clic → flow bundle s'ouvre à STEP 1 (bundle connu)

### Cas 2 — Tap sur carte ✅
- La navigation vers ProductPreviewScreen (détail) fonctionne toujours
- CTA "Investir" = action distincte du tap carte

### Cas 3 — STEP 0 ✅
- Même source de données que Markets (enrichi)
- Liste cohérente avec les bundles réellement visibles
- Plus de "Aucun bundle disponible" si des bundles existent

### Cas 4 — Aucun bundle réellement investissable ✅
- Si aucun produit bundle n'existe → section masquée (SizedBox.shrink)
- Si bundles existent mais sans portfolio → cartes visibles, CTA absent, navigation détail ok

### Cas 5 — Non-régression ✅
- BUY / SELL / SWAP : inchangés
- Product catalog générique : inchangé (champs ajoutés rétro-compatibles)
- Bundle invest flow (STEP 1→4) : inchangé
- Bundle preview : inchangé

---

## Final Status

| Élément | Statut |
|---------|--------|
| Root cause identifiée | ✅ |
| Backend `ProductCatalogItem` enrichi | ✅ |
| Endpoint `GET /api/app/bundle/catalog` | ✅ |
| Proxy Next.js | ✅ |
| Flutter `getBundleCatalog()` | ✅ |
| Flutter `fromJson()` fixé | ✅ |
| Global CTA supprimé | ✅ |
| CryptoBundlesWidget → enriched catalog | ✅ |
| BundleSelectionScreen → enriched catalog | ✅ |
| Flutter analyze | ✅ 0 errors |

**Résultat** : vérité unique entre bundles visibles et bundles investissables.
