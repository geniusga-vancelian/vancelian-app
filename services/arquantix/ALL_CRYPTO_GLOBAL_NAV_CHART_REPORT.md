# All Crypto — Global NAV Chart

## Executive Summary

Le hero chart de la page "All Crypto" (`AllCryptoPositionsScreen`) affichait des **données mock** — aucun appel API n'était fait. Le `LineChartModule` était utilisé sans paramètre `data`, ce qui activait un jeu de données statique interne au widget.

Le backend `build_wallet_history()` sans paramètre `asset` calcule déjà correctement la NAV crypto globale : il charge tous les ordres de tous les assets, choisit une granularité unique basée sur le trade le plus ancien, et reconstruit `global_nav(t) = Σ position_i(t) × price_i(t)`.

**Fix** : brancher le hero chart sur l'API existante `GET /api/app/wallet/history?period=ALL` (sans `asset`).

---

## Current State Audit

### Avant correction

| Élément | État |
|---------|------|
| Hero chart `AllCryptoPositionsScreen` | `LineChartModule` **sans `data`** → mock |
| Appel API pour le chart | **Aucun** |
| Série affichée | Mock statique (identique à chaque visite) |
| Cohérence avec la NAV totale | Aucune (mock) |

### `LineChartModule` sans `data`

```dart
heroFullBleed: const LineChartModule(
  height: 80,
  strokeWidth: 3,
  lineColor: Colors.white,
  paddingTop: 8,
  paddingBottom: 8,
),
// → data: null → utilise mockLineChartData100
```

---

## Backend Logic

### Endpoint utilisé

```
GET /api/app/wallet/history?period=ALL
```

Sans `asset` → mode global portefeuille.

### Flux backend (`build_wallet_history` sans `asset`)

1. **Charge tous les ordres** : `ExchangeOrder.status == "completed"` pour le client, tous assets confondus
2. **Identifie le trade le plus ancien** : `orders[0].created_at` (trié ASC)
3. **Choisit UNE granularité** : `_select_granularity(span_hours)` basée sur `(now - oldest_trade)`
4. **Charge les candles** : pour chaque asset dans `traded_assets`, avec le même `bar_model`
5. **Reconstruit les positions** : `positions[asset] += amount` pour chaque BUY, `-= amount` pour chaque SELL
6. **Valorise à chaque timestamp** : `wallet_value = Σ position_i × price_i` (conversion EUR via FX candles)
7. **Filtre** : points à position zéro exclus, points à valeur zéro exclus
8. **Live injection** : dernier point = `Σ position_i × live_price_i` depuis `MarketDataLatestQuote`

### Aucune modification backend nécessaire

Le code existant fait exactement le calcul demandé.

---

## Granularity Selection Rule

```python
_GRANULARITY_CONFIG = [
    (2, MarketDataBar1m, 60),        # 0–2h      → 1m
    (168, MarketDataBar5m, 300),     # 2h–7d     → 5m
    (720, MarketDataBar1h, 3600),    # 7d–30d    → 1h
    (2880, MarketDataBar4h, 14400),  # 30d–120d  → 4h
    (None, MarketDataBar1d, 86400),  # >120d     → 1d
]
```

La granularité est déterminée par `span_hours = (now - oldest_trade_across_all_assets) / 3600`.

Exemple : si le plus ancien trade crypto date de 45 jours → `span_hours ≈ 1080` → granularité `4h` (config index 3).

**Tous les assets** utilisent la même table de candles (`MarketDataBar4h` dans cet exemple) et la même grille temporelle.

---

## Global NAV Reconstruction

### Formule

```
global_nav(t) = Σ [position_asset_i(t) × price_asset_i(t)]
```

### Prix à chaque timestamp

| Contexte | Source du prix |
|----------|---------------|
| Timestamp = trade de l'asset i | `execution_prices[i]` (EUR per unit, from order) |
| Timestamp entre trades | `candle.close` interpolé → converti en EUR via FX |
| Dernier point (live) | `MarketDataLatestQuote.last_price` → `usdt_to_eur()` |

### Exemple avec BTC + ETH

```
t₁ : Buy 0.01 BTC @ 80,000€
  positions = {BTC: 0.01}
  nav = 0.01 × 80,000 = 800€

t₂ : Buy 0.5 ETH @ 3,200€
  positions = {BTC: 0.01, ETH: 0.5}
  nav = 0.01 × candle_BTC_eur + 0.5 × 3,200 = 780 + 1,600 = 2,380€

t₃ : candle timestamp
  nav = 0.01 × candle_BTC_eur + 0.5 × candle_ETH_eur

t_live : now
  nav = 0.01 × live_BTC_eur + 0.5 × live_ETH_eur
```

---

## Flutter Integration

### Fichier modifié

`mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart`

### Changements

1. **Import** : ajout de `wallet_history_api.dart`
2. **State** : ajout de `_heroSparkline` et `_historyApi`
3. **`_loadHeroSparkline()`** : appel `fetchHistory(period: 'ALL')` sans `asset` → normalisation min/max → `setState`
4. **Hero chart** : `LineChartModule(data: _heroSparkline)` au lieu de `const LineChartModule()`
5. **Refresh** : `_loadHeroSparkline()` appelé aussi dans `onRefresh`

### Code ajouté

```dart
final WalletHistoryApi _historyApi = const WalletHistoryApi();
List<double>? _heroSparkline;

Future<void> _loadHeroSparkline() async {
  try {
    final data = await _historyApi.fetchHistory(period: 'ALL');
    if (!mounted || data.points.isEmpty) return;
    final values = data.points.map((p) => p.walletValue).toList();
    final mn = values.reduce((a, b) => a < b ? a : b);
    final mx = values.reduce((a, b) => a > b ? a : b);
    final range = (mx - mn).clamp(0.001, double.infinity);
    final normalised = values.map((v) => (v - mn) / range).toList();
    setState(() => _heroSparkline = normalised);
  } catch (_) {}
}
```

### Hero chart dynamique

```dart
heroFullBleed: _heroSparkline != null
    ? LineChartModule(
        data: _heroSparkline,
        height: 80,
        strokeWidth: 3,
        lineColor: Colors.white,
        paddingTop: 8,
        paddingBottom: 8,
      )
    : const SizedBox(height: 80),
```

### Pas de recalcul local

La courbe est entièrement produite par le backend. Flutter normalise uniquement pour l'affichage sparkline (min/max → [0, 1]).

---

## Validation Scenarios

### Scénario 1 : Chart global ≠ charts individuels

| Vérification | Attendu |
|-------------|---------|
| Chart "All Crypto" | Courbe = somme BTC + ETH + SOL + ... |
| Chart BTC (detail page) | Courbe = BTC uniquement |
| Les deux diffèrent | ✅ (si plusieurs assets détenus) |

### Scénario 2 : Série = somme cohérente des assets

| Vérification | Attendu |
|-------------|---------|
| `global_nav(t) = Σ position_i(t) × price_i(t)` | ✅ |
| Pas de double comptage | ✅ |
| Pas d'asset manquant | ✅ |

### Scénario 3 : Granularité unique

| Vérification | Attendu |
|-------------|---------|
| Tous les assets utilisent le même `bar_model` | ✅ |
| Granularité basée sur le trade le plus ancien | ✅ (`orders[0].created_at`) |
| Pas de mélange M1 + 1H | ✅ |

### Scénario 4 : Trade le plus ancien détermine la granularité

| Cas | Trade le plus ancien | Span | Granularité |
|-----|---------------------|------|-------------|
| BTC acheté il y a 1h | 1h | 1h | M1 (60s) |
| BTC acheté il y a 3 jours | 3j | 72h | M5 (300s) |
| BTC acheté il y a 45 jours | 45j | 1080h | 4H (14400s) |
| BTC acheté il y a 6 mois | 180j | 4320h | 1D (86400s) |

### Scénario 5 : Dernier point = valeur totale

| Vérification | Attendu |
|-------------|---------|
| Dernier point du chart | = `Σ position_i × live_price_i` |
| Valeur affichée en haut (subtitle) | = `data.totalValueEur` |
| Cohérence | ✅ (même source : `MarketDataLatestQuote`) |

### Scénario 6 : Pas de régression asset-level

| Page | Comportement |
|------|-------------|
| CryptoWalletDetailScreen (BTC) | `fetchHistory(asset: 'BTC')` → inchangé |
| WalletStatisticsScreen (BTC) | `fetchHistory(asset: 'BTC')` → inchangé |
| AllCryptoPositionsScreen | `fetchHistory()` sans asset → global |

---

## Fichier modifié

| Fichier | Modification |
|---------|-------------|
| `mobile/lib/features/wallet/presentation/screens/all_crypto_positions_screen.dart` | Import `WalletHistoryApi`, ajout `_heroSparkline` + `_loadHeroSparkline()`, hero chart dynamique, refresh |

---

## Final Status

| Critère | Statut |
|---------|--------|
| Chart "All Crypto" = NAV crypto globale | ✅ |
| Série = `Σ position_i × price_i` | ✅ |
| Granularité unique pour toute la série | ✅ |
| Basée sur le trade le plus ancien | ✅ |
| Dernier point = valeur live totale | ✅ |
| Backend inchangé | ✅ |
| Pages asset-level inchangées | ✅ |
| Pas de recalcul côté Flutter | ✅ |
