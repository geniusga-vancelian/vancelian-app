# My Crypto Statistics Redesign Report

## Executive Summary

La page Statistics "Mes crypto" réutilisait un modèle semi-mono-asset hérité. Elle a été transformée en vraie vue portefeuille crypto consolidée, agrégeant holdings directs, holdings bundle et cash legs bundle.

La page inclut désormais : performance globale, chart historique en monétaire, allocation globale (donut), répartition par source (direct/bundle/cash), contribution à la performance par actif, déploiement du capital, activité consolidée, et risque.

## Issues in Current My Crypto Statistics

| Section | Problème |
|---|---|
| Overview | Pas de distinction realized/unrealized P&L clairement présentée |
| P&L Breakdown | Section séparée inutile, fusionnée dans Performance |
| Allocation | Correcte mais pas de source breakdown |
| Best/Worst Performers | Remplacé par contribution structurée |
| Manquant | Aucune info source (direct vs bundle vs cash) |
| Manquant | Aucune info déploiement (% investi, % cash, wallets, bundles) |
| Manquant | Aucune info activité structurée (trades directs vs bundle events vs rebalances) |
| Manquant | Aucune info risque (concentration, assets count) |

## New Consolidated Portfolio Model

### A. Performance
- Valeur actuelle (consolidée)
- Total investi
- P&L total (€)
- Performance %
- P&L réalisé
- P&L non réalisé

### B. Performance historique
- Chart en performance monétaire (€)
- Scope global crypto consolidé
- Sélecteur de période (1D / 1W / 1M / ALL)

### C. Allocation globale
- Donut chart (`DonutsChartBig`) avec tous les actifs
- Poids % par actif (incluant sous-jacents bundle)

### D. Répartition par source
- Holdings directs : valeur + %
- Holdings bundle : valeur + %
- Cash bundle : valeur + %

### E. Contribution à la performance
Pour chaque actif :
- P&L (€)
- Contribution %

### F. Déploiement du capital
- % investi
- % cash crypto
- Valeur cash
- Nombre de wallets directs
- Nombre de bundles actifs

### G. Activité
- Trades directs
- Investissements bundle
- Rééquilibrages
- Dernière activité

### H. Risque
- Nombre d'actifs
- Concentration max (asset + %)
- Volatilité 30j (placeholder)
- Max drawdown (placeholder)

## Removed Metrics

- Best / Worst Performers (remplacé par Contribution structurée)
- `position_size` par asset dans le modèle top-level
- `average_entry_price` par asset (mono-asset)
- Total Bought / Sold en qty
- Break-even distance

## Added Metrics

| Section | Métrique | Source |
|---|---|---|
| Performance | Realized / Unrealized P&L | `build_wallet_statistics` global |
| Source | Direct value / Bundle value / Cash value | `pe_position_atoms` par portfolio |
| Contribution | P&L par asset + contribution % | Per-asset stats |
| Deployment | Wallets / Bundles / Cash% | Portfolio count + cash legs |
| Activity | Direct trades / Bundle events / Rebalances | `exchange_orders` metadata |
| Risk | Assets count / Concentration | Allocation weights |

## Backend Data Sources

- `crypto_positions` (CryptoPositionRepository) : vue consolidée
- `build_wallet_statistics()` : stats par asset
- `pe_portfolios` : direct_portfolio + bundle_portfolios
- `pe_position_atoms` : positions par portfolio pour source breakdown
- `price_bridge.get_instrument_price()` : prix live
- `market_data.fx.usdt_to_eur()` : conversion EUR
- `exchange_orders` : activité consolidée (filtré par metadata)

## API Changes

### Backend
`GET /api/app/portfolio/statistics` entièrement refondu.

Ancienne réponse :
```json
{
  "currency": "EUR",
  "total_portfolio_value": 5000,
  "total_invested": 4500,
  "total_pnl": 500,
  "allocation": [...],
  "best_performers": [...],
  "worst_performers": [...]
}
```

Nouvelle réponse :
```json
{
  "currency": "EUR",
  "performance": {
    "current_value": 5000,
    "total_invested": 4500,
    "total_pnl": 500,
    "performance_pct": 11.11,
    "realized_pnl": 200,
    "unrealized_pnl": 300
  },
  "allocation": [...],
  "contributions": [...],
  "source_breakdown": {
    "direct_value": 2700,
    "direct_pct": 54.0,
    "bundle_value": 2100,
    "bundle_pct": 42.0,
    "bundle_cash_value": 200,
    "bundle_cash_pct": 4.0
  },
  "deployment": {
    "invested_pct": 96.0,
    "cash_pct": 4.0,
    "cash_value": 200,
    "direct_wallets": 5,
    "active_bundles": 2
  },
  "activity": {
    "direct_trades": 15,
    "bundle_invest_events": 4,
    "rebalance_events": 1,
    "last_activity": "2026-03-18T14:30:00"
  },
  "risk": {
    "assets_count": 7,
    "concentration_asset": "BTC",
    "concentration_pct": 45.2,
    "volatility_30d": null,
    "max_drawdown": null
  }
}
```

### Proxy Next.js
Inchangé — `web/src/app/api/mobile/flutter/portfolio/statistics/route.ts` redirige déjà vers `/api/app/portfolio/statistics`.

## Flutter UI Changes

### Modèle
`portfolio_statistics.dart` entièrement refondu :
- `PortfolioStatistics` : modèle principal avec sous-objets
- `PortfolioAssetAllocation` : allocation par actif (asset, current_value, pnl, weight)
- `PortfolioContribution` : contribution P&L par actif
- `SourceBreakdown` : direct/bundle/cash values et %
- `DeploymentInfo` : deployed capital metrics
- `ActivityInfo` : trades/events/rebalances
- `RiskInfo` : concentration, volatility, drawdown

### Screen
`PortfolioStatisticsScreen` refondu avec 8 sections :
1. Performance (valeur, investi, P&L, realized/unrealized)
2. Performance historique (chart monétaire)
3. Allocation globale (donut `DonutsChartBig`)
4. Répartition par source (direct / bundle / cash)
5. Contribution à la performance (tableau par actif)
6. Déploiement du capital (% investi, cash, wallets, bundles)
7. Activité (trades, events, rebalances, dernière activité)
8. Risque (assets count, concentration, volatility, drawdown)

### Navigation
Inchangée — `AllCryptoPositionsScreen` pointe toujours vers `PortfolioStatisticsScreen`.

## Validation Scenarios

### Test 1
Page "Mes crypto" n'affiche plus de métriques mono-asset (position, current price, avg entry)

### Test 2
Agrège bien direct + bundles dans la valeur totale

### Test 3
Allocation globale reflète tous les actifs crypto détenus

### Test 4
Source breakdown distingue direct vs bundles vs cash leg

### Test 5
Contribution à la performance cohérente (somme ≈ 100%)

### Test 6
Chart en performance monétaire (€)

### Test 7
Activité affiche trades directs, events bundle, rebalances séparément

### Test 8
Non-régression `WalletStatisticsScreen` (wallet direct mono-asset)

### Test 9
Non-régression `BundleStatisticsScreen`

### Test 10
Non-régression All Crypto / Home / Bundle detail

## Final Status

- **Backend** : endpoint portfolio/statistics refondu en vue consolidée
- **Flutter** : modèle et screen entièrement refondus
- **Navigation** : inchangée, fonctionnelle
- **Non-régression** : WalletStatisticsScreen et BundleStatisticsScreen non impactés
