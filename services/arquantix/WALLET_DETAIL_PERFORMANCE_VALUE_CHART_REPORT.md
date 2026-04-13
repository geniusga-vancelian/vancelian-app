# Wallet Detail Performance Value Chart Report

## Executive Summary

Le hero chart de la page Crypto Wallet Detail (BTC, ETH, SOL, etc.) affiche désormais la **performance monétaire historique** du wallet en devise de référence, et non plus la NAV brute.

La série représente à chaque instant `t` :

```
performance_value(t) = realized_pnl_cumulated(t) + unrealized_pnl(t)
```

Le montant en gros en haut de la page reste la valeur actuelle du wallet. La courbe derrière montre l'évolution du gain/perte cumulé depuis le premier trade.

## Backend Changes

### Nouveau paramètre `mode`

L'endpoint `GET /api/app/wallet/history` accepte désormais un paramètre `mode` :

| Mode | Description | Utilisé par |
|------|-------------|-------------|
| `value` (défaut) | NAV = Σ position × price | All Crypto hero, Statistics |
| `performance_value` | Realized + Unrealized PnL | Crypto Wallet Detail hero |
| `performance_pct` | Réservé (futur) | — |

### Nouvelle fonction `_build_performance_value()`

Ajoutée dans `api/services/wallet_history/service.py`. Réutilise toute l'infrastructure existante (ordres, bougies, timeline, granularité) mais change la métrique calculée.

### Chaîne complète

```
Flutter CryptoWalletDetailScreen
  → fetchHistory(period: 'ALL', asset: 'BTC', mode: 'performance_value')
  → Config.walletHistoryUrl('ALL', asset: 'BTC', mode: 'performance_value')
  → GET /api/mobile/flutter/wallet/history?period=ALL&asset=BTC&mode=performance_value

Next.js proxy
  → forward mode parameter
  → GET /api/app/wallet/history?period=ALL&asset=BTC&mode=performance_value

Backend router
  → build_wallet_history(db, client_id, ref_currency, asset='BTC', mode='performance_value')
  → _build_performance_value(sorted_ts, trade_events, ...)
```

## Series Definition

### Formule

À chaque timestamp `t` :

```
performance_value(t) = realized_pnl_cumulated(t) + unrealized_pnl(t)
```

### Coût moyen pondéré (weighted average cost)

Cohérent avec `wallet_statistics.service.build_wallet_statistics` :

```
avg_cost_per_unit = cost_basis / position_size
```

### Tracking incrémental

À chaque **BUY** :
```
cost_basis[asset] += amount × price_ref
position[asset] += amount
```

À chaque **SELL** :
```
avg_cost = cost_basis[asset] / position[asset]
realized_pnl += amount × (price_ref - avg_cost)
cost_basis[asset] -= amount × avg_cost
position[asset] -= amount
```

À chaque **timestamp** :
```
unrealized_pnl = Σ (position[a] × price_ref(a, t) - cost_basis[a])
total_pnl = realized_pnl + unrealized_pnl
```

### Prix en devise de référence

La fonction `_price_ref()` calcule le prix d'un asset en devise de référence, avec la même logique que le mode `value` :

- **Trade timestamp (EUR)** : `execution_price` directement (déjà en EUR)
- **Inter-trade (EUR)** : `candle_close_USDT / EURUSDT_candle_close`
- **Fallback** : `execution_price` carry-forward

### Premier point

Au premier trade (ex: achat 1000€ BTC) :
- `cost_basis = 1000€`
- `position × price = 1000€`
- `unrealized_pnl = 0€`
- `performance_value = 0€`

La courbe commence à 0€ — cohérent avec « au moment de l'achat, la performance est nulle ».

### Dernier point (live)

Injecté depuis `MarketDataLatestQuote` (même source que "Current Value") :
```
live_unrealized = Σ (position[a] × live_price - cost_basis[a])
live_pnl = realized_pnl + live_unrealized
```

Ce dernier point est cohérent avec le "Total des gains" affiché dans les Statistics.

## Granularity Reuse

La granularité est **identique** au mode `value` — aucun changement :

| Span | Granularité |
|------|-------------|
| 0–2h | 1m |
| 2h–7d | 5m |
| 7d–30d | 1h |
| 30d–120d | 4h |
| >120d | 1d |

Le code partagé dans `build_wallet_history` (lignes 282–400) gère :
- Sélection de granularité (`_select_granularity`)
- Chargement des bougies (`_load_all_candles`)
- Fallback vers des granularités plus grossières
- Construction de la timeline (`sorted_ts`)
- Échantillonnage si > 500 points

Le mode `performance_value` intervient **après** la construction de la timeline.

## Flutter Integration

### CryptoWalletDetailScreen

```dart
// AVANT : NAV brute
final data = await _historyApi.fetchHistory(
  period: 'ALL',
  asset: widget.asset,
);

// APRÈS : performance monétaire
final data = await _historyApi.fetchHistory(
  period: 'ALL',
  asset: widget.asset,
  mode: 'performance_value',
);
```

### Rendu

Le hero chart utilise `LineChartModule` avec les valeurs brutes (en EUR).
La courbe reflète l'évolution du PnL : de 0€ (premier trade) jusqu'à la valeur actuelle du gain/perte.

### Cohérence visuelle

- Montant en haut : valeur actuelle du wallet (inchangé)
- Courbe : performance monétaire historique
- Si le prix a baissé depuis l'achat : la courbe est sous 0
- Si le prix a monté : la courbe est au-dessus de 0

## Files Modified

| Fichier | Changement |
|---------|-----------|
| `api/services/wallet_history/service.py` | Ajout `_build_performance_value()` + paramètre `mode` |
| `api/services/test_clients/router.py` | Ajout paramètre `mode` au endpoint |
| `web/src/app/api/mobile/flutter/wallet/history/route.ts` | Forward `mode` |
| `mobile/lib/core/config.dart` | Ajout `mode` à `walletHistoryUrl` |
| `mobile/lib/features/wallet/data/wallet_history_api.dart` | Ajout `mode` à `fetchHistory` |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | `mode: 'performance_value'` |

## Validation Scenarios

### Scenario 1 : Buy 1000€ BTC, prix stable
- Premier point : 0€
- Dernier point : ≈ -17€ (si prix légèrement en dessous du PRU)
- Cohérent avec "Gains en cours" dans Statistics

### Scenario 2 : Buy 1000€ BTC, prix monte +10%
- Courbe monte de 0€ à ≈ +100€
- Dernier point = unrealized PnL ≈ +90€ (après fees)

### Scenario 3 : Buy puis Sell partiel
- Après le sell : realized_pnl capturé
- Courbe = realized_pnl + unrealized_pnl restant
- Cohérent avec "Gains encaissés" + "Gains en cours"

### Scenario 4 : Sell total puis rebuy
- Après sell total : courbe = realized_pnl (flat)
- Après rebuy : courbe reprend ses fluctuations (realized + new unrealized)

### Scenario 5 : Non-régression
- All Crypto hero : `mode='value'` (défaut) — inchangé
- Statistics chart : `mode='value'` (défaut) — inchangé
- Asset-scoped filter : toujours fonctionnel (paramètre `asset` indépendant)

## Final Status

| Élément | État |
|---------|------|
| Backend `performance_value` | **IMPLÉMENTÉ** |
| Router `mode` parameter | **AJOUTÉ** |
| Next.js proxy forwarding | **AJOUTÉ** |
| Flutter API `mode` parameter | **AJOUTÉ** |
| CryptoWalletDetail hero chart | **UTILISE `performance_value`** |
| Non-régression All Crypto | **OK** — mode par défaut `value` |
| Non-régression Statistics | **OK** — mode par défaut `value` |
| Cohérence avec `build_wallet_statistics` | **OK** — même méthode de coût moyen |
