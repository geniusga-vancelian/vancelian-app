# Bundle Statistics Redesign Report

## Executive Summary

La page Statistics d'un bundle réutilisait le modèle mono-asset (position, current price, avg entry, trading activity, risk metrics) prévu pour un wallet crypto unique. Ce modèle est incorrect pour un portefeuille multi-actifs.

La page a été entièrement refondée en vue portefeuille avec : performance globale, allocation vs cible avec drift, contribution à la performance par actif, déploiement du capital (cash/investi), activité (rééquilibrages), et risque (concentration, nombre d'actifs).

## Issues in Current Implementation

| Métrique | Problème |
|---|---|
| Position (qty) | Non pertinent pour un bundle multi-actifs |
| Current Price | Prix d'un seul asset, pas du portefeuille |
| Avg Entry (PRU) | PRU d'un seul asset, pas du bundle |
| Avg Buy/Sell Price | Pas de sens au niveau portefeuille |
| Total Bought/Sold | Quantités d'un seul asset |
| Break-even Distance | Logique mono-asset |
| Portfolio Weight | Poids d'un asset dans le wallet global, pas dans le bundle |
| Trading Activity | Trades individuels, pas événements bundle |

La page prenait `assets.first.asset` du bundle et ouvrait `WalletStatisticsScreen` avec cet asset unique.

## New Portfolio-Based Model

### Performance
- Valeur actuelle (agrégée tous atoms + cash leg)
- Total investi (somme cost_basis)
- P&L total (€)
- Performance (%)

### Allocation vs Cible
Pour chaque asset du bundle :
- Target % (allocation cible)
- Current % (allocation réelle)
- Drift % (current − target)

### Contribution à la performance
Pour chaque asset :
- P&L € individuel
- Contribution % = asset_pnl / total_pnl

### Cash & Deployment
- % investi
- % cash
- Valeur cash (€)

### Activité
- Nombre de rééquilibrages (orders avec `bundle_action == "rebalance"`)
- Total événements d'allocation (orders scoped au bundle)

### Risque
- Nombre d'actifs
- Concentration max (asset + %)
- Volatilité 30j (placeholder)
- Max drawdown (placeholder)

## Removed Metrics

- Position (qty mono-asset)
- Current Price (mono-asset)
- Avg Entry / PRU (mono-asset)
- Avg Buy Price / Avg Sell Price
- Total Bought / Total Sold (qty)
- Break-even Distance
- Portfolio Weight (mono-asset)
- First Trade / Last Trade (mono-asset)
- Trade Count / Buy Count / Sell Count

## Added Metrics

| Section | Métrique | Source |
|---|---|---|
| Performance | Current Value | Σ market_value tous atoms |
| Performance | Total Invested | Σ cost_basis tous atoms |
| Performance | Total P&L | current − invested |
| Performance | Performance % | (current − invested) / invested × 100 |
| Allocation | Target / Current / Drift par asset | TargetAllocation + market_value |
| Contribution | P&L par asset | market_value − cost_basis par atom |
| Contribution | Contribution % | asset_pnl / total_pnl |
| Cash | Invested % / Cash % | (total − cash) / total |
| Cash | Cash value | cash atom market_value |
| Activity | Rebalance count | exchange_orders avec bundle_action=rebalance |
| Activity | Total allocation events | exchange_orders scoped au bundle |
| Risk | Assets count | nombre d'assets spot |
| Risk | Concentration | max current_pct + asset |

## Data Sources

- `pe_position_atoms` : positions spot + cash du bundle
- `pe_target_allocations` : poids cibles par instrument
- `price_bridge.get_instrument_price()` : prix live
- `market_data.fx.usdt_to_eur()` : conversion EUR
- `exchange_orders` : comptage activité (filtré par metadata_.portfolio_id)

## UI Changes

### Backend
- `GET /api/app/bundle/{portfolio_id}/statistics` : refait en endpoint portfolio-level retournant `performance`, `allocation_vs_target`, `contributions`, `cash_deployment`, `activity`, `risk`

### Flutter
- Nouveau modèle `BundlePortfolioStatistics` + `AllocationVsTarget` + `AssetContribution` dans `bundle_api.dart`
- Nouvelle méthode `getBundlePortfolioStatistics()` dans `BundleApi`
- Nouveau screen `BundleStatisticsScreen` remplaçant `WalletStatisticsScreen` pour les bundles
- Navigation mise à jour dans `BundleWalletDetailScreen` — le bouton stats ouvre désormais `BundleStatisticsScreen`
- Design System : `_ModuleCard`, `AppSectionTitle`, `AppPageTitle`, `AppTopNavBar`, `ChartSonarPoint`
- Chart historique conservé (performance_value scoped bundle)

### Proxy Next.js
- Existant et inchangé : `web/src/app/api/mobile/flutter/bundle/[portfolioId]/statistics/route.ts`

## Validation Scenarios

### Test 1
Bundle multi-actifs → aucune métrique mono-asset affichée (position, current price, avg entry, etc.)

### Test 2
Contribution correcte → somme des contributions ≈ 100%

### Test 3
Allocation drift correcte → drift = current − target pour chaque asset

### Test 4
Cash leg affiché correctement → % cash, valeur cash, % investi

### Test 5
Activité → comptage correct des rééquilibrages et événements

### Test 6
Non-régression → stats des wallets directs inchangées (toujours via `WalletStatisticsScreen`)

## Final Status

- **Backend** : endpoint refait en portfolio-level
- **Flutter** : nouveau screen dédié bundle
- **Navigation** : bouton stats redirige vers le bon écran
- **Non-régression** : `WalletStatisticsScreen` inchangé pour les wallets directs
