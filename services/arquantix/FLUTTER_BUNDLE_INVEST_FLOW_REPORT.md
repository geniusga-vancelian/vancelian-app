# Flutter Bundle Invest Flow — Implementation Report

## Executive Summary

Le flow Flutter "Invest in Bundle" est implémenté en 5 étapes (STEP 0→4), calqué exactement sur les patterns UX existants BUY/SELL. Le flow est backend-driven : aucune logique d'allocation ou comptable n'est côté Flutter. L'app pilote uniquement le moteur Bundle Engine Phase 2 via les endpoints `POST /bundle/invest` et `GET /bundle/{id}/status`.

### Fichiers créés / modifiés

| Fichier | Action | Rôle |
|---------|--------|------|
| `mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_invest_flow_controller.dart` | **Créé** | Controller + data carriers (BundleItem, BundleSourceAccount, BundleFlowHeaderDisk) |
| `mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_selection_screen.dart` | **Créé** | STEP 0 — Sélection du bundle |
| `mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_source_selection_screen.dart` | **Créé** | STEP 1 — Sélection du compte source |
| `mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_amount_entry_screen.dart` | **Créé** | STEP 2 — Saisie du montant |
| `mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_confirmation_screen.dart` | **Créé** | STEP 3 — Confirmation |
| `mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_processing_sheet.dart` | **Créé** | STEP 4 — Processing / Success / Partial / Error bottom sheet |
| `mobile/lib/features/wallet/data/bundle_api.dart` | **Créé** | API client (BundleApi, BundleInvestResult, BundleStatusResult) |
| `mobile/lib/core/config.dart` | **Modifié** | Ajout `bundleInvestUrl` et `bundleStatusUrl` |
| `mobile/lib/features/markets/data/product_catalog_api.dart` | **Modifié** | Ajout champs `portfolioId`, `status`, `entryAssetDefault`, `entryAssetsAllowed` |
| `web/src/app/api/mobile/flutter/bundle/invest/route.ts` | **Créé** | Proxy Next.js → FastAPI `/api/app/bundle/invest` |
| `web/src/app/api/mobile/flutter/bundle/[portfolioId]/status/route.ts` | **Créé** | Proxy Next.js → FastAPI `/api/app/bundle/{id}/status` |

---

## Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  BundleInvestFlowController                   │
│                                                              │
│  start(bundle)          → STEP 1 (bundle connu)              │
│  startWithoutTarget()   → STEP 0 (bundle inconnu)            │
└──────────────────────────────────────────────────────────────┘

STEP 0: BundleSelectionScreen
  ↓ sélection d'un bundle
STEP 1: BundleSourceSelectionScreen
  ↓ sélection du compte source (EUR / USDC / EURC)
STEP 2: BundleAmountEntryScreen
  ↓ saisie du montant + continuer
STEP 3: BundleConfirmationScreen
  ↓ confirmer → ouvre bottom sheet
STEP 4: BundleProcessingSheet
  ↓ processing → success → pop(true) auto
  ↓               partial → bouton Fermer → pop(true)
  ↓               error → bouton Fermer → pop(false)

Résultat : pop(true) remonte à travers toute la stack Navigator
```

### Data Carriers

- **`BundleItem`** : portfolioId, productId, name, description, entryAssetDefault, entryAssetsAllowed, allocations
- **`BundleSourceAccount`** : type (fiat/crypto), label, balance, currency, icon
- **`BundleAllocationTarget`** : asset, weight

### Navigation Pattern

Identique à BUY/SELL : chaque étape `push<bool>(MaterialPageRoute)` puis `.then((result) { if (result == true) pop(true) })`. Le résultat cascade jusqu'au caller initial.

---

## Step 0 — Bundle Selection

**Fichier** : `bundle_selection_screen.dart`

- Scaffold + AppTopNavBar (back)
- AppPageTitle + question dynamique
- Charge les bundles via `ProductCatalogApi.getCatalog(productType: 'crypto_bundle')`
- Filtre sur `status == 'active'`
- Chaque bundle affiché en card Material avec icône, nom, allocation summary, chevron
- Au tap → construit un `BundleItem` et navigue vers STEP 1
- Sauté si le flow est lancé via `BundleInvestFlowController.start(bundle: ...)`

---

## Step 1 — Source Selection

**Fichier** : `bundle_source_selection_screen.dart`

- Même pattern que `BuyFlowSourceSelectionScreen`
- Charge les comptes via `CashApi` (Compte Euro) et `CryptoPositionsApi` (wallets)
- Filtre les wallets crypto par `entryAssetsAllowed` du bundle (ex: USDC uniquement)
- Affiche les comptes en cards avec `TransactionTile` + `TransactionAvatar`
- Balance affichée en EUR ou en crypto selon le type
- Au tap → navigue vers STEP 2

---

## Step 2 — Amount Entry

**Fichier** : `bundle_amount_entry_screen.dart`

- Même pattern que `BuyFlowAmountScreen`
- Header avec BundleFlowHeaderDisk (back) + titre "Montant" + icône bundle
- Source pill (compte sélectionné + balance)
- Question : "Combien souhaitez-vous investir dans {bundle name} ?"
- Montant en grand (48px) avec symbole devise
- TextField invisible + clavier natif (decimal)
- SingleDecimalFormatter (virgule française, max 2 décimales)
- Validation over-balance en rouge + banner d'erreur
- Note contextuelle : "Converti via USDC puis alloué" (fiat) ou "Alloué depuis votre wallet USDC" (crypto)
- Bouton "Continuer" activé quand montant > 0 et ≤ balance
- Au tap → navigue vers STEP 3

---

## Step 3 — Confirmation

**Fichier** : `bundle_confirmation_screen.dart`

- Même pattern que `BuyFlowConfirmationScreen`
- Header avec back disk + titre "Confirmation" + icône bundle
- Texte hero : "Vous êtes sur le point d'investir {montant} dans {bundle}"
- `TableInformationModule` avec :
  - Bundle
  - Compte source
  - Montant débité
  - Entry asset
  - Allocation cible (ex: "BTC 70% · ETH 30%")
- Info box indigo : explication du process (conversion → allocation, reliquat possible)
- Bottom bar : bouton retour circulaire + bouton "Confirmer l'investissement" (indigo, élevé)
- Au tap confirm → ouvre bottom sheet STEP 4

---

## Step 4 — Processing / Success

**Fichier** : `bundle_processing_sheet.dart`

Bottom sheet non-dismissible, 4 phases :

### Processing
- Cercle noir 64px avec CircularProgressIndicator blanc
- "Nous investissons dans votre bundle…"
- "Cela peut prendre quelques secondes"

### Success (status: completed)
- Cercle noir avec check blanc
- "Investissement réussi"
- Montant en hero (28px)
- "{bundle name} · via {entry_asset}"
- Nombre d'allocations réussies
- Auto-pop(true) après 2.5s

### Partial (status: partial)
- Cercle amber avec warning icon
- "Investissement partiel"
- "X sur Y allocations réussies"
- Reliquat affiché si > 0 : "Reliquat : 12.40 USDC dans le cash leg"
- Bouton "Fermer" → pop(true)

### Error (status: failed)
- Cercle noir avec close icon
- Message d'erreur humanisé
- Bouton "Fermer" (gris) → pop(false)

---

## Backend Integration

### API Client : `BundleApi`

```dart
class BundleApi {
  Future<BundleInvestResult> investInBundle({
    required String portfolioId,
    required String fundingAsset,   // "EUR" | "USDC" | "EURC"
    required double fundingAmount,
  })

  Future<BundleStatusResult> getBundleStatus({
    required String portfolioId,
  })
}
```

### Proxy Next.js

| Route Flutter | Proxy Next.js | Backend FastAPI |
|---------------|---------------|-----------------|
| `POST /api/mobile/flutter/bundle/invest` | → | `POST /api/app/bundle/invest` |
| `GET /api/mobile/flutter/bundle/{id}/status` | → | `GET /api/app/bundle/{id}/status` |

### Payload investissement

```json
{
  "portfolio_id": "uuid",
  "funding_asset": "EUR",
  "funding_amount": 1000
}
```

### Réponse

```json
{
  "status": "completed|partial|failed",
  "entry_asset": "USDC",
  "total_entry_asset_received": 998.50,
  "total_entry_asset_consumed": 998.50,
  "cash_leg_remaining": 0,
  "legs_succeeded": 2,
  "legs_failed": 0,
  "allocation_details": [...]
}
```

---

## Bundle Status Refresh

Après succès, le front peut recharger via `BundleApi.getBundleStatus(portfolioId)`.

La réponse `BundleStatusResult` contient :
- `cashLegs` : liste des PositionAtom type=cash (entry asset non alloué)
- `allocatedPositions` : liste des PositionAtom type=spot
- `totalCostBasis` : coût total du bundle

---

## Known Limitations

### 1. Points d'entrée navigation

Le flow est architecturellement prêt avec deux modes d'entrée :
- `BundleInvestFlowController.start(context, bundle: ...)` — bundle connu
- `BundleInvestFlowController.startWithoutTarget(context)` — bundle inconnu

Les points d'entrée concrets dans l'UI existante doivent encore être branchés :
- **Page bundle detail** (ProductPreviewScreen / LandingPagePreviewScreen) : la page est un builder CMS générique. Un bouton "Investir" doit être ajouté en tant que module du builder ou via un CTA fixe.
- **CryptoBundlesWidget** : possibilité d'ajouter un bouton "Investir" sous chaque card bundle.
- **Markets screen** : point d'entrée global "Investir dans un bundle".

### 2. Portfolio ID et provisioning

Le `ProductCatalogItem` expose désormais `portfolioId`, `entryAssetDefault`, et `entryAssetsAllowed`. Ces champs doivent être peuplés par le backend dans la réponse du product catalog quand le client a un bundle provisionné.

Si le client n'a pas encore de portfolio provisionné pour un bundle, le flow ne pourra pas s'exécuter (l'invest endpoint nécessite un `portfolio_id`). Une étape de provisioning automatique pourra être ajoutée en Phase 3.

### 3. EURC support

EURC est configuré comme entry asset autorisé mais n'a pas encore de données de marché de production. Le flow le supporte architecturellement.

### 4. Preview endpoint

Le flow n'utilise pas de preview bundle (contrairement au BUY flow qui a un `previewBuy`). Si un endpoint `POST /bundle/invest/preview` est ajouté au backend, le STEP 2 pourra afficher une estimation détaillée de l'allocation.

### 5. Refresh post-investissement

Le `pop(true)` cascade correctement vers le caller. Le caller doit implémenter un refresh de ses données. Le mécanisme exact dépend de la page appelante (portfolio detail, markets, etc.).

---

## Final Status

| Composant | Status |
|-----------|--------|
| `BundleInvestFlowController` | ✅ Créé |
| `BundleSelectionScreen` (STEP 0) | ✅ Créé |
| `BundleSourceSelectionScreen` (STEP 1) | ✅ Créé |
| `BundleAmountEntryScreen` (STEP 2) | ✅ Créé |
| `BundleConfirmationScreen` (STEP 3) | ✅ Créé |
| `BundleProcessingSheet` (STEP 4) | ✅ Créé |
| `BundleApi` (client) | ✅ Créé |
| `Config` (URLs) | ✅ Modifié |
| `ProductCatalogItem` (champs bundle) | ✅ Modifié |
| `ProductDetailItem` (champs bundle) | ✅ Modifié |
| Next.js proxy `/bundle/invest` | ✅ Créé |
| Next.js proxy `/bundle/{id}/status` | ✅ Créé |
| Backend tests Phase 2 | ✅ 8/8 passent |
| Flutter analyze | ✅ 0 erreur, 0 warning propre |
| BUY/SELL/SWAP non-régression | ✅ Inchangés |
| Points d'entrée navigation | ⚠️ Architecture prête, branchement UI à finaliser |
| Preview bundle | ⚠️ Pas de preview endpoint — affichage simplifié |

**Prêt pour Phase 3** : retry, rebalance, DCA, provisioning automatique, preview endpoint.
