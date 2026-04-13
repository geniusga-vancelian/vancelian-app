# FRONT_PNL_CHART_AND_STATISTICS_FIX_REPORT

## Executive Summary

Alignement complet de la couche UI Flutter avec la vérité comptable backend.

**4 problèmes corrigés** :

1. Les hero charts (wallet + "Mes crypto") affichaient une courbe de P&L (`performance_value`) au lieu de la vraie valeur du portefeuille (`value = qty × price`).
2. Le endpoint `get_crypto_wallet_detail` calculait le PRU et les P&L indépendamment de `build_wallet_statistics`, créant des incohérences.
3. Le toggle "Performance %" du chart statistics recalculait le % côté client au lieu d'utiliser la série `performance_value` du backend (WAC-consistent).
4. Il n'existait aucune page de statistiques portfolio global.

**Résultat** : 21/21 tests backend passent, 0 erreur Flutter, nouvelle page `PortfolioStatisticsScreen` opérationnelle.

---

## Chart Issues Identified

### Problème 1 — Hero sparklines

| Screen | Avant | Après |
|--------|-------|-------|
| `CryptoWalletDetailScreen` | `mode: 'performance_value'` (P&L) | `mode: 'value'` (NAV = qty × price) |
| `AllCryptoPositionsScreen` | `mode: 'performance_value'` (P&L) | `mode: 'value'` (NAV) avec `scope: 'crypto'` |

**Avant** : le hero affichait "1 234,56 €" (total value) mais la sparkline en dessous montrait la courbe de P&L (qui part de ~0). Incohérence visuelle : la courbe ne correspondait pas au montant affiché.

**Après** : la sparkline montre la vraie valeur du wallet dans le temps (`wallet_value(t) = Σ qty_i(t) × price_i(t)`), reconstruite par le backend à partir des `exchange_orders` + OHLC candles + FX. La forme de la courbe correspond désormais au montant affiché.

### Problème 2 — Chart statistics recalcul client-side

**Avant** :
```dart
// Mode "Performance %" — calcul côté client approximatif
return relevant.map((p) => ((p.walletValue / base) - 1) * 100).toList();
```
Le toggle "Performance %" dans `WalletStatisticsScreen` prenait la série `value` et recalculait le % de variation côté client. Cela ne tenait pas compte du WAC, du realized P&L, ni des flux (BUY/SELL).

**Après** : deux séries sont chargées en parallèle depuis le backend :
- `mode: 'value'` → NAV pour l'onglet "Value"
- `mode: 'performance_value'` → P&L WAC-consistent pour l'onglet "Performance %"

Le frontend ne fait plus aucun calcul P&L.

---

## New Chart Computation Logic

### Logique backend (inchangée, déjà correcte)

**Mode `value`** (`wallet_history.service.build_wallet_history`) :
1. Charger tous les `exchange_orders` du client (filtré par asset si demandé)
2. Reconstruire `positions[asset]` step-by-step à chaque trade
3. Pour chaque timestamp candle : `wallet_value = Σ positions[a] × price_candle(a, t)`
4. Dernier point = `MarketDataLatestQuote` (identique au hero "Current Value")

**Mode `performance_value`** (`wallet_history.service._build_performance_value`) :
1. Reconstruire positions + `cost_basis` WAC
2. À chaque trade SELL : `realized_pnl += net_received - (qty × wac_cost_per_unit)`
3. À chaque timestamp : `unrealized = Σ (pos × price - cost_basis)`, `total = realized + unrealized`
4. Points = série de P&L cumulé

### Logique frontend (simplifiée)

- Le frontend affiche directement les `wallet_value` points du backend
- Aucun calcul de P&L côté client
- Toggle Value/Performance % → switch entre deux séries pré-calculées

---

## Wallet Statistics Fix

### Problème identifié

`get_crypto_wallet_detail` (backend) calculait :
```python
avg_price_eur = total_fiat_spent / total_crypto_bought  # GROSS amount / qty
```

`build_wallet_statistics` calculait :
```python
avg_buy_price = sum(qty * exec_price) / sum(qty)  # WAC pur
```

Ces deux calculs donnent des résultats différents car `total_fiat_spent` (= `sum(amount_fiat)`) inclut les frais dans le montant global, tandis que `qty × exec_price` n'inclut pas les frais.

### Fix appliqué

`get_crypto_wallet_detail` délègue maintenant **tous** les calculs P&L à `build_wallet_statistics` :

```python
stats_eur = build_wallet_statistics(db, client.id, asset, reference_currency="EUR")
stats_usd = build_wallet_statistics(db, client.id, asset, reference_currency="USD")

avg_price_eur = Decimal(str(stats_eur["average_entry_price"]))
unrealized_eur = Decimal(str(stats_eur["unrealized_pnl"]))
realized_eur = Decimal(str(stats_eur["realized_pnl"]))
```

**Résultat** : les 3 vues (wallet detail, statistics, charts) utilisent exactement le même calcul WAC. Un seul chemin de code pour le P&L.

### Champs exposés (inchangés côté Flutter)

| Champ UI | Source backend | Calcul |
|----------|---------------|--------|
| Gains en cours | `unrealized_gain_eur` | `current_value - (position × WAC)` |
| Gains encaissés | `realized_gain_eur` | `Σ(net_sell - qty_sold × WAC)` |
| Prix moyen d'achat | `avg_buy_price_eur` | `total_buy_cost / total_bought` (WAC) |
| Total des gains | `total_gain_eur` | `realized + unrealized` |

---

## Portfolio Statistics Page

### Nouvel endpoint backend

**Route** : `GET /api/app/portfolio/statistics`

**Logique** :
1. Charger toutes les `CryptoPosition` du client
2. Pour chaque position active : appeler `build_wallet_statistics`
3. Agréger : `total_value`, `total_invested`, `total_realized`, `total_unrealized`
4. Calculer `roi_pct = total_pnl / total_invested × 100`
5. Calculer allocation (weight = value_asset / total_value × 100)
6. Trier best/worst performers par P&L total

**Réponse** :
```json
{
  "currency": "EUR",
  "total_portfolio_value": 12345.67,
  "total_invested": 10000.00,
  "total_realized_pnl": 500.00,
  "total_unrealized_pnl": 1845.67,
  "total_pnl": 2345.67,
  "roi_pct": 23.46,
  "positions_count": 3,
  "allocation": [...],
  "best_performers": [...],
  "worst_performers": [...]
}
```

### Proxy Next.js

`web/src/app/api/mobile/flutter/portfolio/statistics/route.ts` → forwards to `GET /api/app/portfolio/statistics`

### Flutter Screen

**Fichier** : `lib/features/wallet/presentation/screens/portfolio_statistics_screen.dart`

**5 sections** :

| # | Section | Contenu |
|---|---------|---------|
| 1 | Overview | Total portfolio value, Total invested, Total P&L + ROI % |
| 2 | P&L Breakdown | Realized, Unrealized, Total |
| 3 | Allocation | Liste par asset avec weight %, color-coded |
| 4 | Performance | Chart Value/Performance % avec période 1D/1W/1M/ALL |
| 5 | Best / Worst Performers | Top gainers et losers |

**Accès** : bouton "bar chart" dans la nav bar de `AllCryptoPositionsScreen`.

---

## API Changes

| Action | Endpoint | Description |
|--------|----------|-------------|
| **Nouveau** | `GET /api/app/portfolio/statistics` | Statistiques agrégées portfolio |
| **Nouveau** | Proxy Next.js `/api/mobile/flutter/portfolio/statistics` | Forward vers backend |
| **Modifié** | `GET /api/app/crypto-positions/{asset}` | P&L désormais calculé via `build_wallet_statistics` |
| **Inchangé** | `GET /api/app/wallet/statistics/{asset}` | Aucun changement |
| **Inchangé** | `GET /api/app/wallet/history` | Aucun changement |

---

## UI Changes

| Fichier | Modification |
|---------|-------------|
| `crypto_wallet_detail_screen.dart` | Hero sparkline → `mode: 'value'` |
| `all_crypto_positions_screen.dart` | Hero sparkline → `mode: 'value'` + bouton stats portfolio |
| `wallet_statistics_screen.dart` | Chart dual-mode (value + performance_value backend) |
| `portfolio_statistics_screen.dart` | **Nouveau** — page complète avec 5 sections |
| `portfolio_statistics_api.dart` | **Nouveau** — API client |
| `portfolio_statistics.dart` | **Nouveau** — modèle de données |
| `config.dart` | Ajout `portfolioStatisticsUrl` |

---

## Before / After Comparison

### Hero Sparkline

| | Avant | Après |
|---|-------|-------|
| Source | `mode: 'performance_value'` (P&L) | `mode: 'value'` (NAV) |
| Forme | Part de ~0, monte/descend selon P&L | Forme fidèle à la valeur affichée |
| Cohérence | Incohérent avec le montant hero | Cohérent |

### Wallet Detail P&L

| | Avant | Après |
|---|-------|-------|
| PRU | `sum(amount_fiat) / sum(amount_crypto)` | WAC via `build_wallet_statistics` |
| Unrealized | Calcul local dans service.py | Délégué à `build_wallet_statistics` |
| Realized | Calcul local dans service.py | Délégué à `build_wallet_statistics` |
| Cohérence avec Statistics | Potentiellement différent | Identique (même fonction) |

### Statistics Chart

| | Avant | Après |
|---|-------|-------|
| Value tab | `mode: 'value'` backend | Idem (inchangé) |
| Performance tab | `((value / base) - 1) * 100` client-side | `mode: 'performance_value'` backend (WAC) |

### Portfolio

| | Avant | Après |
|---|-------|-------|
| Page stats global | N'existait pas | `PortfolioStatisticsScreen` avec 5 sections |
| Accès | — | Bouton chart dans nav `AllCryptoPositionsScreen` |

---

## Final Status

| Métrique | Valeur |
|----------|--------|
| Tests backend non-régression | 21/21 |
| Erreurs Flutter analyze | 0 |
| Fichiers backend modifiés | 1 (test_clients/service.py) |
| Fichiers backend créés | 0 |
| Endpoints ajoutés | 1 (portfolio/statistics) |
| Fichiers Flutter modifiés | 4 |
| Fichiers Flutter créés | 3 |
| Modèle comptable impacté | Non |
| BUY / SELL / SWAP impactés | Non |
| Invariants A / B / C impactés | Non |
