# Global Account Statistics Report

## Vision

Créer une vue "wealth management" consolidée pour le compte Vancelian, agrégeant :
- Compte Euro (fiat)
- Portefeuille crypto direct
- Bundles crypto
- Préparé pour placements futurs

La page affiche une performance réelle en monétaire (P&L €), distingue clairement performance et flux, et ne contient aucune logique mono-asset.

## Data Model

### Sources de données

| Source | Usage |
|---|---|
| `CustodyAccount` / `CustodyAccountBalance` | Solde EUR fiat |
| `CustodyTransaction` | Dépôts / retraits (cashflow) |
| `CryptoPosition` (crypto_positions) | Valeur crypto consolidée |
| `pe_position_atoms` + `price_bridge` | Valeur par portfolio (direct/bundle) |
| `Portfolio` (pe_portfolios) | Direct portfolio + bundle portfolios |
| `ExchangeOrder` | Comptage activité |
| `build_wallet_statistics()` | PnL par asset |
| `build_wallet_history()` | Série historique crypto |

### Fonctions réutilisées de `accounting/invariants.py`

- `_get_client_eur_balance()` : solde EUR disponible
- `_get_crypto_value_eur()` : mark-to-market crypto total
- `_get_net_external_cash_flows()` : deposits - withdrawals

## Equity Curve Logic

```
performance_value = total_portfolio_value - cumulative_net_deposits

total_portfolio_value = fiat_balance + crypto_value_eur

cumulative_net_deposits = total_deposits - total_withdrawals
```

Le chart historique utilise la série `wallet_history` en mode `performance_value` (scope crypto), augmentée du fiat_balance courant comme composante constante.

### Vérification performance vs flux

| Événement | Impact performance | Impact flux |
|---|---|---|
| Dépôt 1000 € | 0 € | +1000 € |
| Gain marché +200 € | +200 € | 0 € |
| Retrait 500 € | 0 € | -500 € |
| Achat BTC | 0 € (valeur transférée) | 0 € |

## Cashflow Handling

Les cashflows sont calculés backend-side à partir de `custody_transactions` :

- **Dépôts** : `direction=CREDIT` + (`transaction_kind=BANK_TRANSFER_IN` OU `transaction_type=DEPOSIT`)
- **Retraits** : `direction=DEBIT` + (`transaction_kind=BANK_TRANSFER_OUT` OU `transaction_type=WITHDRAWAL`)

Le flux net (`net_flow`) = deposits - withdrawals.

La performance est toujours `total_value - net_deposits`, jamais confondue avec les flux.

## API

### GET /api/app/portfolio/global/statistics

Retourne :

```json
{
  "currency": "EUR",
  "performance": {
    "current_value": 6200.00,
    "total_invested": 5000.00,
    "total_pnl": 1200.00,
    "performance_pct": 24.00
  },
  "allocation": [
    {"asset": "BTC", "value": 2800, "pnl": 500, "weight": 45.16},
    {"asset": "ETH", "value": 1200, "pnl": 200, "weight": 19.35},
    {"asset": "EUR", "value": 1000, "pnl": 0, "weight": 16.13}
  ],
  "contributions": [
    {"asset": "BTC", "pnl": 500, "contribution_pct": 41.67}
  ],
  "breakdown": {
    "fiat": 1000, "fiat_pct": 16.13,
    "crypto_direct": 3200, "crypto_direct_pct": 51.61,
    "bundles": 2000, "bundles_pct": 32.26
  },
  "cashflow": {
    "deposits": 6000, "withdrawals": 1000, "net_flow": 5000
  },
  "activity": {
    "direct_trades": 15,
    "bundle_invest_events": 4,
    "rebalance_events": 1,
    "last_activity": "2026-03-18T14:30:00"
  },
  "risk": {
    "assets_count": 8,
    "concentration_asset": "BTC",
    "concentration_pct": 45.16,
    "volatility_30d": null,
    "max_drawdown": null
  }
}
```

### GET /api/app/portfolio/global/history?period=ALL

Retourne :

```json
{
  "period": "ALL",
  "points": [
    {
      "timestamp": "2026-01-15T00:00:00",
      "total_value": 5100.00,
      "performance_value": 100.00
    }
  ]
}
```

### Proxies Next.js

- `GET /api/mobile/flutter/portfolio/global/statistics` → backend `/api/app/portfolio/global/statistics`
- `GET /api/mobile/flutter/portfolio/global/history` → backend `/api/app/portfolio/global/history`

## UI

### GlobalStatisticsScreen

8 sections modulaires :

1. **Performance** : valeur totale, net investi, P&L total, performance %
2. **Performance historique** : chart equity curve en monétaire, sélecteur 1D/1W/1M/1Y/ALL
3. **Répartition par compte** : Compte Euro / Crypto direct / Bundles (valeur + %)
4. **Allocation globale** : donut chart `DonutsChartBig` avec tous les actifs + EUR
5. **Contribution à la performance** : tableau actif / P&L / contribution %
6. **Flux de trésorerie** : dépôts, retraits, flux net
7. **Activité** : trades directs, events bundle, rééquilibrages, dernière activité
8. **Risque** : nombre d'actifs, concentration max, volatilité/drawdown (placeholders)

### Navigation

- **Dashboard home** : icône stats (bar_chart_rounded) en haut à droite → `GlobalStatisticsScreen`
- Le `onPressed` était absent, maintenant branché via `_goToGlobalStatistics()`

### Design System

Composants utilisés :
- `AppTopNavBar`, `AppPageTitle`, `AppSectionTitle`
- `_ModuleCard` (cards blanches arrondies)
- `DonutsChartBig` + `DonutsChartSlice`
- `_ChartPainter` (courbe Catmull-Rom)
- Couleurs P&L : `#059669` (gain) / `#DC2626` (perte)

## Tests

### Test 1 — Deposit only
Dépôt de 1000 € → performance = 0 € (total_value = net_deposits)

### Test 2 — Market gain
+200 € de gain marché → performance = +200 €

### Test 3 — Withdrawal
Retrait 500 € → performance inchangée (flux net baisse, total value baisse proportionnellement)

### Test 4 — Sum consistency
Somme sous-comptes (fiat + crypto_direct + bundles) = current_value total

### Test 5 — Allocation
Donut affiche tous les actifs + EUR avec poids corrects

### Test 6 — Cashflow distinct
Section cashflow séparée de la section performance — pas de confusion

### Test 7 — Non-régression
- `PortfolioStatisticsScreen` (Mes crypto) inchangé
- `BundleStatisticsScreen` inchangé
- `WalletStatisticsScreen` (wallet mono-asset) inchangé
- Home screen reste fonctionnel

## Final Status

- **Backend** : 2 nouveaux endpoints (`/portfolio/global/statistics`, `/portfolio/global/history`)
- **Proxies** : 2 routes Next.js créées
- **Flutter** : modèles (`GlobalStatistics` + sous-objets), API (`GlobalStatisticsApi`), screen (`GlobalStatisticsScreen`)
- **Navigation** : icône stats du dashboard branchée
- **Non-régression** : aucun écran existant modifié (sauf ajout `onPressed` sur l'icône stats du home)
