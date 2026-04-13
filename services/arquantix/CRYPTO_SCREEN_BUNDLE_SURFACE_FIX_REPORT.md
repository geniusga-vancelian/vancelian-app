# CRYPTO_SCREEN_BUNDLE_SURFACE_FIX_REPORT

## Executive Summary

Après un investissement bundle, les actifs achetés (BTC, ETH, etc.) apparaissaient uniquement
dans la section "Mes crypto" de la page Crypto, confondus avec les positions spot directes.
Il n'existait aucune surface dédiée aux bundles dans la page Crypto.

**Correctif appliqué** : une nouvelle section **"Mes bundles"** a été ajoutée à la page Crypto,
alimentée par un nouvel endpoint backend dédié (`GET /api/app/bundle/my-bundles`) qui retourne
les bundle portfolios du client avec positions, valorisation marché et performance.

La section affiche chaque bundle comme une entité distincte avec son nom, sa valeur, sa
performance, et un accès au détail produit. La section "Mes crypto" continue de fonctionner
normalement en dessous.

---

## Root Cause

L'écran `AllCryptoPositionsScreen` utilisait uniquement `CryptoPositionsApi.fetchPositions()`
qui retourne les positions consolidées depuis `crypto_positions` — sans distinction entre
positions directes et overlay bundle du Portfolio Engine.

Le Bundle Engine Phase 2 stocke les allocations bundle dans `pe_position_atoms` (overlay),
mais `crypto_positions` est la vue consolidée client. Aucune surface ne lisait les données
PE bundle pour les afficher distinctement.

**Conséquence** : l'utilisateur voyait ses BTC et ETH augmenter après un investissement
bundle, mais sans comprendre que ces positions provenaient d'un bundle.

---

## Current Crypto Screen Data Model

### Source de données (AVANT)
```
AllCryptoPositionsScreen
  → CryptoPositionsApi.fetchPositions()
  → GET /api/mobile/flutter/crypto-positions
  → retourne CryptoPositionsData { summary, positions: [CryptoPositionItem] }
```

### Limites
- Vue consolidée `crypto_positions` : ne distingue pas spot direct vs overlay bundle
- Aucun appel aux données PE / bundle
- Aucune section bundle dans le layout

---

## Bundle Data Source

### Nouvel endpoint backend

**`GET /api/app/bundle/my-bundles`** (`api/services/test_clients/router.py`)

Retourne les bundle portfolios du client avec valorisation live.

**Logique** :
1. Charge les `pe_portfolios` du client (type `bundle_portfolio`, status `active`)
2. Pour chaque portfolio, charge les `pe_position_atoms` (status `open`)
3. Pour chaque atom, résout le prix live via `price_bridge.get_instrument_price()`
   (PE instrument → `market_data_instrument_id` → `market_data_latest_quotes`)
4. Calcule `total_market_value` = Σ(quantity × price) et `performance_pct`

**Réponse** :
```json
{
  "bundles": [
    {
      "portfolio_id": "2430f858-...",
      "portfolio_name": "Crypto Bundle Top 2",
      "origin_product_id": "9426e035-...",
      "status": "active",
      "assets_count": 2,
      "total_cost_basis": 1000.00,
      "total_market_value": 1156.43,
      "performance_pct": 15.64,
      "has_holdings": true,
      "positions": [
        {
          "asset": "BTC",
          "quantity": 0.01145633,
          "cost_basis": 699.93,
          "market_value": 809.63,
          "price_usd": 70670.54,
          "position_type": "spot"
        },
        ...
      ]
    }
  ],
  "total": 2
}
```

### Proxy Next.js

`web/src/app/api/mobile/flutter/bundle/my-bundles/route.ts`
→ proxy vers `GET $BACKEND_URL/api/app/bundle/my-bundles`

### Client Flutter

`BundleApi.getMyBundles()` → `List<MyBundleSummary>`

Modèle `MyBundleSummary` :
- `portfolioId`, `portfolioName`, `originProductId`
- `status`, `assetsCount`, `hasHoldings`
- `totalCostBasis`, `totalMarketValue`, `performancePct`
- `positions: List<BundlePositionInfo>`
- `spotPositions` (getter filtré par `position_type == 'spot'`)

### Fix data : `market_data_instrument_id` alignment

Les instruments PE (`pe_instruments`) référençaient de mauvais `market_data_instrument_id`
dans leurs metadata (IDs obsolètes). Corrigé en base :
```
BTC-SPOT: 46 → 86, ETH-SPOT: 47 → 87, SOL-SPOT: 48 → 88
XRP-SPOT: 49 → 89, BNB-SPOT: 50 → 90, USDC-SPOT: 53 → 93
```
Ceci permet à `price_bridge.get_instrument_price()` de résoudre les prix live correctement.

---

## New "Mes bundles" Section

### Placement
La section "Mes bundles" apparaît **au-dessus** de "Mes crypto" dans la page Crypto.
Elle n'est visible que si au moins un bundle a des holdings (`has_holdings == true`).

### Layout
```
┌─────────────────────────────────┐
│            HERO                 │
│   Chart + Total + Actions       │
├─────────────────────────────────┤
│  Mes bundles                    │  ← titre section (visible si bundles existent)
│  ┌───────────────────────────┐  │
│  │ 🟣 Crypto Bundle Top 2   │  │  ← TransactionTile avec avatar, nom,
│  │   2 actifs    1 157 €     │  │     sous-titre (nb assets), valeur, perf%
│  │              +15.64 %     │  │
│  └───────────────────────────┘  │
│                                 │
│  Mes crypto                     │  ← titre section (visible si bundles + crypto existent)
│  ┌───────────────────────────┐  │
│  │ ₿ Bitcoin                 │  │  ← positions spot classiques (inchangé)
│  │   0.01145 BTC  809 €      │  │
│  │ ◆ Ethereum               │  │
│  │   0.16120 ETH  347 €      │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### Composants DS utilisés
- **`TransactionTile`** : ligne bundle avec avatar, titre, sous-titre, valeur, perf
- **`TransactionAvatar`** : icône pie_chart violet (#6366F1) pour les bundles
- **`AppTypography.headlineSmall`** : titres de section
- **`AppColors.cardBackground`** + `borderRadius(24)` : carte conteneur
- **Box shadow** : `alpha: 0.06, blur: 8` (identique aux positions crypto)

### Comportement
- Le titre "Mes crypto" n'apparaît que si des bundles ET des crypto existent
  (quand il n'y a pas de bundles, pas besoin de séparer les sections)
- Si aucun bundle n'a de holdings, la section est invisible
- Si aucune position et aucun bundle, le message "Aucune position crypto" s'affiche

---

## Spot vs Bundle Display Strategy

**Stratégie retenue : Option A (minimal safe)**

- "Mes crypto" reste la vue consolidée existante (inchangée)
- "Mes bundles" ajouté au-dessus comme section distincte
- Pas de déduction des atoms bundle de la vue spot

**Limite connue** : les actifs détenus via bundle (BTC, ETH) apparaissent aussi dans
"Mes crypto" car `crypto_positions` est la vue consolidée. L'utilisateur voit les
mêmes actifs dans les deux sections.

**Raison du choix** : déduire les atoms bundle des positions spot nécessiterait de
modifier la logique du backend `crypto-positions` et de connaître les quantités PE
atom par asset. Cela risquerait de casser la comptabilité et les autres surfaces.
Le choix est documenté pour un futur raffinement (Option B).

---

## Navigation / Detail Behavior

- Chaque bundle tile a un **chevron** et un **onTap**
- Le tap ouvre `ProductPreviewScreen.open(context, originProductId)`
  → page détail produit existante avec modules CMS, allocations, et bouton "Investir"
- Si `originProductId` est absent (ne devrait pas arriver), le tap est ignoré

**Limite** : `ProductPreviewScreen` affiche la définition produit (allocations cibles,
description marketing) mais pas les holdings réels de l'utilisateur. Un futur
`BundleHoldingsScreen` dédié pourrait être créé pour afficher les positions avec
leur performance individuelle.

---

## Validation Scenarios

### Cas 1 — Section "Mes bundles" visible après investissement
```
AllCryptoPositionsScreen._load()
  → BundleApi.getMyBundles()
  → Crypto Bundle Top 2 : has_holdings=true, cost=$1000, market=$1157
  → activeBundles = [Crypto Bundle Top 2]
  → _buildBundlesSection() affiché ✅
```

### Cas 2 — Nom du bundle visible
```
TransactionTile.title = "Crypto Bundle Top 2"
TransactionTile.subtitle = "2 actifs"
TransactionTile.rightPrimary = "1 157 €"
TransactionTile.rightSecondary = "+15.64 %"  ✅
```

### Cas 3 — Bundle ouvrable en détail
```
onTap → ProductPreviewScreen.open(context, "9426e035-...")
→ page détail bundle chargée ✅
```

### Cas 4 — Section "Mes crypto" inchangée
```
CryptoPositionsApi.fetchPositions() → même réponse qu'avant
TransactionTile pour chaque CryptoPositionItem → inchangé ✅
```

### Cas 5 — Non-régression BUY / SELL / SWAP
```
Aucune modification de :
  - ExchangeApi
  - BuyFlowController
  - SellAllConfirmationScreen
  - SwapScreen
  - crypto_positions_api.dart
→ non-régression garantie ✅
```

### Cas 6 — Bundle sans holdings invisible
```
Crypto Bundle TOP 5 : has_holdings=false
→ filtré par activeBundles.where((b) => b.hasHoldings)
→ non affiché ✅
```

### Cas 7 — Quotes indisponibles
```
Si market_data_latest_quotes vide ou instrument non lié :
→ market_value = null, performance_pct = null
→ affiche total_cost_basis comme valeur de fallback
→ pas de crash, pas de perf affichée ✅
```

---

## Files Modified

| Fichier | Changement |
|---------|------------|
| `api/services/test_clients/router.py` | Nouvel endpoint `GET /api/app/bundle/my-bundles` |
| `web/src/app/api/mobile/flutter/bundle/my-bundles/route.ts` | Nouveau proxy Next.js |
| `mobile/lib/core/config.dart` | Ajout `myBundlesUrl` |
| `mobile/lib/features/wallet/data/bundle_api.dart` | Ajout `MyBundleSummary`, `getMyBundles()` |
| `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` | Section "Mes bundles" + "Mes crypto" labels |

**DB data fixes** (non-code) :
- `pe_instruments` metadata `market_data_instrument_id` corrigé pour BTC/ETH/SOL/XRP/BNB/USDC

---

## Final Status

| Critère | Avant | Après |
|---------|-------|-------|
| Section "Mes bundles" dans Crypto | Absente | Visible |
| Bundle identifié par son nom | Non | Oui |
| Valeur marché bundle | Non disponible | Affichée (avec fallback cost basis) |
| Performance bundle | Non disponible | Affichée si quotes disponibles |
| Navigation détail bundle | Inexistante | ProductPreviewScreen |
| Séparation visuelle spot/bundle | Non | Oui (sections distinctes) |
| Impact sur "Mes crypto" | N/A | Aucun |
| Impact sur BUY/SELL/SWAP | N/A | Aucun |
| Flutter analyze | 1 info pré-existant | 1 info pré-existant |

**Status : LIVRÉ** — La section "Mes bundles" est opérationnelle sur la page Crypto avec
données live PE, valorisation marché, et navigation vers le détail produit.
