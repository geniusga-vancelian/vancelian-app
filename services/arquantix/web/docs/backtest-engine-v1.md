# Backtest Engine V1

Documentation du moteur de backtest multi-assets avec convention D1 open-to-open.

## 📋 Vue d'ensemble

Le Backtest Engine permet de :
- Simuler des stratégies de trading multi-assets (equity, ETF, crypto)
- Utiliser des données historiques D1 (open-to-open) depuis Market Data
- Gérer les contraintes de tradabilité (weekend trading)
- Calculer des métriques de performance (CAGR, Sharpe, Max Drawdown, etc.)
- Visualiser les résultats avec des charts interactifs

## 🔧 Architecture

### Backend (`api/services/backtest/`)

**Structure** :
```
api/services/backtest/
├── __init__.py
├── schemas.py          # Pydantic models (requests/responses)
├── engine.py           # Moteur pur (fonctions pures, pas de DB)
├── repository.py       # Accès DB (load/store)
└── routes.py           # FastAPI router
```

**Source** : `api/services/backtest/`

### Frontend (`web/src/components/backtests/`)

**Structure** :
```
web/src/components/backtests/
├── types.ts            # TypeScript types
├── api.ts              # API helpers
├── BacktestBuilder.tsx # UI: formulaire de création
├── BacktestChart.tsx   # UI: charts recharts
├── BacktestStatsTable.tsx # UI: table de métriques
└── BacktestResults.tsx # UI: résultats complets
```

**Source** : `web/src/components/backtests/`

## 📊 Modèle de données

### Backtest Runs (`backtest_runs`)

Métadonnées d'un backtest :

- `id` : ID unique
- `name` : Nom optionnel
- `created_by_user_id` : Utilisateur créateur
- `start_date`, `end_date` : Période demandée
- `effective_start_date`, `effective_end_date` : Période réelle (intersection des données)
- `instrument_ids_json` : Liste des instruments (snapshot)
- `strategy_type` : "equal_weight" ou "momentum"
- `strategy_params_json` : Paramètres stratégie (ex: `{"lookback_days": 20}`)
- `rebalance` : "daily", "weekly", "monthly"
- `fees_bps`, `slippage_bps` : Coûts en basis points
- `allow_weekend_trading` : Booléen
- `status` : "PENDING", "SUCCESS", "FAILED"
- `error_message` : Message d'erreur si FAILED

**Source** : `api/database.py` lignes 231-254

### Portfolio Series (`backtest_portfolio_series`)

Série temporelle du portefeuille (quotidienne) :

- `run_id`, `date` : PK composite
- `nav_base100` : NAV normalisé à 100 au début
- `portfolio_return` : Rendement quotidien du portefeuille
- `drawdown` : Drawdown (négatif)
- `turnover` : Turnover (0.5 * sum(|w_new - w_old|))
- `costs` : Coûts totaux (fees + slippage)
- `weights_json` : Poids par instrument (JSON)
- `tradable_json` : Masque tradable (JSON)

**Source** : `api/database.py` lignes 257-275

### Instrument Series (`backtest_instrument_series`)

Série temporelle de chaque instrument (base100) :

- `run_id`, `instrument_id`, `date` : PK composite
- `base100` : Prix normalisé à 100 au début
- `instrument_return` : Rendement quotidien (optionnel)

**Source** : `api/database.py` lignes 278-290

### Metrics (`backtest_metrics`)

Métriques calculées :

- `run_id`, `scope`, `instrument_id`, `key` : PK composite
- `scope` : "portfolio" ou "instrument"
- `instrument_id` : NULL pour portfolio, ID pour instrument
- `key` : "cagr", "volatility", "sharpe", "calmar", "max_drawdown", "mean_daily_return", "variance_daily_return"
- `value` : Valeur numérique

**Source** : `api/database.py` lignes 293-305

## 🚀 Endpoints API

### Backend FastAPI

Tous les endpoints sont protégés par `Depends(get_current_user)` (JWT Bearer Token).

#### GET `/api/backtests/instruments`

Liste les instruments disponibles pour sélection.

**Query Parameters** :
- `is_active` (boolean, optional) : Filtrer par statut actif

**Response** :
```json
[
  {
    "id": 1,
    "symbol": "SPY",
    "name": "SPDR S&P 500 ETF",
    "asset_class": "etf",
    "weekend_tradable": false
  },
  ...
]
```

**Source** : `api/services/backtest/routes.py` lignes 48-82

#### POST `/api/backtests/run`

Lance un backtest synchronisé.

**Request** :
```json
{
  "name": "My Backtest",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "instrument_ids": [1, 2, 3],
  "strategy": {
    "type": "momentum",
    "params": {
      "lookback_days": 20
    }
  },
  "rebalance": "weekly",
  "fees_bps": 10.0,
  "slippage_bps": 5.0,
  "allow_weekend_trading": true
}
```

**Response** :
```json
{
  "run_id": 1,
  "status": "SUCCESS",
  "metrics": {
    "cagr": 0.15,
    "volatility": 0.12,
    "sharpe": 1.25,
    "max_drawdown": -0.08,
    "calmar": 1.875,
    "mean_daily_return": 0.0004,
    "variance_daily_return": 0.0001
  },
  "effective_start_date": "2024-01-02",
  "effective_end_date": "2024-12-30",
  "warnings": ["Effective date range adjusted due to data availability"]
}
```

**Note** : L'exécution est synchronisée (MVP). Pour de longs backtests, prévoir extension async plus tard.

**Source** : `api/services/backtest/routes.py` lignes 85-380

#### GET `/api/backtests/{run_id}`

Récupère les détails d'un backtest avec métriques comparatives.

**Response** :
```json
{
  "run_id": 1,
  "name": "My Backtest",
  "created_at": "2026-01-09T12:00:00Z",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "effective_start_date": "2024-01-02",
  "effective_end_date": "2024-12-30",
  "instrument_ids": [1, 2, 3],
  "strategy_type": "momentum",
  "strategy_params": {"lookback_days": 20},
  "rebalance": "weekly",
  "fees_bps": 10.0,
  "slippage_bps": 5.0,
  "allow_weekend_trading": true,
  "status": "SUCCESS",
  "metrics_portfolio": {
    "cagr": 0.15,
    "volatility": 0.12,
    "sharpe": 1.25,
    "calmar": 1.875,
    "max_drawdown": -0.08,
    "mean_daily_return": 0.0004,
    "variance_daily_return": 0.0001
  },
  "metrics_instruments": [
    {
      "instrument_id": 1,
      "symbol": "SPY",
      "cagr": 0.12,
      "volatility": 0.10,
      "sharpe": 1.20,
      ...
    },
    ...
  ]
}
```

**Source** : `api/services/backtest/routes.py` lignes 383-450

#### GET `/api/backtests/{run_id}/series`

Récupère les séries temporelles (portfolio + instruments).

**Response** :
```json
{
  "portfolio": [
    {
      "date": "2024-01-01T00:00:00Z",
      "nav_base100": 100.0,
      "portfolio_return": 0.0,
      "drawdown": 0.0,
      "turnover": 0.0,
      "costs": 0.0
    },
    ...
  ],
  "instruments": [
    {
      "instrument_id": 1,
      "symbol": "SPY",
      "series": [
        {
          "date": "2024-01-01T00:00:00Z",
          "base100": 100.0,
          "instrument_return": 0.0
        },
        ...
      ]
    },
    ...
  ],
  "weights": [
    {
      "date": "2024-01-01",
      "weights_json": {"1": 0.5, "2": 0.5},
      "tradable_json": {"1": true, "2": true}
    },
    ...
  ]
}
```

**Source** : `api/services/backtest/routes.py` lignes 453-520

### Frontend Next.js (Proxy Routes)

Toutes les routes proxy suivent le pattern :
1. Vérification session cookie (`getSessionFromCookie()`)
2. Création JWT depuis session
3. Proxy vers FastAPI avec `Authorization: Bearer <JWT>`

**Routes disponibles** :
- `GET /api/backtests/instruments` → Proxy vers `GET /api/backtests/instruments`
- `POST /api/backtests/run` → Proxy vers `POST /api/backtests/run`
- `GET /api/backtests/[run_id]` → Proxy vers `GET /api/backtests/{run_id}`
- `GET /api/backtests/[run_id]/series` → Proxy vers `GET /api/backtests/{run_id}/series`

**Source** : `web/src/app/api/backtests/`

## 🔄 Convention D1 "Open-to-Open"

**Définition** : Chaque bar D1 représente une journée de trading complète, de l'ouverture à la clôture.

**Prix utilisé** : `open` (prix d'ouverture)

**Rendement** : `return[t] = open[t] / open[t-1] - 1`

**Si open manquant** : Forward-fill du dernier open disponible. Si aucun open disponible, return = 0.

**Source** : `api/services/backtest/engine.py` lignes 40-50

## 📅 Calendrier & Tradabilité

### Calendrier

- **Calendrier** : Daily 7/7 (tous les jours, y compris weekends)
- **Index** : Chaque jour est un point de données

**Source** : `api/services/backtest/engine.py` lignes 12-17

### Weekend Tradability

**Règle** :
- Chaque instrument a `weekend_tradable` (booléen)
- **Weekend (samedi/dimanche)** :
  - Instruments `weekend_tradable=false` : **frozen** (weights inchangés)
  - Instruments `weekend_tradable=true` : **tradable** (peuvent être rebalancés)
- **Weekday** : Tous les instruments sont tradables

**Renormalisation** :
- Si des instruments sont frozen, leur poids est gelé
- Le budget restant (`1 - sum(frozen_weights)`) est redistribué sur les instruments tradables

**Exemple** :
- Portfolio: SPY (50%, weekend_tradable=false) + BTC (50%, weekend_tradable=true)
- Samedi : SPY frozen à 50%, BTC peut être rebalancé sur les 50% restants
- Si stratégie veut 60% BTC : BTC = 60% * 0.5 = 30% (sur budget 50%), SPY reste 50%, total = 80% → renormalisé à 62.5% SPY, 37.5% BTC

**Source** : `api/services/backtest/engine.py` lignes 120-200

## 🎯 Stratégies

### Equal Weight

**Type** : `"equal_weight"`

**Description** : Poids égal pour tous les instruments sélectionnés.

**Paramètres** : Aucun

**Formule** : `weight[i] = 1 / n` où `n` = nombre d'instruments

**Source** : `api/services/backtest/engine.py` lignes 60-70

### Momentum

**Type** : `"momentum"`

**Description** : Score basé sur rendement sur lookback period. Long-only (scores négatifs → 0).

**Paramètres** :
- `lookback_days` : Nombre de jours de lookback (1-252)

**Formule** :
- `score[i] = open[t] / open[t-lookback] - 1`
- Si `score[i] < 0` : `score[i] = 0` (long-only)
- `weight[i] = score[i] / sum(scores)` (normalisé)

**Source** : `api/services/backtest/engine.py` lignes 73-120

## 🔄 Rebalancing

**Fréquences** :
- `daily` : Rebalance chaque jour
- `weekly` : Rebalance chaque lundi (weekday 0)
- `monthly` : Rebalance le 1er de chaque mois

**Logique** :
- Si date est un jour de rebalance → calculer target weights selon stratégie
- Sinon → garder weights précédents (turnover = 0)

**Source** : `api/services/backtest/routes.py` lignes 33-46, 214-238

## 💰 Coûts

### Fees

**Formule** : `fees = (fees_bps / 10000) * turnover`

**Application** : Appliqué sur le turnover (pas sur la valeur totale)

### Slippage

**Formule** : `slippage = (slippage_bps / 10000) * turnover`

**Application** : Appliqué sur le turnover

### Turnover

**Formule** : `turnover = 0.5 * sum(|w_new[i] - w_old[i]|)` pour instruments tradables uniquement

**Note** : Le facteur 0.5 vient du fait qu'on compte chaque trade une fois (pas buy + sell séparément).

**Source** : `api/services/backtest/engine.py` lignes 200-220, `api/services/backtest/routes.py` lignes 245-248

## 📈 Métriques

### CAGR (Compound Annual Growth Rate)

**Formule** : `CAGR = (1 + total_return) ^ (365 / n_days) - 1`

**Annualisation** : 365 jours par défaut

**Source** : `api/services/backtest/engine.py` lignes 280-290

### Volatility (Annualisée)

**Formule** : `volatility = sqrt(variance_daily * 365)`

**Annualisation** : 365 jours

**Source** : `api/services/backtest/engine.py` lignes 292-295

### Sharpe Ratio

**Formule** : `sharpe = (mean_daily_return * sqrt(365)) / volatility`

**Risk-free rate** : 0 (MVP)

**Annualisation** : 365 jours

**Source** : `api/services/backtest/engine.py` lignes 297-301

### Max Drawdown

**Formule** :
- `running_max[t] = max(nav[0..t])`
- `drawdown[t] = (nav[t] - running_max[t]) / running_max[t]`
- `max_drawdown = min(drawdown)`

**Source** : `api/services/backtest/engine.py` lignes 270-275

### Calmar Ratio

**Formule** : `calmar = CAGR / |max_drawdown|`

**Source** : `api/services/backtest/engine.py` lignes 303-307

### Mean Daily Return

**Formule** : `mean = mean(returns)`

**Source** : `api/services/backtest/engine.py` lignes 292-293

### Variance Daily Return

**Formule** : `variance = var(returns)`

**Source** : `api/services/backtest/engine.py` lignes 293-294

## 🖥️ UI Admin

### Page : `/admin/backtests`

**Layout** : 2 colonnes (Builder gauche, Results droite)

**Composants** :
- `BacktestBuilder` : Formulaire de création
- `BacktestResults` : Affichage résultats avec tabs (Chart, Stats, Weights)

**Charts** :
- **Library** : Recharts (déjà installé)
- **Layout** : Single chart (default) ou Small multiples
- **Séries** : Portfolio (toujours) + Instruments (clickable show/hide)
- **Normalisation** : Toutes les séries en base100

**Source** : `web/src/app/admin/backtests/page.tsx`, `web/src/components/backtests/`

## ⚠️ Limitations & Warnings

### Données Manquantes

**Gestion** :
- Si certaines séries sont incomplètes, la période effective est tronquée à l'intersection
- Warning renvoyé dans la réponse : `"Effective date range: YYYY-MM-DD to YYYY-MM-DD"`

**Source** : `api/services/backtest/routes.py` lignes 160-170

### Rate Limits Alpha Vantage

Si les données Market Data ne sont pas disponibles (rate limit, etc.), le backtest échouera avec erreur claire.

**Solution** : S'assurer que les données sont backfillées avant de lancer le backtest.

### Exécution Synchronisée

**MVP** : Le backtest s'exécute de manière synchronisée (bloquant).

**Limitation** : Pour de très longs backtests (plusieurs années, nombreux instruments), le timeout HTTP peut être atteint.

**Extension future** : Prévoir jobs asynchrones (Celery/RQ) pour backtests longs.

**Source** : `api/services/backtest/routes.py` ligne 85

## 🔐 Sécurité

- **Auth** : Tous les endpoints protégés par JWT (`Depends(get_current_user)`)
- **Proxy** : Frontend utilise proxy Next.js (jamais appels directs depuis client)
- **Validation** : Pydantic (backend) + Zod (frontend)

**Source** : Pattern identique à Email Builder et Market Data

## 📝 Workflow Recommandé

### 1. Seed Market Data

```bash
# Via Market Data API
POST /api/market-data/instruments/seed
POST /api/market-data/instruments/{id}/backfill
```

### 2. Lancer Backtest

```bash
# Via Backtest API
POST /api/backtests/run
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "instrument_ids": [1, 2, 3],
  "strategy": {"type": "momentum", "params": {"lookback_days": 20}},
  "rebalance": "weekly"
}
```

### 3. Visualiser Résultats

```bash
# Via UI Admin
GET /admin/backtests
# → Charts, Stats, Weights
```

## 🐛 Troubleshooting

### "No price data found for selected instruments"

**Cause** : Instruments non backfillés

**Solution** : Backfill les instruments via Market Data API avant de lancer le backtest

### "No overlapping date range for instruments"

**Cause** : Les instruments n'ont pas de dates communes

**Solution** : Vérifier que les instruments ont des données sur la période demandée

### "Backtest failed: ..."

**Cause** : Erreur lors de l'exécution (données manquantes, calcul, etc.)

**Solution** : Vérifier les logs backend, s'assurer que les données sont complètes

## 📚 Références

- **Market Data Module** : `api/services/market_data/` (source de données)
- **Email Builder** : `api/services/ai_email/` (pattern de référence)
- **Audit Architecture** : `AUDIT_ARCHITECTURE_MARKET_DATA_BACKTEST.md`

---

**Dernière mise à jour** : 2026-01-09






