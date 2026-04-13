# All Crypto NAV Source Fix Report

## Executive Summary

Le patch visuel précédent (WALLET_HISTORY_SPIKE_FIX_REPORT) avait mal identifié le problème. Le vrai enjeu n'était pas un problème de rendu/hauteur de courbe, mais un besoin de validation que la **donnée source** du hero chart "All Crypto" est bien une série NAV globale crypto correcte.

**Résultat de l'audit** : la donnée source backend (`build_wallet_history` sans paramètre `asset`) construit bien la NAV globale `Σ position_i(t) × price_i(t)` sur une grille temporelle unique. La chaîne Flutter → Next.js → Backend est correcte.

**Action réalisée** : revert des hacks visuels (minimum visual range artificiel) qui déformaient l'échelle verticale du graphique. Les correctifs backend utiles sur la donnée (fallback execution price, pas de prix futur) sont conservés.

## Wrong Fix Reverted

### Ce qui a été reverté

| Fichier | Changement reverté | Raison |
|---------|-------------------|--------|
| `line_chart_module.dart` | `minRange = mid.abs() * 0.05` + `baseMin = mid - range / 2` | Écrasait artificiellement l'amplitude du chart, le rendant plat |
| `wallet_statistics_screen.dart` | Même logique dans `_computeChartGeometry` | Même problème : déformation de l'échelle Y |

### Avant revert (mauvais)

```dart
// Forçait un range minimum de 5% du midpoint
var range = rawMax - rawMin;
final mid = (rawMin + rawMax) / 2;
if (mid.abs() > 0.01) {
  final minRange = mid.abs() * 0.05;
  if (range < minRange) range = minRange;
}
final baseMin = mid - range / 2;
```

Effet : une variation réelle de 1€ sur une base de 983€ n'occupait que 2% de la hauteur du chart au lieu de 100%. La courbe devenait plate et illisible.

### Après revert (correct)

```dart
// Normalisation standard min/max : la courbe occupe toute la hauteur
final minY = values.reduce(math.min);
final maxY = values.reduce(math.max);
final range = (maxY - minY).clamp(0.001, double.infinity);
ys.add(size.height - (values[i] - minY) / range * size.height);
```

### Ce qui a été conservé

| Fichier | Changement conservé | Raison |
|---------|-------------------|--------|
| `service.py` | `_interpolate_price` retourne `None` au lieu de la 1ère bougie future | Évite d'injecter un prix futur dans des timestamps passés |
| `service.py` | Fallback `execution_prices[a]` quand `cp is None` | Carry-forward du prix d'exécution, évite les trous de valorisation |
| `all_crypto_positions_screen.dart` | Raw values au lieu de pré-normalisation `[0,1]` | Simplification : le painter normalise déjà en interne |
| `crypto_wallet_detail_screen.dart` | Idem | Idem |

## All Crypto Data Source Audit

### Chaîne complète

```
Flutter AllCryptoPositionsScreen._loadHeroSparkline()
  → WalletHistoryApi.fetchHistory(period: 'ALL')   // pas de paramètre asset
  → Config.walletHistoryUrl('ALL')
  → GET /api/mobile/flutter/wallet/history?period=ALL

Next.js proxy (web/src/app/api/mobile/flutter/wallet/history/route.ts)
  → asset = null (pas dans les params)
  → GET /api/app/wallet/history?period=ALL

Backend (api/services/test_clients/router.py)
  → get_wallet_history(period='ALL', asset=None)
  → build_wallet_history(db, client_id, reference_currency, asset=None)
```

**Verdict** : la chaîne est correcte. `asset=None` déclenche le path global dans le backend.

### Backend `build_wallet_history(asset=None)`

Logique vérifiée point par point :

| Étape | Code | Correct ? |
|-------|------|-----------|
| 1. Charger tous les orders completed du client | `q = db.query(ExchangeOrder).filter(client_id, status="completed")` (pas de filtre asset) | ✅ |
| 2. Identifier tous les assets tradés | `traded_assets = {o.asset for o in orders}` | ✅ |
| 3. Trouver le trade le plus ancien | `first_trade_ts = orders[0].created_at` (query triée par `created_at.asc()`) | ✅ |
| 4. Choisir UNE granularité commune | `_select_granularity(span_hours)` basé sur `now - first_trade_ts` | ✅ |
| 5. Charger les bougies pour TOUS les assets | `_load_all_candles(model)` itère sur `asset_to_provider` | ✅ |
| 6. Construire UNE grille temporelle | `all_timestamps` = trade timestamps + candle timestamps >= `first_trade_ts` | ✅ |
| 7. Pour chaque timestamp, cumuler TOUS les assets | `wallet_value += pos * price` pour chaque asset avec `pos > 0` | ✅ |
| 8. Injecter le dernier point live | `live_value = Σ pos_i × MarketDataLatestQuote_i` | ✅ |

## Global NAV Reconstruction Logic

La formule implémentée est exactement celle demandée :

```
global_crypto_nav(t) = Σ asset_nav_i(t)
```

où `asset_nav_i(t) = position_i(t) × price_i(t)` avec :

- **Trade timestamps** : `price_i = execution_price` (prix réel payé)
- **Inter-trade timestamps** : `price_i = candle.close` converti en EUR via `EURUSDT`
- **Fallback si pas de bougie** : `price_i = last_execution_price` (carry-forward)
- **Dernier point** : `price_i = MarketDataLatestQuote.last_price`

### Positions

```python
for each trade up to timestamp t:
    if side == "buy":  positions[asset] += amount_crypto
    if side == "sell": positions[asset] -= amount_crypto
```

### Valorisation

```python
wallet_value = 0
for asset, position in positions.items():
    if position > 0:
        price = candle_close(asset, t) or execution_price(asset)
        wallet_value += position * price_eur
```

## Granularity Selection

La granularité est déterminée par le span entre `first_trade_ts` (le trade le plus ancien parmi TOUS les assets) et `now` :

| Span | Granularité | Table |
|------|-------------|-------|
| 0–2h | 1 minute | `market_data_bars_1m` |
| 2h–7d | 5 minutes | `market_data_bars_5m` |
| 7d–30d | 1 heure | `market_data_bars_1h` |
| 30d–120d | 4 heures | `market_data_bars_4h` |
| >120d | 1 jour | `market_data_bars_1d` |

Si aucune bougie n'existe dans la granularité sélectionnée, le système fait un fallback vers des granularités plus grossières (5m → 1h → 4h → 1d).

La grille temporelle est **unique** : les timestamps de la série viennent de l'asset ayant le plus de bougies (`best_candle_source`), ce qui garantit la meilleure résolution disponible sur une seule grille.

## Flutter Integration

### AllCryptoPositionsScreen (hero chart)

```dart
Future<void> _loadHeroSparkline() async {
  final data = await _historyApi.fetchHistory(period: 'ALL');  // ← pas d'asset
  final values = data.points.map((p) => p.walletValue).toList();
  setState(() => _heroSparkline = values);  // ← valeurs brutes EUR
}
```

Le `LineChartModule` reçoit les valeurs brutes et son `_LineChartPainter` applique la normalisation min/max standard pour les mapper sur la hauteur du canvas.

### CryptoWalletDetailScreen (hero chart asset-level)

```dart
final data = await _historyApi.fetchHistory(period: 'ALL', asset: widget.asset);
```

Passe `asset` → le backend filtre sur cet asset uniquement. Pas de confusion avec la série globale.

### Rendu (après revert)

Le `_LineChartPainter` utilise la normalisation min/max standard :
- `minY = min(values)`, `maxY = max(values)`, `range = maxY - minY`
- Chaque point est mappé sur `[0, height]` proportionnellement
- La courbe occupe toute la hauteur disponible, fidèle aux données réelles

## Validation Scenarios

### 1. La courbe All Crypto ≠ courbes individuelles

- **Attendu** : Si BTC et ETH sont détenus, la courbe globale montre `BTC_value + ETH_value` à chaque timestamp, pas la courbe de l'un ou l'autre.
- **Vérifié** : Le backend somme `wallet_value += pos * price` pour chaque asset avec position > 0.

### 2. Valeur finale = valeur affichée en haut

- **Attendu** : Le dernier point du chart = `totalValue` affiché dans le hero.
- **Vérifié** : Le dernier point live utilise `MarketDataLatestQuote` pour chaque asset, la même source que l'API `crypto/positions` qui alimente `totalValue`.

### 3. Multi-assets pris en compte

- **Attendu** : Si BTC, ETH et SOL existent, la NAV globale inclut les 3.
- **Vérifié** : `traded_assets = {o.asset for o in orders}` sans filtre → tous les assets sont inclus.

### 4. Un trade ETH modifie All Crypto mais pas BTC

- **Attendu** : Ajouter un ordre ETH modifie la courbe globale mais pas la courbe BTC.
- **Vérifié** : La courbe BTC utilise `fetchHistory(asset: 'BTC')` → filtre backend `ExchangeOrder.asset == 'BTC'`. La courbe globale utilise `fetchHistory()` sans asset → tous les ordres.

### 5. Granularité déterminée par le trade le plus ancien

- **Attendu** : Si le premier trade BTC date de 3 jours, la granularité est 5m (2h–7d).
- **Vérifié** : `span_hours = (now - first_trade_ts).total_seconds() / 3600` → `_select_granularity(span_hours)` applique la règle.

## Final Status

| Élément | État |
|---------|------|
| Hack visuel (minRange 5%) | **REVERTÉ** dans `_LineChartPainter` et `_computeChartGeometry` |
| Donnée source All Crypto | **CORRECTE** — NAV globale `Σ position_i × price_i` |
| Granularité unique | **CORRECTE** — basée sur le trade le plus ancien |
| Dernier point live | **CORRECT** — `Σ pos_i × MarketDataLatestQuote_i` |
| Rendu du chart | **RESTAURÉ** — normalisation min/max standard, amplitude fidèle |
| Correctifs backend utiles | **CONSERVÉS** — no-future-candle, execution price fallback |
| Régressions | **AUCUNE** — hero charts asset-level et Statistics non impactés |
