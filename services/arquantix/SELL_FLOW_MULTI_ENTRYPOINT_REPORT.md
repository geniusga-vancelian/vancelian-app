# SELL Flow Multi-Entrypoint Report

## Executive Summary

Le flow SELL multi-step multi-entrypoint a été implémenté avec succès, en miroir de l’architecture du BUY flow. La logique métier du moteur SELL existant est respectée : le transfert du produit fiat vers le compte client se fait uniquement après exécution réussie de la vente.

## Flow Architecture

```
STEP 0 (optionnel)          STEP 1              STEP 2           STEP 3           STEP 4
Asset Selection       →   Destination       →  Amount Entry  →  Confirmation  →  Processing/Success
(wallets balance>0)        (Compte Euro)       (crypto qty)     (recap)         (bottom sheet)
```

- **Cas A** (asset connu) : `SellFlowController.start()` → STEP 1 → 2 → 3 → 4
- **Cas B** (asset inconnu) : `SellFlowController.startWithoutSourceAsset()` → STEP 0 → 1 → 2 → 3 → 4

## Step 0 — Asset Selection

### Fichier
`mobile/lib/features/wallet/presentation/screens/sell_flow/sell_flow_asset_selection_screen.dart`

### Comportement
- Affiche la question "Que souhaitez-vous vendre ?"
- Charge les positions crypto via `CryptoPositionsApi.fetchPositions()`
- N’affiche que les wallets avec `balance > 0` ou `availableBalance > 0`
- Chaque ligne : logo, nom, symbole, volume détenu, valeur estimée

### Layout
- Page standard avec `AppTopNavBar` (bouton back)
- `AppPageTitle('Vendre')`
- Utilisation de `TransactionTile` + `TransactionAvatar` du DS

### État vide
Si aucune position avec balance > 0 : message "Aucun actif à vendre" avec explication.

## Step 1 — Destination Selection

### Fichier
`mobile/lib/features/wallet/presentation/screens/sell_flow/sell_flow_destination_selection_screen.dart`

### Comportement
- Question : "Vers quel compte souhaitez-vous recevoir le produit de la vente ?"
- Pour v1 : uniquement le Compte Euro réel du client
- Charge le solde EUR via `CashApi.fetchCashData()`
- Extensible pour d’autres destinations futures

### Layout
- Même style que le BUY flow
- Card avec `TransactionTile` pour le Compte Euro

## Step 2 — Amount Entry

### Fichier
`mobile/lib/features/wallet/presentation/screens/sell_flow/sell_flow_amount_screen.dart`

### Comportement
- Saisie en **quantité crypto** (ex. 0.01 BTC)
- Question : "Combien souhaitez-vous vendre de Bitcoin ?"
- Compte de destination affiché en haut
- Montant crypto affiché en grand
- Estimation en EUR reçue sous le montant (via preview backend)

### Validation
- Montant > 0
- Montant ≤ balance crypto disponible
- Preview valide et fraîche
- Pas de loading en cours

### UX
- Clavier numérique natif
- Zone montant tappable pour ouvrir le clavier
- Focus robuste (identique au BUY flow)

## Step 3 — Confirmation

### Fichier
`mobile/lib/features/wallet/presentation/screens/sell_flow/sell_flow_confirmation_screen.dart`

### Comportement
- Phrase : "Vous êtes sur le point de vendre X BTC et de recevoir environ Y € sur votre Compte Euro"
- Tableau récap via `TableInformationModule` : Type, Asset vendu, Quantité vendue, Compte de destination, Montant brut/net, Frais, Prix estimé
- Boutons "Confirmer la vente" et "Retour"

### Sécurité
- Rafraîchissement du preview avant exécution
- Blocage si quote stale

## Step 4 — Processing and Success

### Fichier
`mobile/lib/features/wallet/presentation/screens/sell_flow/sell_flow_processing_sheet.dart`

### États
1. **Processing** : loader + "Nous traitons votre vente..."

2. **Success** : icône + "Vente effectuée" + "-X BTC" + "+ Y € reçus" + prix

3. **Error** : icône + message d’erreur + bouton "Fermer"

### Fermeture
- Après succès : fermeture automatique après 2 s
- `pop(true)` pour déclencher le refresh côté appelant

## Backend Preview and Execution Reuse

### Preview SELL
- **Nouveau** : `ExchangeService.preview_sell(db, asset, amount_crypto, currency)`
- Réutilise `_resolve_price` avec `side="sell"` (bid)
- Même logique de frais (fee_bps en EUR)
- Retourne : `estimated_fiat_gross`, `fee_amount`, `estimated_fiat_net`, `is_fresh`

### Endpoints mobile
- `POST /api/app/exchange/sell/preview` — preview
- `POST /api/app/exchange/sell` — exécution

### Proxy Next.js
- `POST /api/mobile/flutter/exchange/sell/preview`
- `POST /api/mobile/flutter/exchange/sell`

### Règle métier
Le transfert du produit fiat vers le compte client se fait uniquement **après** exécution réussie du SELL (dans la même transaction atomique).

## Navigation and Refresh

- `pop(true)` propagé de STEP 4 → 3 → 2 → 1 → 0 → caller
- Retour arrière entre étapes
- Fermeture globale via bouton back
- Refresh immédiat après succès : `_load()`, `_loadHeroSparkline()` sur les écrans wallet et All Crypto

## Entry Points

| Écran | Bouton | Méthode | Démarre à |
|-------|--------|---------|-----------|
| `CryptoWalletDetailScreen` | "Vendre" | `SellFlowController.start()` | STEP 1 |
| `AllCryptoPositionsScreen` | "Vendre" | `SellFlowController.startWithoutSourceAsset()` | STEP 0 |

## Known Limitations

- **Destination v1** : uniquement Compte Euro
- **Saisie** : v1 en quantité crypto uniquement (pas de saisie en valeur fiat)
- **Swap** : non supporté (crypto → crypto)

## Final Status

- Flow SELL multi-step complet
- Support multi-entrypoint (asset connu / inconnu)
- Backend preview et exécution réutilisés
- UX alignée avec le BUY flow
- Intégration wallet detail et All Crypto
