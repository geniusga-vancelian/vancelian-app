# BUNDLE_DETAIL_ALLOCATION_AND_REBALANCE_CTA_REPORT

## Executive Summary

Deux améliorations UX appliquées à la page détail bundle (`BundleWalletDetailScreen`) :

1. **Donut "Allocation réelle"** — le cash leg (USDC/EURC) est maintenant inclus dans le graphique et la légende, reflétant la vraie allocation du bundle à l'instant t
2. **Bouton "Rééquilibrer"** — ajouté à côté de "Investir" dans le hero, non branché fonctionnellement (snackbar "Bientôt disponible" au tap)

**Scope** : Flutter uniquement. Aucune modification backend nécessaire — le cash leg était déjà présent dans le payload `my-bundles`.

## Root Cause of Missing Cash Leg in Allocation

### Diagnostic

`_buildAllocationDonut()` utilisait `b.spotPositions` comme seule source de données :

```dart
// AVANT — ligne 252
final spotPositions = b.spotPositions;
// spotPositions = positions.where((p) => p.positionType == 'spot')
```

Le getter `spotPositions` filtre explicitement `positionType == 'spot'`, excluant par définition les positions `cash`. Le total du donut était donc calculé sur les seuls actifs investis — le pourcentage de chaque actif étant rapporté à 100% des spots, pas du bundle complet.

### Données disponibles

Le payload backend (`GET /api/app/bundle/my-bundles`) inclut déjà les positions cash dans `positions[]` avec `position_type: "cash"`. Aucun enrichissement backend n'était nécessaire.

| Champ | Disponible ? | Utilisé par le donut ? |
|-------|-------------|----------------------|
| `positions[].asset` | ✅ | ✅ (spots seulement) |
| `positions[].position_type` | ✅ | ❌ (cash ignoré) |
| `positions[].market_value` | ✅ | ✅ (spots seulement) |
| `positions[].quantity` | ✅ | ❌ par le donut |

## Allocation Real Donut Fix

### Logique modifiée

```dart
// APRÈS
final allPositions = <BundlePositionInfo>[];
allPositions.addAll(b.spotPositions);

final cashPositions = b.positions
    .where((p) => p.isCash && p.quantity > 0.001)
    .toList();
for (final cash in cashPositions) {
  allPositions.add(cash);
}
```

Le total du donut est maintenant :

```
total_bundle_value = Σ spot_market_values + Σ cash_market_values
```

Chaque segment :

```
segment_pct = segment_market_value / total_bundle_value × 100
```

## Cash Leg Inclusion Logic

### Seuil de filtrage

Le cash leg n'apparaît dans le donut que si `quantity > 0.001`. Cela évite d'afficher un segment invisible pour un reliquat de poussière.

### Couleur dédiée

```dart
const cashLegColor = Color(0xFF94A3B8); // slate-400 — gris-bleu neutre
```

Les actifs spot conservent leurs couleurs `AppColors.cryptoAssetBrand`. Le cash leg se distingue visuellement par cette teinte neutre, identifiable comme "non-investissement" sans ajouter de style incohérent.

### Label

Le label affiché est le ticker réel de l'entry asset (ex. `USDC`), pas un label générique "Cash". Cela reste factuel et cohérent avec le reste de la légende.

## Rebalance CTA Added

### Positionnement

Le bouton est ajouté dans le `heroActionsBelowFullBleed` de `LayoutPageLevel2`, à droite du bouton "Investir" :

```
[  ➕ Investir  ]    [  ⚙ Rééquilibrer  ]
   heroPrimary            heroLight
```

### Configuration

| Propriété | Valeur |
|-----------|--------|
| Icône | `Icons.tune_rounded` |
| Label | `Rééquilibrer` |
| Variant | `ButtonRoundedVariant.heroLight` (style secondaire) |
| Action | Snackbar "Bientôt disponible" (2s, floating) |

### Comportement

- Le bouton est visuellement actif (pas disabled/grisé)
- Au tap : `SnackBar` discret avec message "Bientôt disponible"
- Prêt à être branché sur le futur moteur de rebalance sans modification de layout

## Design System Components Used

| Composant | Usage |
|-----------|-------|
| `PortfolioAllocationModule` | Donut + légende (inchangé structurellement) |
| `PortfolioAllocationSlice` | Segments du donut (spot + cash) |
| `ActionButtonRow` | Rangée de boutons hero |
| `ActionButtonItem` | Items Investir + Rééquilibrer |
| `ButtonRoundedVariant.heroPrimary` | Investir (style existant) |
| `ButtonRoundedVariant.heroLight` | Rééquilibrer (style secondaire DS) |
| `AppColors.cryptoAssetBrand` | Couleurs par asset crypto |
| `AppTypography.sectionTitle` | Titre "Allocation réelle" |
| `SnackBar` | Feedback "Bientôt disponible" |

## Validation Scenarios

| # | Scénario | Résultat attendu |
|---|----------|-----------------|
| 1 | Bundle partiellement investi (reliquat USDC) | ✅ Donut affiche spots + USDC (gris-bleu) |
| 2 | Bundle totalement investi (cash ≤ 0.001) | ✅ Donut affiche uniquement les spots (pas de segment cash parasite) |
| 3 | Somme des pourcentages du donut | ✅ ≈ 100% (spots + cash) |
| 4 | Légende complète | ✅ Chaque asset + cash leg a sa ligne avec couleur et % |
| 5 | Bouton "Rééquilibrer" visible | ✅ À côté de "Investir", style heroLight |
| 6 | Tap "Rééquilibrer" | ✅ Snackbar "Bientôt disponible" |
| 7 | Tap "Investir" | ✅ Flow invest inchangé |
| 8 | Non-régression section "Mon investissement" | ✅ Cash leg info-row toujours affichée |
| 9 | Non-régression section "Détail des positions" | ✅ Spots seulement (inchangé) |
| 10 | Non-régression "Mes bundles" | ✅ Aucune modification |

## Final Status

| Item | Status |
|------|--------|
| Cash leg inclus dans le donut | ✅ Implémenté |
| Cash leg inclus dans la légende | ✅ Implémenté |
| Seuil de filtrage (> 0.001) | ✅ Implémenté |
| Couleur dédiée cash leg | ✅ `#94A3B8` (slate-400) |
| Total donut = spots + cash | ✅ Implémenté |
| Bouton "Rééquilibrer" ajouté | ✅ Implémenté |
| Style secondaire DS | ✅ `heroLight` |
| Action "Bientôt disponible" | ✅ SnackBar |
| Modification backend | ❌ Non nécessaire |
| Non-régression bundle invest | ✅ Inchangé |
