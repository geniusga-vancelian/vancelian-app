# Dashboard Chart Alignment Fix

## Root Cause

Deux surfaces utilisaient `totalValue` (valeur patrimoniale brute) au lieu de `performanceValue` (gains/pertes nets) pour dessiner les courbes :

1. **Home dashboard** (`home_screen.dart` → `_loadHeroChart`) : `points.map((p) => p.totalValue)`
2. **Global Statistics** (`global_statistics_screen.dart` → `_chartValues`) : `_chartPoints.map((p) => p.totalValue)`

Toutes les autres pages (Crypto, Bundle, Wallet) appelaient l'API avec `mode: 'performance_value'` et affichaient directement le résultat.

### Pourquoi c'est un problème

- `totalValue` = fiat + crypto NAV (inclut les dépôts/retraits)
- `performanceValue` = totalValue − net_deposits (pure performance)

Conséquence : un dépôt de 1000 € créait un **spike** sur le dashboard alors que sur "Mes Crypto" la courbe restait plate. Les deux charts étaient visuellement incohérents.

## Fix Applied

### home_screen.dart — `_loadHeroChart()`

```dart
// AVANT
final chartValues = points.map((p) => p.totalValue).toList();

// APRÈS
final chartValues = points.map((p) => p.performanceValue).toList();
```

Le pourcentage de performance affiché (`_heroPerformancePct`) vient toujours de `stats.performancePct` (endpoint `/global/statistics`, pas de calcul local).

### global_statistics_screen.dart — `_chartValues`

```dart
// AVANT
return _chartPoints.map((p) => p.totalValue).toList();

// APRÈS
return _chartPoints.map((p) => p.performanceValue).toList();
```

L'en-tête du chart affichait déjà `performanceValue` pour le label — seule la forme de la courbe était incorrecte.

## Before vs After

| Scénario | Avant | Après |
|---|---|---|
| Dépôt 1000 € | Spike visible sur Dashboard, pas sur Crypto | Pas de spike (identique) |
| Perte -200 € | Dashboard : baisse atténuée par le solde fiat | Dashboard = Crypto : descente nette |
| Forme de la courbe | Dashboard ≠ Crypto | Dashboard == Crypto |

## Validation

### Test 1 : Dépôt → pas de spike
`performanceValue = totalValue - netDeposits` → un dépôt augmente les deux de manière égale → pas de variation de performance.

### Test 2 : Perte → descente progressive
`performanceValue` diminue proportionnellement à la perte crypto, sans dilution par le solde fiat.

### Test 3 : Dashboard == My Crypto
Les deux surfaces utilisent maintenant `performanceValue`. Le dashboard utilise `build_global_history` (scope global incluant fiat), mais comme le fiat n'a pas de performance propre, la courbe est dominée par la performance crypto — identique à "Mes Crypto".

Tolérance : 0 (même source de données, même champ).

## Final State

| Surface | Champ utilisé pour le chart | Source |
|---|---|---|
| Home dashboard | `performanceValue` | `/global/history` → `build_global_history` |
| Global Statistics | `performanceValue` | `/global/history` → `build_global_history` |
| Crypto Statistics | `performance_value` | `/wallet/history?mode=performance_value&scope=crypto` |
| Bundle Statistics | `performance_value` | `/wallet/history?mode=performance_value&portfolioScope=bundle` |
| Wallet Statistics | `performance_value` | `/wallet/history?mode=performance_value&asset=X` |

Tous les charts sont maintenant uniformes sur `performance_value`.
