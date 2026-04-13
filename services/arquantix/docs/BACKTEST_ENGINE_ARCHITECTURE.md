# Backtest Engine Architecture

## Structure du module

```
api/services/backtest/
├── __init__.py
├── schemas.py         # Pydantic models (API)
├── repository.py      # DB access functions
├── engine.py          # Pure functions (calculs)
└── routes.py          # FastAPI endpoints
```

---

## Fichiers détaillés

### `schemas.py`

**Rôle** : Définition des modèles Pydantic pour validation API.

#### `StrategyConfig`
```python
class StrategyConfig(BaseModel):
    type: Literal["equal_weight", "momentum"]
    params: Optional[StrategyParams]  # lookback_days pour momentum
```

#### `BacktestCreateRequest`
```python
class BacktestCreateRequest(BaseModel):
    name: Optional[str]
    start_date: str  # YYYY-MM-DD
    end_date: str
    instrument_ids: List[int]  # 1-50 instruments
    initial_weights: Optional[Dict[int, float]]  # Optionnel, sinon equal-weight
    strategy: StrategyConfig
    rebalance: Literal["daily", "weekly", "monthly"]  # Default: "weekly"
    fees_bps: float  # 0-1000
    slippage_bps: float  # 0-1000
    allow_weekend_trading: bool  # Default: True
```

**Validations** :
- `end_date > start_date`
- `initial_weights` sum = 1.0 (si fourni)
- `momentum` strategy requiert `lookback_days`

#### `BacktestRunResponse`
```python
class BacktestRunResponse(BaseModel):
    run_id: int
    status: Literal["SUCCESS", "FAILED"]
    metrics: Optional[Dict[str, Any]]
    error_message: Optional[str]
    effective_start_date: Optional[str]  # Intersection dates disponibles
    effective_end_date: Optional[str]
    warnings: Optional[List[str]]
```

#### `BacktestDetailResponse`
Détails complets d'un backtest (run + métriques portfolio + instruments).

#### `SeriesResponse`
Séries temporelles (portfolio + instruments + weights).

---

### `repository.py`

**Rôle** : Accès DB pour backtest (SQLAlchemy).

#### `load_instruments(db, instrument_ids)`
Charge metadata instruments (id, symbol, name, asset_class, weekend_tradable).

#### `load_open_bars(db, instrument_ids, start_date, end_date)`
Charge prix OPEN pour instruments dans date range.

**Retour** : `Dict[int, pd.Series]` avec index=date, values=open prices.

**Usage** : Input pour `align_prices()`.

#### `create_backtest_run(...)`
Crée enregistrement `BacktestRun` dans DB.

**Champs importants** :
- `created_by_user_id` : `Optional[int]` (pas de FK, quant DB isolée)
- `created_by_email` : `Optional[str]` (pour traçabilité)
- `instrument_ids_json` : JSON array
- `strategy_params_json` : JSON object
- `status` : `"PENDING"` → `"SUCCESS"` ou `"FAILED"`

#### `store_portfolio_series(db, run_id, series)`
Stocke série temporelle portfolio (daily bars).

**Format** : `List[Dict]` avec :
- `date`
- `nav_base100`
- `portfolio_return`
- `drawdown`
- `turnover`
- `costs`
- `weights_json` : `Dict[instrument_id, weight]`
- `tradable_json` : `Dict[instrument_id, bool]`

#### `store_instrument_series(db, run_id, instrument_id, series)`
Stocke série temporelle par instrument (base100).

**Format** : `List[Dict]` avec :
- `date`
- `base100`
- `instrument_return` (optionnel)

#### `store_metrics(db, run_id, scope, instrument_id, metrics)`
Stocke métriques calculées.

**Scope** :
- `"portfolio"` : `instrument_id=None`
- `"instrument"` : `instrument_id=<id>`

**Format metrics** : `Dict[str, float]` (ex: `{"cagr": 0.15, "sharpe": 1.2}`)

**Note** : `instrument_id` nullable pour métriques portfolio (voir DB schema).

---

### `engine.py`

**Rôle** : Fonctions pures pour calculs backtest (pandas, numpy).

#### `build_calendar(start_date, end_date)`
**Retour** : `pd.DatetimeIndex` avec tous les jours (7/7, pas seulement jours ouvrés).

**Usage** : Calendrier de référence pour alignement prix.

#### `align_prices(instrument_price_series, calendar)`
**Rôle** : Aligne séries prix au calendrier (forward-fill).

**Input** : `Dict[int, pd.Series]` (instrument_id → série prix)

**Retour** : `pd.DataFrame` avec :
- Index : calendar dates
- Columns : instrument_ids
- Values : open prices (forward-filled)

**Forward-fill** : Si pas de prix pour un jour, utilise dernier prix connu.

#### `compute_returns(open_prices)`
**Rôle** : Calcule returns open-to-open.

**Retour** : `pd.DataFrame` avec même structure, `returns = prices.pct_change()`.

**Première ligne** : NaN (pas de return pour premier jour).

#### `compute_target_weights(...)`
**Rôle** : Calcule poids cibles selon stratégie.

**Stratégies** :

##### `equal_weight`
```python
weight = 1.0 / len(eligible_instruments)
return {inst_id: weight for inst_id in eligible_instruments}
```

##### `momentum`
```python
# Score = (price[t] / price[t-lookback]) - 1
# Long-only : scores négatifs → 0
# Normalise à sum=1
```

**Retour** : `Dict[int, float]` (instrument_id → weight).

#### `apply_tradability_constraints(...)`
**Rôle** : Applique contraintes weekend tradability.

**Logique** :
- **Weekday** : Applique target weights directement
- **Weekend** :
  - Instruments `weekend_tradable=false` : freeze poids précédent
  - Instruments `weekend_tradable=true` : redistribue budget restant

**Retour** : `(new_weights, turnover, tradable_mask)`

**Turnover** : `0.5 * sum(|w_new - w_old|)` pour instruments tradables uniquement.

#### `compute_nav(...)`
**Rôle** : Calcule NAV série à partir returns et costs.

**Formule** :
```
NAV[t] = NAV[t-1] * (1 + portfolio_return[t] - costs[t])
```

**Initial** : `NAV[0] = 100.0` (base100).

#### `compute_metrics(returns, nav, days_per_year=365)`
**Rôle** : Calcule métriques finales.

**Métriques** :

1. **Max Drawdown** :
   ```
   running_max = nav.expanding().max()
   drawdown = (nav - running_max) / running_max
   max_drawdown = drawdown.min()
   ```

2. **CAGR** (Compound Annual Growth Rate) :
   ```
   total_return = (nav[-1] / nav[0]) - 1
   cagr = (1 + total_return) ** (365 / n_days) - 1
   ```

3. **Volatility** (annualisée) :
   ```
   volatility = std(daily_returns) * sqrt(365)
   ```

4. **Sharpe** (rf=0, annualisé) :
   ```
   sharpe = (mean_return * sqrt(365)) / volatility
   ```

5. **Calmar** :
   ```
   calmar = cagr / abs(max_drawdown)
   ```

6. **Mean daily return** : `mean(returns)`

7. **Variance daily return** : `var(returns)`

**Retour** : `Dict[str, float]` avec toutes métriques.

---

### `routes.py`

**Rôle** : Endpoints FastAPI pour Backtest Engine.

**Router** : `APIRouter(prefix="/api/backtests", tags=["backtests"])`

**Protection** : Tous endpoints protégés par `Depends(get_current_user)`

#### Endpoints

##### `GET /api/backtests/instruments`
Liste instruments disponibles pour sélection backtest.

**Retour** : `List[InstrumentInfo]` (id, symbol, name, asset_class, weekend_tradable)

**Filtre** : `is_active=true` uniquement.

---

##### `POST /api/backtests/run`
**Rôle** : Exécute un backtest synchronement.

**Body** : `BacktestCreateRequest`

**Cycle complet** :

1. **Parse dates** : `start_date`, `end_date`

2. **Créer BacktestRun** :
   ```python
   run = create_backtest_run(
       name=request.name,
       start_date=start_date,
       end_date=end_date,
       instrument_ids=request.instrument_ids,
       strategy_type=request.strategy.type,  # Note: 'type' pas 'strategy_type'
       strategy_params=request.strategy.params.dict(),
       rebalance=request.rebalance,
       fees_bps=request.fees_bps,
       slippage_bps=request.slippage_bps,
       allow_weekend_trading=request.allow_weekend_trading,
       created_by_user_id=current_user.id,
       created_by_email=current_user.email,
   )
   ```

3. **Charger instruments** : `load_instruments(db, instrument_ids)`

4. **Charger prix** : `load_open_bars(db, instrument_ids, start_date, end_date)`

5. **Trouver effective date range** :
   - Intersection de toutes séries prix
   - `effective_start = max(min_dates)`
   - `effective_end = min(max_dates)`
   - Warning si différent de `start_date`/`end_date` demandés

6. **Mettre à jour run** : `run.effective_start_date`, `run.effective_end_date`

7. **Construire calendrier** : `build_calendar(effective_start, effective_end)`

8. **Aligner prix** : `align_prices(price_series, calendar)`

9. **Calculer returns** : `compute_returns(open_prices)`

10. **Initialiser weights** :
    - Si `initial_weights` fourni : utiliser
    - Sinon : equal-weight

11. **Simuler jour par jour** :
    ```python
    for current_date in calendar:
        # Rebalance check
        if should_rebalance(current_date, last_rebalance_date, rebalance):
            target_weights = compute_target_weights(...)
            new_weights, turnover, tradable_mask = apply_tradability_constraints(...)
            last_rebalance_date = current_date
        else:
            new_weights = prev_weights.copy()
            turnover = 0.0
        
        # Calculer costs
        fees = (fees_bps / 10000) * turnover
        slippage = (slippage_bps / 10000) * turnover
        costs = fees + slippage
        
        # Calculer portfolio return
        portfolio_return = sum(weight * return for weight, return in zip(weights, returns))
        
        # Stocker pour série
        weights_series.append(new_weights)
        turnover_series.append(turnover)
        costs_series.append(costs)
        portfolio_returns.append(portfolio_return)
        tradable_masks.append(tradable_mask)
        
        prev_weights = new_weights
    ```

12. **Calculer NAV** : `compute_nav(weights_series, returns, costs_series, portfolio_returns)`

13. **Calculer métriques** :
    - Portfolio : `compute_metrics(portfolio_returns, nav)`
    - Par instrument : `compute_metrics(instrument_returns, instrument_base100)`

14. **Stocker séries** :
    - `store_portfolio_series(db, run_id, portfolio_series)`
    - `store_instrument_series(db, run_id, instrument_id, instrument_series)` pour chaque instrument
    - `store_metrics(db, run_id, "portfolio", None, portfolio_metrics)`
    - `store_metrics(db, run_id, "instrument", instrument_id, instrument_metrics)` pour chaque instrument

15. **Mettre à jour status** : `update_backtest_run_status(db, run_id, "SUCCESS")`

16. **Retourner réponse** : `BacktestRunResponse(run_id, status, metrics, ...)`

**Gestion erreurs** :
- Si erreur → `update_backtest_run_status(db, run_id, "FAILED", error_message)`
- Retourne `BacktestRunResponse(status="FAILED", error_message=...)`

---

##### `GET /api/backtests/{run_id}`
**Rôle** : Détails complets d'un backtest.

**Retour** : `BacktestDetailResponse` avec :
- Run metadata (dates, strategy, rebalance, etc.)
- `metrics_portfolio` : `Dict[str, float]`
- `metrics_instruments` : `List[Dict]` (par instrument)

---

##### `GET /api/backtests/{run_id}/series`
**Rôle** : Séries temporelles (portfolio + instruments + weights).

**Retour** : `SeriesResponse` avec :
- `portfolio` : `List[PortfolioBar]` (date, nav_base100, return, drawdown, turnover, costs)
- `instruments` : `List[InstrumentSeries]` (par instrument : date, base100, return)
- `weights` : `List[Dict]` (date, weights_json, tradable_json)

---

## Cycle complet d'un backtest

```
1. Admin UI → POST /api/backtests/run
2. Backend crée BacktestRun (status=PENDING)
3. Charge instruments + bars D1
4. Trouve effective date range (intersection)
5. Construit calendrier (7/7)
6. Aligne prix (forward-fill)
7. Calcule returns (open-to-open)
8. Simule jour par jour:
   - Rebalance si nécessaire
   - Applique contraintes weekend
   - Calcule NAV, turnover, costs
9. Calcule métriques finales
10. Stocke séries + métriques
11. Met à jour status=SUCCESS
12. Retourne run_id
13. Admin UI → GET /api/backtests/{run_id}/series
14. Affiche chart + stats
```

---

## Stratégies supportées

### `equal_weight`
**Description** : Poids égal pour tous instruments.

**Poids** : `1.0 / n_instruments`

**Usage** : Baseline, benchmark.

---

### `momentum`
**Description** : Poids proportionnels à performance récente.

**Paramètres** :
- `lookback_days` : Période lookback (ex: 20, 60, 252)

**Calcul** :
1. Score par instrument : `(price[t] / price[t-lookback]) - 1`
2. Long-only : scores négatifs → 0
3. Normalise à sum=1

**Exemple** :
- BTC : +10% sur 20 jours → score = 0.10
- ETH : +5% sur 20 jours → score = 0.05
- QQQ : -2% sur 20 jours → score = 0 (long-only)
- Poids : BTC=0.67, ETH=0.33, QQQ=0.0

---

## Rebalancing

### `daily`
**Description** : Rebalance chaque jour.

**Usage** : Stratégies très actives.

---

### `weekly`
**Description** : Rebalance chaque lundi (weekday=0).

**Usage** : Stratégies modérées (default).

---

### `monthly`
**Description** : Rebalance premier jour du mois (day=1).

**Usage** : Stratégies passives.

---

## Contraintes Weekend Tradability

**Règle** : Instruments `weekend_tradable=false` ne peuvent pas être tradés le weekend.

**Implémentation** :
- **Weekday** : Applique target weights directement
- **Weekend** :
  - Instruments non-tradables : freeze poids précédent
  - Instruments tradables : redistribue budget restant

**Exemple** :
- Vendredi : BTC=0.5, QQQ=0.5
- Samedi (weekend) :
  - QQQ non-tradable → freeze QQQ=0.5
  - BTC tradable → BTC=0.5 (budget restant)
- Dimanche : même logique
- Lundi : Rebalance normal

---

## Calcul NAV

**Formule** :
```
NAV[t] = NAV[t-1] * (1 + portfolio_return[t] - costs[t])
```

**Initial** : `NAV[0] = 100.0` (base100)

**Portfolio return** :
```
portfolio_return[t] = sum(weight[i] * return[i][t] for i in instruments)
```

**Costs** :
```
fees = (fees_bps / 10000) * turnover
slippage = (slippage_bps / 10000) * turnover
costs = fees + slippage
```

**Turnover** :
```
turnover = 0.5 * sum(|w_new[i] - w_old[i]| for i in tradable_instruments)
```

---

## Métriques calculées

### Portfolio metrics

**Scope** : `scope="portfolio"`, `instrument_id=None`

**Métriques** :
- `cagr` : Compound Annual Growth Rate
- `volatility` : Volatilité annualisée
- `sharpe` : Ratio Sharpe (rf=0)
- `max_drawdown` : Drawdown maximum (négatif)
- `calmar` : Ratio Calmar (CAGR / |MaxDD|)
- `mean_daily_return` : Moyenne returns quotidiens
- `variance_daily_return` : Variance returns quotidiens

---

### Instrument metrics

**Scope** : `scope="instrument"`, `instrument_id=<id>`

**Métriques** : Mêmes que portfolio, calculées sur série base100 de l'instrument.

**Usage** : Comparaison performance instrument vs portfolio.

---

## Pourquoi `instrument_id` nullable dans `backtest_metrics` ?

**Raison** : Métriques portfolio n'ont pas d'instrument associé.

**Structure** :
- **Portfolio metrics** : `instrument_id=NULL`
- **Instrument metrics** : `instrument_id=<id>`

**Unique constraint** : `(run_id, scope, instrument_id, key)` permet `instrument_id=NULL` pour portfolio.

---

## Documents associés

- [Overview](./MARKET_DATA_AND_BACKTEST_OVERVIEW.md)
- [Database Schema](./DATABASE_SCHEMA_MARKET_BACKTEST.md)
- [Frontend UI](./FRONTEND_BACKTEST_AND_MARKET_UI.md)
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)






