# Wallet Historical Value Chart — Implementation Report

## 1. Executive Summary

Le module **Wallet Historical Value Chart v1** est implémenté de bout en bout :
- **Backend** : endpoint `GET /api/app/wallet/history` reconstruit dynamiquement `wallet_value(t) = Σ position_i(t) × price_i(t)` à partir des trades exécutés et des chandelles OHLC.
- **Flutter** : widget `HistoricalWalletValueChart` intégré dans `CryptoWalletDetailScreen` avec sélecteur de période (1D, 1W, 1M, ALL).
- **Tests** : 6 tests backend couvrant les cas vides, BUY, BUY+SELL, conversion EUR, limite 500 points, et filtrage par période.

Aucune série historique n'est stockée en base. Tout est recalculé à la volée.

## 2. Files Modified / Created

| Fichier | Rôle |
|---------|------|
| `api/services/wallet_history/__init__.py` | **NEW** — Package init |
| `api/services/wallet_history/service.py` | **NEW** — Service de reconstruction de la série wallet_value(t) |
| `api/services/test_clients/router.py` | **MODIFIED** — Ajout endpoint `GET /api/app/wallet/history` |
| `api/tests/test_wallet_history.py` | **NEW** — 6 tests de couverture |
| `web/src/app/api/mobile/flutter/wallet/history/route.ts` | **NEW** — Proxy Next.js pour Flutter |
| `mobile/lib/core/config.dart` | **MODIFIED** — Ajout `walletHistoryUrl(period)` |
| `mobile/lib/features/wallet/data/wallet_history_api.dart` | **NEW** — Client API Flutter |
| `mobile/lib/features/wallet/presentation/widgets/historical_wallet_value_chart.dart` | **NEW** — Widget chart avec sélecteur de période |
| `mobile/lib/features/wallet/presentation/screens/crypto_wallet_detail_screen.dart` | **MODIFIED** — Intégration du chart + sparkline hero |

## 3. Reconstruction Logic

### Algorithme

1. **Charger les trades** : `exchange_orders WHERE status='completed' AND client_id=X ORDER BY created_at`
2. **Identifier les actifs** tradés et résoudre les `instrument_id` correspondants (BTCUSDT, ETHUSDT, etc.)
3. **Sélectionner la granularité** des chandelles selon l'étendue temporelle :
   - 0–48h → `market_data_bars_5m`
   - 48h–7j → `market_data_bars_1h`
   - 7j–30j → `market_data_bars_4h`
   - >30j → `market_data_bars_1d`
4. **Charger les chandelles** en une seule requête par actif (range complet)
5. **Charger les chandelles EURUSDT** si `reference_currency=EUR`
6. **Construire les timestamps** : union des timestamps de trades + timestamps de chandelles + now
7. **Rejouer les trades** chronologiquement pour reconstruire `position(t)` :
   - BUY → `position[asset] += amount_crypto`
   - SELL → `position[asset] -= amount_crypto`
8. **Calculer wallet_value(t)** pour chaque point :
   - Si timestamp = trade → utiliser `execution_price` (en EUR)
   - Sinon → interpoler depuis la chandelle la plus proche (close)
   - EUR : `price_eur = price_usdt / eurusdt_rate`
   - USD : `price_usd = price_usdt` (direct)
9. **Limiter à 500 points** par échantillonnage (trades toujours conservés)

### Pricing Rules

| Contexte | Source de prix |
|----------|---------------|
| Timestamp de trade | `exchange_orders.price` (exécution EUR) |
| Timestamp intermédiaire (EUR) | `candle.close / eurusdt_candle.close` |
| Timestamp intermédiaire (USD) | `candle.close` directement |

## 4. Performance

- **Requêtes optimisées** : une seule query par actif pour toutes les chandelles (range complet), pas de requête par point
- **Échantillonnage** : si > 500 points, sous-échantillonnage avec préservation des timestamps de trades
- **Granularité adaptative** : 5m pour données récentes, 1d pour historique long — évite de charger des millions de chandelles

### Estimation de charge

| Scénario | Chandelles chargées | Temps estimé |
|----------|---------------------|--------------|
| 1 actif, 30j | ~720 (1h) | < 100ms |
| 3 actifs, 6 mois | ~540 (1d) × 3 | < 200ms |
| 5 actifs, 2 ans | ~730 (1d) × 5 | < 500ms |

## 5. Period Filtering

Le paramètre `period` filtre les points côté backend après reconstruction :

| Period | Fenêtre |
|--------|---------|
| `1D` | Dernières 24h |
| `1W` | Derniers 7 jours |
| `1M` | Derniers 30 jours |
| `ALL` | Depuis le premier trade |

## 6. Flutter Integration

### Widget `HistoricalWalletValueChart`

- Sélecteur de période (chips 1D / 1W / 1M / ALL)
- Graphique `CustomPaint` avec courbe Catmull-Rom lissée
- Dégradé sous la courbe (vert si positif, rouge si négatif)
- Point lumineux sur la dernière valeur
- Indicateur de performance (% variation) en haut à droite
- État loading / vide / erreur

### Intégration

- Placé en première carte du contenu (`CryptoWalletDetailScreen`), avant les Key Info
- Les données normalisées [0..1] sont remontées au hero via callback `onDataLoaded`
- Le mini-chart du hero utilise les données réelles au lieu du mock

## 7. Tests

| Test | Résultat |
|------|----------|
| `test_wallet_history_empty` | PASS — points=[] si aucun trade |
| `test_wallet_history_single_buy` | PASS — série avec valeurs > 0 après un BUY |
| `test_wallet_history_buy_and_sell` | PASS — valeurs réduites après SELL |
| `test_wallet_history_eur_conversion` | PASS — prix EUR < USDT (division par FX) |
| `test_wallet_history_max_500_points` | PASS — série <= 500 points sur 550 jours |
| `test_wallet_history_period_filter` | PASS — 1W contient moins de points que ALL |

## 8. Limitations connues (v1)

1. **Pas de chandelles 1 minute** : la granularité minimale est 5m. Pour les trades dans les 2 dernières heures, la résolution est donc 5m (pas 1m comme dans la PRD initiale).
2. **FX historique approximé** : si les chandelles EURUSDT manquent pour certains timestamps, le fallback est 1.08. Prérequis : backfill robuste des candles EURUSDT.
3. **Pas de cache** : la série est recalculée à chaque requête. Pour un usage intensif, envisager un cache `wallet_value_history` en v2.
4. **Multi-actifs** : supporté nativement (somme des positions × prix par actif).
5. **Swap crypto/crypto** : non supporté (v1 = EUR ↔ crypto uniquement).

## 9. API Contract

```
GET /api/app/wallet/history?period=ALL

Response:
{
  "currency": "EUR",
  "points": [
    {"timestamp": "2025-01-15T10:30:00+00:00", "wallet_value": 7400.00},
    {"timestamp": "2025-01-16T00:00:00+00:00", "wallet_value": 7520.33},
    ...
  ]
}
```

Maximum 500 points. Vide si aucun trade.
