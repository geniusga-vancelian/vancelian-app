# Buy Asset Modal UI Report

## Executive Summary

Création d'un écran modal plein écran `BuyAssetModalScreen` pour l'achat de crypto-assets, au style fintech premium (Revolut / N26). L'écran s'ouvre depuis le bouton "Acheter" de la page `CryptoWalletDetailScreen` avec une animation slide-up iOS-like.

Fonctionnalités implémentées :
- Header custom : croix fermeture (gauche), titre "Acheter" (centre), logo asset (droite)
- Texte explicatif dynamique : "Combien souhaitez-vous acheter de Bitcoin ?"
- Saisie montant via TextField invisible avec affichage custom gros format
- Conversion indicative fiat → crypto en temps réel
- Pill de sélection du compte source avec solde
- Bouton "Confirmer" avec validation d'état
- Clavier numérique natif avec décimales, ouvert automatiquement

## Files Created / Modified

### Créé

| Fichier | Description |
|---------|-------------|
| `mobile/lib/features/wallet/presentation/screens/buy_asset_modal_screen.dart` | Écran modal complet (606 lignes) |

### Modifié

| Fichier | Changement |
|---------|-----------|
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | Import + navigation vers `BuyAssetModalScreen` depuis le bouton "Acheter" |

## Navigation Integration

### Ouverture

Depuis `CryptoWalletDetailScreen._buildHeroActionButtons()`, le bouton "Acheter" appelle :

```dart
BuyAssetModalScreen.show(
  context,
  assetSymbol: widget.asset,      // ex: 'BTC'
  assetName: widget.assetName,    // ex: 'Bitcoin'
  assetLogoUrl: Config.resolveLogoUrl(_logoUrl),
  unitPrice: _livePrice,          // prix live pour la conversion
);
```

### Animation

- `PageRouteBuilder` avec `SlideTransition` bottom→top
- Courbe : `easeOutCubic` (ouverture), `easeInCubic` (fermeture)
- Durée : 300ms (ouverture), 250ms (fermeture)
- Opaque : true (plein écran)

### Fermeture

- Bouton croix (×) en haut à gauche → `Navigator.pop()`
- Bouton "Confirmer" → `Navigator.pop()` (placeholder, pas d'exécution réelle)

## Amount Input Behavior

### Architecture technique

Le champ de saisie utilise un pattern "invisible TextField" :

1. Un `TextField` réel existe dans l'arbre widget mais est rendu invisible (`Opacity: 0`, taille 1×1px)
2. Ce TextField capture les événements clavier natifs et gère le `TextEditingController`
3. L'affichage visible est un `Text` widget custom avec formatage adapté

### Formatage de l'affichage

| Saisie brute | Affichage |
|-------------|-----------|
| `""` | `0 €` |
| `1` | `1 €` |
| `1250` | `1 250 €` |
| `1250,5` | `1 250,50 €` |
| `0,99` | `0,99 €` |

- Séparateur de milliers : espace (locale `fr_FR`)
- Séparateur décimal : virgule
- Symbole monétaire : `€` ou `$` selon `CurrencyPreference`
- Taille : 48px, weight 700, avec `FittedBox` pour s'adapter aux grands montants

### Conversion crypto

Sous le montant, affichage de l'équivalent crypto :

```
≈ 0.01609813 BTC
```

Calculé par `_computeEstimatedCrypto(amountFiat, unitPrice)` :

```dart
double? _computeEstimatedCrypto(double amountFiat, double? unitPrice) {
  if (unitPrice == null || unitPrice <= 0 || amountFiat <= 0) return null;
  return amountFiat / unitPrice;
}
```

Le `unitPrice` est le prix live passé depuis `CryptoWalletDetailScreen`. Quand null, la ligne affiche `0 BTC`.

### Input Formatter

`_SingleDecimalFormatter` applique :
- Normalisation : `.` → `,`
- Maximum 1 séparateur décimal
- Maximum 2 décimales
- Pas de zéros en tête (`007` → `7`, mais `0,5` OK)

## Native Keyboard Behavior

| Propriété | Valeur |
|-----------|--------|
| `keyboardType` | `TextInputType.numberWithOptions(decimal: true)` |
| `autofocus` | `true` |
| Ouverture auto | Oui, via `FocusNode.requestFocus()` dans `addPostFrameCallback` |
| Chiffres | Natif OS |
| Décimal | `,` ou `.` (normalisé en `,`) |
| Backspace | Natif, fonctionne proprement |
| Alphanumérique | Bloqué par `FilteringTextInputFormatter` |

Le clavier s'ouvre **dès l'ouverture** de la modal grâce au `autofocus: true` et au `requestFocus` en post-frame callback.

## Validation Rules

| Règle | Condition |
|-------|-----------|
| Montant vide ou 0 | Bouton désactivé |
| Montant > 0, pas de solde fourni | Bouton **activé** (mode démo, backend non branché) |
| Montant > 0 et ≤ solde | Bouton activé |
| Montant > solde | Bouton désactivé |

```dart
bool get _isValid =>
    _parsedAmount > 0 &&
    (widget.sourceAccountBalance <= 0 ||
        _parsedAmount <= widget.sourceAccountBalance);
```

### Style du bouton

| État | Fond | Texte | Ombre |
|------|------|-------|-------|
| Désactivé | Gris clair 15% | Gris moyen 50% | Aucune |
| Activé | `AppColors.indigo` (#6B5DFF) | Blanc | Indigo 35% |

## Structure de l'écran

```
┌──────────────────────────────────┐
│  [×]      Acheter        [Logo]  │  ← Header custom
├──────────────────────────────────┤
│                                  │
│  Combien souhaitez-vous acheter  │  ← Question text
│  de Bitcoin ?                    │
│                                  │
│         1 250 €                  │  ← Amount display (48px)
│       ≈ 0.01609 BTC              │  ← Crypto equivalent
│                                  │
│                                  │
│  ┌──────────────────────────┐    │
│  │ (€)  Compte Euro         │    │  ← Source account pill
│  │      150 778,96 €      > │    │
│  └──────────────────────────┘    │
│                                  │
├──────────────────────────────────┤
│  (i)  [    Confirmer    ]        │  ← Bottom bar
└──────────────────────────────────┘
│      Clavier numérique natif     │
└──────────────────────────────────┘
```

## Design System Compliance

| Token | Utilisation |
|-------|------------|
| `AppColors.pageBackground` | Fond de page (#F5F5F5) |
| `AppColors.cardBackground` | Pill source, bouton info |
| `AppColors.textPrimary` | Montant, titre, labels |
| `AppColors.textSecondary` | Question, équivalent crypto, chevron |
| `AppColors.indigo` | Bouton confirmer actif |
| `AppColors.cryptoAssetBrand[asset]` | Teinte du logo asset |
| `AppTypography.heroAmount` | Montant principal |
| `AppTypography.titleMedium` | Titre navbar, labels |
| `AppTypography.bodyLarge` | Question text |
| `AppTypography.bodyMedium` | Équivalent crypto, label compte |
| `AppTypography.bodySmall` | Solde du compte source |
| `AppSpacing.lg` | Padding horizontal (16px) |
| `AppSpacing.sm` | Padding vertical header (8px) |

## Final Status

| Élément | État |
|---------|------|
| Écran `BuyAssetModalScreen` | **CRÉÉ** |
| Header (×, titre, logo asset) | **OK** |
| Question text dynamique | **OK** |
| Saisie montant (invisible TextField) | **OK** |
| Formatage montant (milliers, décimales) | **OK** |
| Conversion fiat → crypto | **OK** |
| Pill compte source | **OK** |
| Bouton "Confirmer" avec validation | **OK** |
| Clavier numérique natif auto-open | **OK** |
| Navigation depuis "Acheter" | **OK** |
| Linters | **0 erreurs** |
| Exécution réelle (trading) | **Non implémentée** (placeholder) |
| Solde compte source | **Placeholder** (0 par défaut, à brancher) |
