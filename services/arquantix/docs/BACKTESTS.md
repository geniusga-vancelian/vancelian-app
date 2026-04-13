# Backtesting Engine — Documentation

**Source de vérité pour le moteur de backtesting Arquantix**

---

## Vue d'Ensemble

Le moteur de backtesting permet d'évaluer des stratégies d'investissement sur des données historiques. Les backtests sont **reproductibles** et utilisent la même logique que la production (garantie de cohérence).

---

## Filtrage des Instruments

### Instruments Disponibles

Les backtests utilisent **uniquement** les instruments qui :

1. **`provider = 'yahoo'`** : Uniquement les instruments importés depuis Yahoo Finance
2. **`is_active = 'true'`** : Uniquement les instruments actifs (STRING, pas boolean)
3. **Ont au moins un bar** : Au moins une ligne dans `market_data_bars_d1`

### Endpoint

**`GET /api/backtests/instruments`**

**Paramètres par défaut** :
- `provider=yahoo` (obligatoire)
- `has_bars=true` (obligatoire)
- `is_active=true` (par défaut)

**Réponse** :
```json
[
  {
    "id": 1,
    "symbol": "BTCUSD",
    "name": null,
    "asset_class": "crypto",
    "weekend_tradable": true
  }
]
```

### Exclusion Automatique

- Instruments avec `provider != 'yahoo'` → **Jamais affichés**
- Instruments avec `is_active = 'false'` → **Jamais affichés**
- Instruments sans bars → **Jamais affichés**
- Instruments archivés (`archived_at IS NOT NULL`) → **Jamais affichés**

---

## Weekend Trading

### Règles

- **Crypto** (`asset_class = 'crypto'`) : **Tradable** le weekend
- **Equities/ETFs** (`asset_class IN ('equity', 'etf')`) : **Non tradable** le weekend

### Implémentation

Le champ `weekend_tradable` est stocké comme **STRING "true" ou "false"** (pas boolean).

**⚠️ NE JAMAIS CHANGER** : Le type doit rester STRING pour compatibilité.

### Logique de Trading

```python
# Pseudo-code
if date.weekday() >= 5:  # Saturday (5) or Sunday (6)
    if instrument.weekend_tradable == "true":
        # Trade allowed
    else:
        # Skip this date (no trade)
```

---

## Convention Open-to-Open

### Principe

Les backtests utilisent le **prix d'ouverture** (`open`) pour les calculs de performance.

**Pourquoi ?**
- Représente le prix auquel on peut réellement trader
- Évite le look-ahead bias
- Cohérent avec la production

### Implémentation

```python
# Pseudo-code
for date in trading_dates:
    # Get open price for this date
    bar = get_bar(instrument_id, date)
    price = bar.open  # NOT bar.close
    
    # Calculate position value
    position_value = shares * price
```

**⚠️ NE JAMAIS CHANGER** : Cette convention est fondamentale pour la cohérence.

---

## NAV Base 100

### Principe

Le NAV (Net Asset Value) est normalisé à 100 au début du backtest.

**Calcul** :
```python
nav_base100[0] = 100.0

for i in range(1, len(dates)):
    return = (current_price / previous_price) - 1
    nav_base100[i] = nav_base100[i-1] * (1 + return)
```

### Garantie

Le NAV base 100 permet de comparer différentes stratégies sur la même échelle, indépendamment du capital initial.

---

## Rebalancing

### Fréquences Supportées

- **Daily** : Rebalance chaque jour
- **Weekly** : Rebalance chaque lundi (weekday 0)
- **Monthly** : Rebalance le 1er de chaque mois

### Logique

```python
def should_rebalance(current_date, last_rebalance_date, rebalance_freq):
    if last_rebalance_date is None:
        return True  # First day
    
    if rebalance_freq == "daily":
        return True
    elif rebalance_freq == "weekly":
        return current_date.weekday() == 0  # Monday
    elif rebalance_freq == "monthly":
        return current_date.day == 1
```

---

## Métriques Calculées

### Métriques Portfolio

- **Total Return** : `(nav_final / nav_initial) - 1`
- **CAGR** : Annualized return
- **Volatility** : Écart-type annualisé des returns
- **Sharpe Ratio** : `(CAGR - risk_free_rate) / volatility`
- **Max Drawdown** : Plus grande perte depuis un pic
- **Calmar Ratio** : `CAGR / abs(max_drawdown)`

### Métriques par Instrument

- **Total Return** : Performance individuelle
- **Volatility** : Volatilité individuelle
- **Sharpe Ratio** : Ratio de Sharpe individuel

### Stockage

Les métriques sont stockées dans `backtest_metrics` :

```sql
CREATE TABLE backtest_metrics (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    scope VARCHAR(20) NOT NULL,        -- "portfolio" or "instrument"
    instrument_id INTEGER NULL,        -- NULL for portfolio metrics
    key VARCHAR(50) NOT NULL,           -- "cagr", "sharpe", "max_drawdown", etc.
    value NUMERIC(20, 8) NOT NULL,
    UNIQUE (run_id, scope, instrument_id, key)
);
```

---

## Relations Base de Données

### Tables Impliquées

#### `market_data_instruments`
- Définit les instruments disponibles
- Filtre : `provider='yahoo'` et `is_active='true'`

#### `market_data_bars_d1`
- Données historiques (OHLCV)
- Utilisé pour calculer les returns
- Convention : utiliser `open` (pas `close`)

#### `backtest_runs`
- Exécution d'un backtest
- Stocke : dates, stratégie, paramètres, instrument_ids

#### `backtest_portfolio_series`
- Série temporelle du portfolio
- Colonnes : `nav_base100`, `portfolio_return`, `drawdown`, `turnover`, `costs`

#### `backtest_instrument_series`
- Série temporelle par instrument
- Colonnes : `base100`, `instrument_return`

#### `backtest_metrics`
- Métriques calculées (Sharpe, Calmar, etc.)
- Scope : `portfolio` ou `instrument`

### Relations

```
backtest_runs
  ├── instrument_ids_json (List[int]) → market_data_instruments.id
  ├── backtest_portfolio_series (1:N)
  ├── backtest_instrument_series (1:N)
  └── backtest_metrics (1:N)
```

---

## Garantie de Reproductibilité

### Même Logique Production

Le code du backtest engine est **identique** à la logique de production.

**Garantie** :
- Si un backtest montre X% de return, la production peut atteindre X% (sous réserve de slippage/fees)
- Pas de divergence entre backtest et production

### Paramètres Réalistes

- **Fees** : Configurable en bps (basis points)
- **Slippage** : Configurable en bps
- **Weekend trading** : Respecte les règles par asset class

---

## Exécution d'un Backtest

### Flux

1. **User sélectionne instruments** → Frontend `/admin/backtests`
2. **User configure stratégie** → Equal weight ou Momentum
3. **User configure dates** → Start date, end date
4. **User configure rebalance** → Daily, weekly, monthly
5. **POST /api/backtests/run** → Backend FastAPI
6. **Load bars** → `market_data_bars_d1` pour chaque instrument
7. **Run backtest** → Calcul NAV, returns, métriques
8. **Store results** → `backtest_runs`, `backtest_metrics`, `backtest_*_series`
9. **Return results** → Frontend affiche charts et métriques

### Synchronous Execution

Les backtests sont exécutés **synchroniquement** (pas de queue).

**Limitation actuelle** : Grands univers ou longues périodes peuvent prendre du temps.

**Recommandation future** : Implémenter queue asynchrone si nécessaire.

---

## Stratégies Supportées

### Equal Weight

**Description** : Répartition égale entre tous les instruments sélectionnés.

**Calcul** :
```python
weight_per_instrument = 1.0 / len(instruments)
```

### Momentum

**Description** : Sélection des instruments avec meilleure performance sur `lookback_days`.

**Calcul** :
```python
# Calculate returns over lookback period
returns = calculate_returns(instruments, lookback_days)

# Select top performers
selected = sorted(returns, reverse=True)[:top_n]

# Equal weight among selected
weight_per_selected = 1.0 / len(selected)
```

**Paramètre** : `lookback_days` (ex: 20 jours)

---

## Limitations Actuelles

1. **Synchronous execution** : Pas de queue asynchrone
2. **Petits univers** : Optimisé pour < 20 instruments
3. **Pas de short selling** : Long only
4. **Pas de leverage** : Pas de marge

---

## Checklist Avant Modification

Avant de modifier le backtest engine, vérifier :

- [ ] J'ai lu ce document en entier
- [ ] Je comprends la convention open-to-open
- [ ] Je n'ai pas changé le type de `weekend_tradable` (STRING)
- [ ] J'ai testé avec des instruments Yahoo uniquement
- [ ] J'ai vérifié que les métriques sont cohérentes
- [ ] J'ai documenté les changements

---

**Dernière mise à jour:** 2026-01-09

