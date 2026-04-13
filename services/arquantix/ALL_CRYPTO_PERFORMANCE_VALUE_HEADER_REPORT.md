# All Crypto Performance Value Header Report

## Executive Summary

Le hero chart de la page "All Crypto" affiche désormais la **performance monétaire globale** du portefeuille crypto, et non plus la NAV brute.

La série représente à chaque instant `t` :

```
global_crypto_performance_value(t) = Σ performance_value_asset_i(t)
```

Le montant en gros en haut de la page reste la valeur totale actuelle du portefeuille crypto (inchangé). La courbe derrière montre l'évolution du gain/perte cumulé de l'ensemble des wallets crypto.

## Backend Changes

### Aucune modification de logique backend

La fonction `_build_performance_value()` (implémentée dans le ticket précédent) gère **déjà** le cas multi-assets. Quand `asset=None`, elle :

1. Charge tous les `exchange_orders` completed du client (tous assets confondus)
2. Identifie le trade le plus ancien → détermine la granularité unique
3. Construit une timeline commune
4. Tracke par asset : `positions[a]`, `cost_basis[a]`, `exec_prices[a]`
5. Accumule un seul `realized_pnl` global
6. À chaque timestamp : `unrealized_pnl = Σ (pos_i × price_i - cost_basis_i)`
7. Émet : `total_pnl = realized_pnl + unrealized_pnl`

### Nouveau paramètre `scope` (API clarté)

Ajouté au router pour documenter l'intention de l'appel :

```
GET /api/app/wallet/history?scope=crypto&mode=performance_value&period=ALL
```

Le paramètre `scope=crypto` est accepté par le router et forwardé à travers la chaîne, mais ne modifie pas la logique backend actuelle (tous les exchange_orders sont crypto).

### Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `api/services/test_clients/router.py` | Ajout paramètre `scope` (optional) |
| `web/src/app/api/mobile/flutter/wallet/history/route.ts` | Forward `scope` |
| `mobile/lib/core/config.dart` | Ajout `scope` à `walletHistoryUrl` |
| `mobile/lib/features/wallet/data/wallet_history_api.dart` | Ajout `scope` à `fetchHistory` |
| `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` | `mode: 'performance_value', scope: 'crypto'` |

## Global Performance Value Series Definition

### Formule

```
global_crypto_performance_value(t) = realized_pnl_cumulated(t) + Σ unrealized_pnl_i(t)
```

Où pour chaque asset `i` :
```
unrealized_pnl_i(t) = position_i(t) × price_i(t) - cost_basis_i(t)
```

### Tracking incrémental (multi-assets)

```python
# État global
realized_pnl = 0        # cumulé sur TOUS les assets

# État par asset
positions[asset]         # position courante
cost_basis[asset]        # coût total de la position courante

# À chaque BUY :
cost_basis[asset] += amount × price_ref
positions[asset] += amount

# À chaque SELL :
avg_cost = cost_basis[asset] / positions[asset]
realized_pnl += amount × (price_ref - avg_cost)    # PnL réalisé global
cost_basis[asset] -= amount × avg_cost

# À chaque timestamp :
unrealized = Σ (positions[a] × price(a,t) - cost_basis[a])
total_pnl = realized_pnl + unrealized
```

### Cohérence

La méthode de coût moyen pondéré est identique à celle de `build_wallet_statistics`, qui calcule les métriques "Gains en cours", "Gains encaissés", et "Total des gains".

## Granularity Selection Rule

La granularité est déterminée par le **trade le plus ancien** parmi TOUS les assets crypto du client :

```python
first_trade_ts = orders[0].created_at  # query triée par created_at ASC, tous assets
span_hours = (now - first_trade_ts) / 3600
```

| Span | Granularité | Table |
|------|-------------|-------|
| 0–2h | 1 minute | `market_data_bars_1m` |
| 2h–7d | 5 minutes | `market_data_bars_5m` |
| 7d–30d | 1 heure | `market_data_bars_1h` |
| 30d–120d | 4 heures | `market_data_bars_4h` |
| >120d | 1 jour | `market_data_bars_1d` |

La grille temporelle est **unique** pour toute la série. Les bougies de TOUS les assets sont chargées sur la même granularité. La timeline combine les timestamps de trades + les timestamps de bougies de l'asset ayant le plus de bougies.

## Flutter Integration

### AllCryptoPositionsScreen (hero chart)

```dart
// AVANT : NAV brute globale
final data = await _historyApi.fetchHistory(period: 'ALL');

// APRÈS : performance monétaire globale
final data = await _historyApi.fetchHistory(
  period: 'ALL',
  mode: 'performance_value',
  scope: 'crypto',
);
```

### Chaîne complète

```
Flutter AllCryptoPositionsScreen._loadHeroSparkline()
  → fetchHistory(period: 'ALL', mode: 'performance_value', scope: 'crypto')
  → GET /api/mobile/flutter/wallet/history?period=ALL&mode=performance_value&scope=crypto

Next.js proxy
  → forward period, mode, scope
  → GET /api/app/wallet/history?period=ALL&mode=performance_value&scope=crypto

Backend router
  → build_wallet_history(db, client_id, ref_currency, asset=None, mode='performance_value')
  → _build_performance_value(sorted_ts, trade_events, ...)
  → série globale : realized_pnl + Σ unrealized_pnl_i
```

### Rendu

- Montant en haut : valeur totale actuelle du portefeuille crypto (INCHANGÉ)
- Courbe : performance monétaire globale (PnL cumulé)
- La courbe commence à 0€ (au premier trade, performance = 0)
- Si le portefeuille est en perte : courbe sous 0
- Si le portefeuille est en gain : courbe au-dessus de 0

## Validation Scenarios

### Scenario 1 : BTC acheté hier, ETH et SOL aujourd'hui

- Granularité : déterminée par BTC (le plus ancien)
- Courbe All Crypto = perf BTC + perf ETH + perf SOL
- Au moment de chaque achat : la performance de ce wallet est 0€
- La courbe totale reflète les gains/pertes cumulés

### Scenario 2 : Nouveau trade ETH ajouté

- La courbe All Crypto change (ETH contribue au PnL global)
- La courbe BTC asset-level ne change PAS (appel avec `asset=BTC`)

### Scenario 3 : Wallet entièrement soldé

- `realized_pnl` reste pris en compte (gain/perte encaissé)
- `unrealized_pnl` de cet asset = 0 (position = 0, cost_basis = 0)
- La performance globale reste cohérente

### Scenario 4 : Dernier point live

- Le dernier point = `realized_pnl + Σ (pos_i × live_price_i - cost_basis_i)`
- Calculé depuis `MarketDataLatestQuote` (même source que la valeur affichée)
- Cohérent avec le "Total des gains" agrégé

### Scenario 5 : Granularité

- Si le premier trade date de 2 jours : granularité 5m
- Si un nouveau trade SOL est ajouté aujourd'hui : la granularité reste 5m (BTC est plus ancien)
- L'ajout d'un asset récent n'écrase pas la granularité

## Non-Regression Notes

| Page | Appel | Mode | Changé ? |
|------|-------|------|----------|
| All Crypto hero | `fetchHistory(mode: 'performance_value', scope: 'crypto')` | `performance_value` | **OUI** |
| Crypto Wallet Detail hero | `fetchHistory(asset: 'BTC', mode: 'performance_value')` | `performance_value` | Non |
| Statistics chart | `fetchHistory(period: '1W', asset: 'BTC')` | `value` (défaut) | Non |
| Statistics initial load | `fetchHistory(period: '1M', asset: 'ETH')` | `value` (défaut) | Non |

Les paramètres `scope` et `mode` sont optionnels avec des valeurs par défaut (`mode='value'`, `scope=None`). Aucun appelant existant n'est impacté.

## Final Status

| Élément | État |
|---------|------|
| Paramètre `scope` (router, proxy, Flutter) | **AJOUTÉ** |
| Logique backend `performance_value` multi-assets | **DÉJÀ EN PLACE** (aucune modification) |
| All Crypto hero chart | **UTILISE `performance_value`** |
| Montant total en haut | **INCHANGÉ** (valeur actuelle du portefeuille) |
| Granularité unique | **CORRECTE** (trade le plus ancien) |
| Dernier point live | **CORRECT** (realized + Σ unrealized via MarketDataLatestQuote) |
| Non-régression asset-level | **OK** |
| Non-régression Statistics | **OK** |
