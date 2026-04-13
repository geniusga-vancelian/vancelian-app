# Backtests — Exécution & Stratégies

**Fichiers clés**: `api/services/backtest/routes.py`, `api/services/backtest/executor.py`, `api/services/backtest/repository.py`

---

## 1. Entrées possibles

### XOR: `instrument_ids` vs `bundle_id`

**Contrainte**: Un backtest prend en entrée **SOIT** `instrument_ids` **SOIT** `bundle_id` (pas les deux, pas aucun).

**Implémentation** (`api/services/backtest/routes.py:73-98`):

```python
instrument_ids = request.instrument_ids
bundle_allocations = None

if request.bundle_id:
    # Load from bundle
    components = db.query(BundleComponent).filter(...)
    instrument_ids = [comp.instrument_id for comp in components]
    bundle_allocations = {comp.instrument_id: float(comp.weight) for comp in components}
    final_strategy_type = "bundle_strategy"  # Override
else:
    instrument_ids = request.instrument_ids
    final_strategy_type = request.strategy.type

if not instrument_ids or len(instrument_ids) == 0:
    raise HTTPException(status_code=400, detail="instrument_ids or bundle_id must be provided")
```

**Référence**: `api/services/backtest/routes.py:73-114`

---

## 2. Stratégies de rebalancing

### Types de stratégies

**Trois types supportés**:

1. **`equal_weight`**: Poids égal pour chaque instrument (1/n)
2. **`momentum`**: Poids basés sur momentum (retours passés, lookback 20 jours)
3. **`bundle_strategy`**: Poids fixes depuis le bundle (allocations définies)

**Référence**: `api/services/backtest/executor.py:93-144`

### Rebalancing: strategy-based vs fixed target weights

**Strategy-based** (`equal_weight`, `momentum`):
- Poids calculés dynamiquement (égal ou momentum)
- Rééquilibrés selon `rebalance` frequency (daily/weekly/monthly)

**Fixed target weights** (`bundle_strategy`):
- Poids fixes depuis allocations du bundle
- Pas de rééquilibrage (stratégie statique)
- Poids constants pour toutes les dates

**Référence**: `api/services/backtest/executor.py:93-144`

### Fréquence de rebalancing

**Types**: `"daily"`, `"weekly"`, `"monthly"`

**Implémentation** (`api/services/backtest/executor.py:146-157`):

```python
if rebalance == "daily":
    pass  # Already daily
elif rebalance == "weekly":
    weekly_weights = weights_df.resample('W-MON').first()
    weights_df = weekly_weights.reindex(weights_df.index).ffill()
elif rebalance == "monthly":
    monthly_rebalance = weights_df.resample('MS').first()
    weights_df = monthly_rebalance.reindex(weights_df.index).ffill()
```

**Référence**: `api/services/backtest/executor.py:146-157`

---

## 3. Skip rebalance si prix manquant

### Détection de données manquantes

**Validation avant exécution** (`api/services/backtest/executor.py:45-50`):

```python
missing_instruments = [inst.id for inst in instruments if inst.id not in price_data or price_data[inst.id].empty]
if missing_instruments:
    update_backtest_run_status(db, run_id, "FAILED", f"No price data found for instruments: {', '.join(missing_symbols)}")
    return
```

**Référence**: `api/services/backtest/executor.py:45-50`

### Forward fill

**Gestion des prix manquants** (`api/services/backtest/executor.py:78-87`):

```python
# Reindex to calendar, forward fill missing values
df_aligned = df.reindex(pd.DatetimeIndex(calendar))
df_aligned = df_aligned.ffill()  # Forward fill

# Combine into single DataFrame
prices_df = pd.DataFrame(aligned_prices, index=pd.DatetimeIndex(calendar))
prices_df = prices_df.ffill().bfill()  # Forward then backward fill
```

**Implication**: Si un prix est manquant, utilisation du dernier prix connu (forward fill) ou du premier prix connu (backward fill).

**Référence**: `api/services/backtest/executor.py:78-87`

⚠️ **UNKNOWN (needs confirmation)**: Si un prix est manquant le jour de rééquilibrage, le rebalance est-il skippé ou utilise-t-on le prix forward-fillé ?

---

## 4. Drift, turnover, coûts

### Turnover

**Définition**: Changement de poids entre deux périodes.

**Calcul** (`api/services/backtest/executor.py:167-168,183-184`):

```python
weight_changes = weights_df.diff().abs().sum(axis=1)
turnover = weight_changes * 100.0  # En pourcentage
```

**Référence**: `api/services/backtest/executor.py:167-168,183-184`

### Coûts

**Fees et Slippage** (`api/services/backtest/executor.py:162-173`):

```python
fees_per_trade = fees_bps / 10000.0  # Conversion bps → decimal
slippage_per_trade = slippage_bps / 10000.0

# Detect rebalancing: weight changes
rebalance_days = weight_changes > 0.001  # Threshold for rebalancing

# Apply costs
costs = pd.Series(0.0, index=portfolio_returns.index)
costs[rebalance_days] = fees_per_trade + slippage_per_trade
portfolio_returns = portfolio_returns - costs
```

**Référence**: `api/services/backtest/executor.py:162-173`

**Important**: Coûts appliqués uniquement les jours de rééquilibrage (`weight_changes > 0.001`).

---

## 5. Calcul des performances

### NAV (Net Asset Value)

**Calcul** (`api/services/backtest/executor.py:175-177`):

```python
nav_series = (1 + portfolio_returns).cumprod()
nav_base100 = nav_series * 100.0 / nav_series.iloc[0] if len(nav_series) > 0 else pd.Series([100.0])
```

**Base 100**: Normalisation à 100 au début (première valeur = 100).

**Référence**: `api/services/backtest/executor.py:175-177`

### Drawdown

**Calcul** (`api/services/backtest/executor.py:179-181`):

```python
running_max = nav_base100.cummax()
drawdown = (nav_base100 - running_max) / running_max * 100.0  # En pourcentage
```

**Référence**: `api/services/backtest/executor.py:179-181`

### Métriques

**Calcul** (`api/services/backtest/executor.py:234-251`):

```python
total_return = (nav_base100.iloc[-1] / nav_base100.iloc[0] - 1) * 100.0
annualized_return = (1 + total_return / 100.0) ** (252.0 / len(calendar)) - 1
annualized_return_pct = annualized_return * 100.0
volatility = portfolio_returns.std() * np.sqrt(252) * 100.0  # Annualized
sharpe = (annualized_return_pct / volatility) if volatility > 0 else 0.0
max_drawdown = drawdown.min()
```

**Métriques calculées**:
- `total_return` (en %)
- `annualized_return` (en %, basé sur 252 jours/an)
- `volatility` (volatilité annualisée, en %)
- `sharpe_ratio`
- `max_drawdown` (en %)

**Référence**: `api/services/backtest/executor.py:234-251`

---

## 6. Endpoints `/api/backtests`

### `POST /api/backtests/run`

**Request** (`api/services/backtest/routes.py:29-39`):

```json
{
  "name": "Backtest BTC/ETH",
  "start_date": "2021-01-01",
  "end_date": "2026-01-10",
  "instrument_ids": [11, 27],  // OU bundle_id
  "bundle_id": "14",  // OU instrument_ids
  "strategy": {
    "type": "bundle_strategy",  // ou "equal_weight", "momentum"
    "params": {"lookback_days": 20}  // si momentum
  },
  "rebalance": "weekly",
  "fees_bps": 0.0,
  "slippage_bps": 0.0,
  "allow_weekend_trading": true
}
```

**Response** (`api/services/backtest/routes.py:187-196`):

```json
{
  "run_id": 45,
  "id": 45,
  "name": "Backtest BTC/ETH",
  "status": "SUCCESS",  // ou "PENDING", "FAILED"
  "created_at": "2026-01-10T16:00:00",
  "start_date": "2021-01-01",
  "end_date": "2026-01-10",
  "message": "Backtest completed successfully."
}
```

**Référence**: `api/services/backtest/routes.py:56-196`

**Important**: Exécution **synchrone** actuellement (TODO pour async dans production).

**Référence**: `api/services/backtest/routes.py:150-151`

### `GET /api/backtests/{run_id}`

**Response** (`api/services/backtest/routes.py:210-230`):

```json
{
  "run": {
    "id": 45,
    "name": "Backtest BTC/ETH",
    "status": "SUCCESS",
    "created_at": "2026-01-10T16:00:00",
    "start_date": "2021-01-01",
    "end_date": "2026-01-10",
    "effective_start_date": "2021-01-04",  // Première date avec données
    "effective_end_date": "2026-01-10",
    "rebalance": "weekly",
    "strategy_type": "bundle_strategy",
    "strategy_params_json": null,
    "fees_bps": 0.0,
    "slippage_bps": 0.0,
    "allow_weekend_trading": true,
    "instrument_ids_json": [11, 27],
    "bundle_id": "14",
    "error_message": null
  }
}
```

**Référence**: `api/services/backtest/routes.py:199-230`

### `GET /api/backtests/{run_id}/series`

**Response** (`api/services/backtest/routes.py:302-306`):

```json
{
  "portfolio": [
    {
      "date": "2021-01-04",
      "nav_base100": 100.0,
      "portfolio_return": 0.0,
      "drawdown": 0.0,
      "turnover": 0.0,
      "costs": 0.0,
      "weights_json": {"11": 0.8, "27": 0.2},
      "tradable_json": {"11": true, "27": true}
    }
  ],
  "instruments": [
    {
      "instrument_id": 11,
      "symbol": "BTCUSD",
      "series": [
        {
          "date": "2021-01-04",
          "base100": 100.0,
          "instrument_return": 0.0
        }
      ]
    }
  ]
}
```

**Référence**: `api/services/backtest/routes.py:233-306`

**Format**: Transformé depuis `BacktestPortfolioSeries` et `BacktestInstrumentSeries` pour correspondre au format frontend.

---

## 7. Exécution backtest (détails)

### Workflow complet (`api/services/backtest/executor.py:16-267`)

1. **Load instruments**: `load_instruments(db, instrument_ids)`
2. **Load price data**: `load_open_bars(db, instrument_ids, start_date, end_date)` depuis `market_data_bars_d1`
3. **Build calendar**: Toutes les dates disponibles, filtrées par `start_date`/`end_date`, weekend si `!allow_weekend_trading`
4. **Align prices**: Reindex sur calendar, forward fill
5. **Compute returns**: `returns_df = prices_df.pct_change().fillna(0)`
6. **Compute weights**: Selon `strategy_type` (equal_weight, momentum, bundle_strategy)
7. **Rebalance**: Selon `rebalance` frequency (daily/weekly/monthly)
8. **Compute portfolio returns**: `portfolio_returns = (weights_df.shift(1) * returns_df).sum(axis=1)`
9. **Apply costs**: Fees + slippage sur jours de rééquilibrage
10. **Compute NAV**: `nav_base100 = (1 + portfolio_returns).cumprod() * 100.0 / nav_series.iloc[0]`
11. **Compute metrics**: Total return, annualized return, volatility, Sharpe, max drawdown
12. **Store results**: `store_portfolio_series()`, `store_instrument_series()`, `store_metrics()`

**Référence**: `api/services/backtest/executor.py:16-267`

### Gestion des NaN

**Problème**: `NaN` et `inf` incompatibles avec JSON PostgreSQL.

**Solution**: Conversion en `None` (devient `null` en JSON) avant stockage.

**Référence**: `api/services/backtest/executor.py:191-196`, `api/services/backtest/repository.py:107-124`

---

## 8. Repository (`api/services/backtest/repository.py`)

### Fonctions exposées

**`load_instruments(db, instrument_ids)`**:
- Query `MarketDataInstrument` où `id IN (...)` ET `is_active == "true"`
- Retourne liste d'objets `MarketDataInstrument`

**`load_open_bars(db, instrument_ids, start_date, end_date)`**:
- Query `MarketDataBarD1` avec filtres
- Retourne `Dict[int, pd.DataFrame]` où DataFrame index = date, colonnes = OHLCV

**`update_backtest_run_status(db, run_id, status, error_message, effective_start_date, effective_end_date)`**:
- Met à jour `BacktestRun.status`, `error_message`, dates effectives

**`store_portfolio_series(db, run_id, series)`**:
- Delete existing, puis insert `BacktestPortfolioSeries`
- Conversion `NaN` → `None` pour JSON

**`store_instrument_series(db, run_id, series)`**:
- Delete existing, puis insert `BacktestInstrumentSeries`

**`store_metrics(db, run_id, metrics)`**:
- Delete existing, puis insert `BacktestMetrics` (portfolio + instruments)

**Référence**: `api/services/backtest/repository.py`

---

## 9. Limitations actuelles

- **Exécution asynchrone**: TODO dans `api/services/backtest/routes.py:151` (actuellement synchrone)
- **Skip rebalance si prix manquant**: UNKNOWN (forward fill utilisé, mais rebalance skippé ?)
- **Stratégies avancées**: Seulement `equal_weight`, `momentum`, `bundle_strategy` (pas de stratégies quantitatives avancées)


