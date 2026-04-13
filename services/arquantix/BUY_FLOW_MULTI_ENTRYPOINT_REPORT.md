# BUY Flow Multi-Entrypoint Report

## Executive Summary

Le flow BUY multi-step a été étendu pour supporter deux modes d'entrée :

1. **Cible connue** — depuis un wallet crypto ou une page instrument. Le flow démarre directement à STEP 1 (sélection du compte source). Aucune régression.

2. **Cible inconnue** — depuis un point d'entrée global (bouton "Échanger" sur All Crypto, ou tout futur point d'entrée). Le flow démarre à STEP 0 (sélection de l'asset cible), puis enchaîne vers le flow existant.

Zéro duplication de code. L'orchestrateur `BuyFlowController` expose deux méthodes statiques selon le contexte.

## Flow Architecture

```
STEP 0 (optionnel)          STEP 1              STEP 2           STEP 3           STEP 4
Asset Selection       →   Source Selection   →  Amount Entry  →  Confirmation  →  Processing/Success
(full-height page)        (full-height page)    (full-height)    (full-height)    (bottom sheet)
```

- **Cas A** (asset connu) : `BuyFlowController.start()` → STEP 1 → 2 → 3 → 4
- **Cas B** (asset inconnu) : `BuyFlowController.startWithoutTarget()` → STEP 0 → 1 → 2 → 3 → 4

## Step 0 — Asset Selection

### Fichier créé
`mobile/lib/features/wallet/presentation/screens/buy_flow/buy_flow_asset_selection_screen.dart`

### Comportement
- Affiche la question "Que souhaitez-vous acheter ?"
- Charge les assets disponibles depuis l'API market-data (`getMarketSummary`) pour les symboles supportés par l'exchange engine : BTC, ETH, SOL, XRP, ADA
- Chaque ligne affiche : logo, nom, symbole, prix live, variation 24h (avec couleur verte/rouge)
- Utilise `TransactionTile` + `TransactionAvatar` du Design System
- Couleurs de marque crypto via `AppColors.cryptoAssetBrand`
- Au clic sur un asset → push vers `BuyFlowSourceSelectionScreen` avec les données de l'asset sélectionné

### Fallback
Si l'API market-data échoue, affiche la liste des 5 assets supportés sans prix ni variation, permettant quand même la sélection.

### Layout
- Page standard avec `AppTopNavBar` (bouton back uniquement)
- `AppPageTitle('Investir')`
- Typographie DS (`AppTypography.titleLarge` bold pour la question)
- Card englobante avec `borderRadius: 24`

## Reuse of Existing Steps

Le STEP 0 push un `MaterialPageRoute` vers `BuyFlowSourceSelectionScreen` (STEP 1) en passant `assetSymbol`, `assetName`, `assetLogoUrl`. Le reste du flow est 100% réutilisé sans aucune modification :

| Étape | Fichier | Modifié ? |
|-------|---------|-----------|
| STEP 1 | `buy_flow_source_selection_screen.dart` | Non |
| STEP 2 | `buy_flow_amount_screen.dart` | Non |
| STEP 3 | `buy_flow_confirmation_screen.dart` | Non |
| STEP 4 | `buy_flow_processing_sheet.dart` | Non |

## Entry Point Handling

### BuyFlowController (modifié)

Deux méthodes statiques :

| Méthode | Paramètres | Démarre à | Usage |
|---------|-----------|-----------|-------|
| `start()` | `assetSymbol`, `assetName`, `assetLogoUrl?` | STEP 1 | Wallet detail, instrument detail |
| `startWithoutTarget()` | aucun | STEP 0 | All Crypto, entrées globales |

### Points d'entrée intégrés

| Écran | Bouton | Méthode appelée | Refresh post-buy |
|-------|--------|-----------------|------------------|
| `CryptoWalletDetailScreen` | "Acheter" | `BuyFlowController.start()` | `_load()` + `_loadHeroSparkline()` |
| `CryptoDetailScreen` (Markets) | "Acheter" | `BuyFlowController.start()` | `_loadInitial()` |
| `AllCryptoPositionsScreen` | "Échanger" | `BuyFlowController.startWithoutTarget()` | `_load(forceRefresh: true)` + `_loadHeroSparkline()` |

## Navigation Logic

### Propagation du résultat

Chaque écran du flow propage le résultat `true` (buy exécuté) via `Navigator.pop(true)` en cascade :

```
STEP 4 pop(true) → STEP 3 pop(true) → STEP 2 pop(true) → STEP 1 pop(true) → STEP 0 pop(true) → Caller
```

### Retour arrière

- Chaque étape a un bouton back qui fait `Navigator.pop(false)` ou `Navigator.pop()`
- Depuis STEP 1, le back revient à STEP 0 (si flow global) ou ferme le flow (si asset connu)
- Le contexte est conservé entre les étapes via les paramètres passés aux constructeurs

### Fermeture globale

- Le bouton back de la première étape visible ferme le flow complet
- Aucune perte de contexte lors de la navigation arrière entre étapes

## Backend / Data Source Reuse

### Assets disponibles
- Source : `MarketDataApi.getMarketSummary(symbols: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT'])`
- Aligné avec `SUPPORTED_ASSETS` de l'exchange engine (`api/services/exchange/assets.py`)
- Prix et variations 24h en temps réel
- Logos résolus via `Config.resolveLogoUrl()`

### Flow d'achat
- 100% réutilisation du backend existant : `CashApi`, `ExchangeApi.previewBuy`, `ExchangeApi.executeBuy`
- Aucune duplication de logique pricing
- Aucun nouvel endpoint backend nécessaire

## Validation Scenarios

### Cas 1 — Entrée depuis wallet BTC
- ✅ Ouvrir le flow depuis le wallet BTC
- ✅ STEP 0 est sautée
- ✅ Arrivée directe à STEP 1 ("À partir de quel compte souhaitez-vous acheter du Bitcoin ?")
- ✅ Flow complet : source → montant → confirmation → processing → success
- ✅ Refresh du wallet après succès

### Cas 2 — Entrée depuis All Crypto / Échanger
- ✅ Ouvrir le flow via le bouton "Échanger"
- ✅ STEP 0 affiche "Que souhaitez-vous acheter ?" avec les 5 assets
- ✅ Choix d'un asset → passage à STEP 1
- ✅ Flow complet identique au cas 1 ensuite
- ✅ Refresh de All Crypto après succès

### Cas 3 — Entrée depuis page instrument (Markets)
- ✅ Bouton "Acheter" sur la page détail crypto
- ✅ STEP 0 est sautée (asset connu)
- ✅ Flow complet
- ✅ Refresh de la page instrument après succès

### Cas 4 — Retour arrière
- ✅ Depuis STEP 1 en flow global → retour à STEP 0
- ✅ Depuis STEP 1 en flow wallet → fermeture du flow
- ✅ Depuis STEP 0 → fermeture du flow
- ✅ Aucune perte de contexte

### Cas 5 — Continuité du flow
- ✅ Après choix de l'asset et du compte source, le reste fonctionne identiquement
- ✅ Preview backend, exécution, success, refresh — tout inchangé

## Files Modified / Created

| Fichier | Action |
|---------|--------|
| `buy_flow/buy_flow_asset_selection_screen.dart` | **Créé** — STEP 0 |
| `buy_flow/buy_flow_controller.dart` | **Modifié** — ajout `startWithoutTarget()` |
| `all_crypto_positions_screen.dart` | **Modifié** — branchement bouton "Échanger" |
| `crypto_detail_screen.dart` (Markets) | **Modifié** — branchement bouton "Acheter" |

## Final Status

✅ **Complet** — Le flow BUY multi-step supporte désormais plusieurs points d'entrée avec zéro duplication de code et une architecture extensible pour de futurs entry points.
