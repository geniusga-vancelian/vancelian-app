# BUY Multi-Step Flow Report

## Executive Summary

Refonte du flow d'achat crypto monolithique en un parcours multi-étapes premium en 4 steps :

1. **Source Account Selection** — modal full height
2. **Amount Entry** — modal full height
3. **Confirmation Recap** — modal full height
4. **Processing + Success** — bottom sheet compacte

L'ancien `BuyAssetModalScreen` (écran unique) est conservé intact mais n'est plus utilisé.
Le nouveau flow est orchestré par `BuyFlowController` et réutilise 100 % du backend existant (preview + buy réels).

## Flow Architecture

```
CryptoWalletDetailScreen
  └─ BuyFlowController.start()
       └─ STEP 1: BuyFlowSourceSelectionScreen  (full-height modal, slide-up)
            └─ STEP 2: BuyFlowAmountScreen       (full-height modal, slide-right)
                 └─ STEP 3: BuyFlowConfirmationScreen (full-height modal, slide-right)
                      └─ STEP 4: BuyFlowProcessingSheet (bottom sheet, non full-height)
                           ├─ Processing state (spinner)
                           └─ Success state (check + recap, auto-close 2s)
```

### Navigation

- **Forward**: chaque step `push` le suivant avec animation slide appropriée
- **Back**: bouton retour ou swipe back sur chaque step
- **Close**: bouton ✕ sur Step 1 ferme tout le flow
- **Success propagation**: Step 4 pop `true` → Step 3 pop `true` → Step 2 pop `true` → Step 1 pop `true` → retour à `CryptoWalletDetailScreen` avec refresh

### Fichiers créés

| Fichier | Rôle |
|---------|------|
| `buy_flow/buy_flow_controller.dart` | Entry point + shared widgets (`BuyFlowHeaderDisk`, `BuyFlowSourceAccount`) |
| `buy_flow/buy_flow_source_selection_screen.dart` | Step 1 — sélection du compte source |
| `buy_flow/buy_flow_amount_screen.dart` | Step 2 — saisie du montant + preview live |
| `buy_flow/buy_flow_confirmation_screen.dart` | Step 3 — récapitulatif avant exécution |
| `buy_flow/buy_flow_processing_sheet.dart` | Step 4 — bottom sheet processing/success/error |

### Fichier modifié

| Fichier | Changement |
|---------|-----------|
| `crypto_wallet_detail_screen.dart` | Import `BuyFlowController` au lieu de `BuyAssetModalScreen` ; `_openBuyModal()` appelle `BuyFlowController.start()` |

## Step 1 — Source Selection

### Écran

Modal full height avec header (✕ close + titre "Acheter" + icône asset cible).

### Titre dynamique

"À partir de quel compte souhaitez-vous acheter du Bitcoin ?"

### Comptes affichés

1. **Comptes fiat** : Compte Euro (chargé via `CashApi.fetchCashData()`) — tappable, navigable
2. **Wallets crypto** : positions du client (via `CryptoPositionsApi.fetchPositions()`) dont le solde > 0 et ≠ asset cible — affichés avec label "Swap (bientôt disponible)", non tappables en v1

### Chaque row affiche

- Icône (fond bleu + € pour fiat, logo crypto pour les wallets)
- Nom du compte / wallet
- Balance disponible à droite
- Chevron pour les comptes fiat actifs

### Au clic

→ push Step 2 avec le `BuyFlowSourceAccount` sélectionné

## Step 2 — Amount Entry

### Écran

Modal full height avec header (← back + titre "Montant" + icône asset).

### Éléments

- Pill source account (style identique au dashboard : icône + label + balance droite)
- Question "Combien souhaitez-vous acheter de {AssetName} ?" (titleLarge, w700, noir)
- Montant en gros (heroAmount, 48px) avec clavier numérique natif
- Équivalent crypto via **backend preview** (`ExchangeApi.previewBuy`) avec debounce 500ms
- Pas de calcul local simplifié

### Validation

Bouton "Continuer" actif si :
- montant > 0
- montant ≤ balance source
- preview valide (pas d'erreur, pas en loading)

### Navigation

Le bouton "Continuer" **ne fait PAS l'achat** — il push Step 3.

## Step 3 — Confirmation

### Écran

Modal full height, purement informatif (pas de clavier).

### Contenu

- Titre : "Vous êtes sur le point d'acheter"
- Montant crypto en gros : "0.00162464 BTC"
- Équivalent fiat : "≈ 100,00 €"
- Tableau récapitulatif (card blanche avec rows séparées par dividers fins) :
  - Type : Achat immédiat
  - Compte source
  - Asset cible
  - Montant débité
  - Quantité brute estimée
  - Frais
  - Quantité nette estimée
  - Prix estimé

### Actions

- Bouton "Confirmer l'achat" (indigo, pleine largeur)
- Bouton retour (← dans le header)

### Exécution

Au clic sur "Confirmer l'achat" :
1. Re-fetch un preview frais (sécurité anti race condition)
2. Si preview OK → ouvre la bottom sheet Step 4
3. Si preview erreur → affiche erreur inline

## Step 4 — Processing and Success Bottom Sheets

### Bottom sheet compacte (non full-height)

Trois états internes :

#### Processing

- Spinner central (indigo, 48px)
- "Nous traitons votre achat…"
- "Cela ne prend que quelques secondes"

#### Success

- Icône check verte dans cercle
- "Achat effectué avec succès"
- "+0.01602 BTC" (emerald, 28px, bold)
- "≈ 100,00 €"
- Prix et frais en sous-texte discret
- Animation scale-in (easeOutBack)
- Auto-close après 2 secondes → pop `true`

#### Error

- Icône erreur rouge
- Message d'erreur humanisé
- Bouton "Fermer" → pop `false`

## Backend Reuse

| Composant | Réutilisation |
|-----------|--------------|
| `CashApi.fetchCashData()` | Step 1 — chargement balance EUR |
| `CryptoPositionsApi.fetchPositions()` | Step 1 — chargement wallets crypto |
| `ExchangeApi.previewBuy()` | Step 2 — preview live avec debounce |
| `ExchangeApi.previewBuy()` | Step 3 — re-fetch frais avant exécution |
| `ExchangeApi.executeBuy()` | Step 4 — exécution réelle |
| `BuyPreviewResult` | Modèle preview partagé entre steps 2/3/4 |
| `BuyResult` | Modèle résultat utilisé dans Step 4 |

**Zéro duplication de logique pricing.** Le flow utilise exactement les mêmes endpoints et modèles que l'ancien écran monolithique.

## Navigation and Refresh

### Ouverture

```dart
// crypto_wallet_detail_screen.dart
void _openBuyModal() async {
  final didBuy = await BuyFlowController.start(
    context,
    assetSymbol: widget.asset,
    assetName: widget.assetName,
    assetLogoUrl: Config.resolveLogoUrl(_logoUrl),
  );
  if (didBuy == true && mounted) {
    _load();
    _loadHeroSparkline();
  }
}
```

### Refresh après succès

Après Step 4 success, la chaîne de pop propage `true` jusqu'au caller.
`CryptoWalletDetailScreen` reçoit `didBuy == true` et appelle :
- `_load()` : rechargement des données wallet (position, stats)
- `_loadHeroSparkline()` : rechargement du chart hero

## Known Limitations

| Limitation | Détail |
|------------|--------|
| **Swap crypto → crypto** | L'UI affiche les wallets crypto comme sources potentielles avec le label "Swap (bientôt disponible)", mais les rows sont non tappables. Le backend swap n'existe pas encore. |
| **Source fiat uniquement** | Seul le Compte Euro est fonctionnel comme source. L'architecture `BuyFlowSourceAccount` supporte `type: 'fiat'` et `type: 'crypto'` pour extension future. |
| **Ancien écran conservé** | `buy_asset_modal_screen.dart` reste dans le projet mais n'est plus importé/utilisé. Il pourra être supprimé lors d'un cleanup. |
| **Point d'entrée unique** | Le flow est actuellement accessible uniquement depuis `CryptoWalletDetailScreen`. D'autres points d'entrée (page instrument, all crypto) pourront appeler `BuyFlowController.start()` directement. |

## Final Status

- ✅ Step 1 — Source Account Selection (modal full height)
- ✅ Step 2 — Amount Entry (modal full height, preview backend)
- ✅ Step 3 — Confirmation Recap (modal full height, tableau récap)
- ✅ Step 4 — Processing + Success (bottom sheet compacte)
- ✅ Navigation forward/back/close
- ✅ Refresh après succès
- ✅ Backend réutilisé à 100 % (CashApi, ExchangeApi)
- ✅ 0 erreur linter
- ✅ Architecture extensible (SELL, SWAP)
