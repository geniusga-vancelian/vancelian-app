# Market Data & Backtest Engine — Vue d'ensemble

## Objectif

Ce document fournit une vue d'ensemble fonctionnelle des modules **Market Data** et **Backtest Engine** du projet Arquantix. Ces modules permettent de :

1. **Collecter et stocker** des données de marché historiques (prix quotidiens)
2. **Simuler des stratégies d'investissement** sur des périodes passées
3. **Calculer des métriques de performance** (CAGR, Sharpe, Drawdown, etc.)

---

## Architecture globale

```
┌─────────────────┐
│ Alpha Vantage   │  Provider externe (API)
│   API           │
└────────┬────────┘
         │
         │ HTTP (rate-limited)
         │
┌────────▼─────────────────────────────────────┐
│  FastAPI Backend                              │
│  ┌─────────────────────────────────────────┐ │
│  │  Market Data Service                     │ │
│  │  - Client Alpha Vantage                  │ │
│  │  - Routes API                             │ │
│  │  - Repository (DB access)                 │ │
│  └─────────────────────────────────────────┘ │
│                                                │
│  ┌─────────────────────────────────────────┐ │
│  │  Backtest Engine                        │ │
│  │  - Engine (calculs purs)                │ │
│  │  - Routes API                            │ │
│  │  - Repository (DB access)                │ │
│  └─────────────────────────────────────────┘ │
└────────┬─────────────────────────────────────┘
         │
         │ SQLAlchemy
         │
┌────────▼────────┐
│  PostgreSQL     │  Base dédiée: arquantix_quant
│  arquantix_quant│
└────────┬────────┘
         │
         │ Next.js API Routes (proxy)
         │
┌────────▼─────────────────────────────────────┐
│  Next.js Frontend (Admin UI)                  │
│  - /admin/backtests                           │
│  - /admin/diagnostics                          │
└───────────────────────────────────────────────┘
```

---

## Différence entre Market Data et Backtest

### Market Data (Données brutes)

**Rôle** : Collecte, validation et stockage des données de marché.

- **Instruments** : Définition des actifs (BTC, ETH, QQQ, etc.)
- **Bars D1** : Prix quotidiens (open, high, low, close, volume)
- **Provider** : Alpha Vantage (API externe)
- **Backfill** : Remplissage historique manuel ou automatique

**Tables DB** :
- `market_data_instruments` : Liste des instruments
- `market_data_bars_d1` : Prix quotidiens par instrument

### Backtest Engine (Simulation)

**Rôle** : Simulation de stratégies d'investissement sur données historiques.

- **Stratégies** : `equal_weight`, `momentum`
- **Rebalancing** : `daily`, `weekly`, `monthly`
- **Métriques** : CAGR, Volatility, Sharpe, Max Drawdown, Calmar
- **Contraintes** : Weekend tradability, fees, slippage

**Tables DB** :
- `backtest_runs` : Exécution d'un backtest
- `backtest_portfolio_series` : Série temporelle du portefeuille (NAV, drawdown, turnover)
- `backtest_instrument_series` : Série temporelle par instrument (base100)
- `backtest_metrics` : Métriques calculées (portfolio + instruments)

---

## Flux de données

### 1. Initialisation (Seed)

```
Admin UI → POST /api/market-data/instruments/seed
         → Backend crée 7 instruments CORE_V1
         → DB: market_data_instruments (is_active=true)
```

**CORE_V1 Universe** (7 instruments) :
- **Crypto** : BTC, ETH, SOL (weekend_tradable=true)
- **ETFs** : URTH, QQQ, DIA, GLD (weekend_tradable=false)

### 2. Backfill Market Data

```
Admin UI → POST /api/market-data/backfill-missing
         → Backend appelle Alpha Vantage (séquentiel, rate-limited)
         → Parse JSON → Insert bars dans DB
         → DB: market_data_bars_d1
```

**Validation** :
- `POST /api/market-data/validate-provider` : Vérifie Alpha Vantage avant backfill
- Hard fail si 0 bars insérés après filtrage

### 3. Exécution Backtest

```
Admin UI → POST /api/backtests/run
         → Backend:
           1. Crée BacktestRun (status=PENDING)
           2. Charge instruments + bars D1
           3. Calcule calendrier (7/7)
           4. Aligne prix (forward-fill)
           5. Simule jour par jour:
              - Rebalance si nécessaire
              - Applique contraintes weekend
              - Calcule NAV, turnover, costs
           6. Calcule métriques finales
           7. Stocke séries + métriques
           8. Met à jour status=SUCCESS
         → DB: backtest_runs, backtest_portfolio_series, backtest_instrument_series, backtest_metrics
```

### 4. Visualisation

```
Admin UI → GET /api/backtests/{run_id}
         → GET /api/backtests/{run_id}/series
         → Frontend affiche:
            - Chart (NAV base100, benchmarks)
            - Stats (métriques)
            - Weights (debug)
```

---

## Rôles Backend vs Frontend

### Backend (FastAPI)

**Responsabilités** :
- Authentification (JWT via `get_current_user`)
- Appels Alpha Vantage (rate limiting)
- Calculs backtest (pandas, numpy)
- Persistance DB (SQLAlchemy)
- Validation (Pydantic)

**Endpoints principaux** :
- `/api/market-data/*` : Gestion instruments, backfill, validation
- `/api/backtests/*` : Exécution backtest, récupération résultats
- `/api/diagnostics/*` : Diagnostic système

### Frontend (Next.js)

**Responsabilités** :
- Proxy API (Next.js API routes)
- Authentification (session cookie → JWT)
- UI Admin (React, Tailwind, Recharts)
- Gestion d'état (useState, useEffect)

**Pages** :
- `/admin/backtests` : Builder + Results + Market Data panel
- `/admin/diagnostics` : Diagnostic checks

**Proxies** :
- `/api/market-data/*` → `buildBackendUrl()` + JWT
- `/api/backtests/*` → `buildBackendUrl()` + JWT
- `/api/diagnostics/*` → `buildBackendUrl()` + JWT

---

## Environnement

### Base de données dédiée

**Nom** : `arquantix_quant`

**Raison** : Séparation des données quantitatives (market data, backtest) de la base principale (admin_users, emails, etc.)

**Configuration** :
- `DATABASE_URL` dans `api/.env.local`
- Alembic migrations : `api/alembic/versions/`
- Pas de FK vers `admin_users` (quant DB isolée)

### Mode diagnostic

**Endpoint** : `POST /api/diagnostics/market-backtest/run`

**Checks** :
1. Router availability
2. Instruments exist (seed si nécessaire)
3. Bars existence
4. Quick backfill (120 jours, 1 crypto + 1 tradfi)
5. Backtest run minimal (BTC+SPY, equal_weight, weekly)
6. API/Proxy verification

**Mode** : `quick` (120 jours) ou `full` (configurable)

### Mode admin uniquement

**Sécurité** :
- Tous les endpoints protégés par `Depends(get_current_user)`
- Frontend : session cookie requis
- JWT signé avec `JWT_SECRET_KEY` (backend) = `AUTH_SECRET` (frontend)

---

## Conventions techniques

### Backend

- **Config** : `os.getenv()` (pas Pydantic Settings)
- **Module pattern** : `api/services/{module}/` (routes.py, schemas.py, client.py, config.py)
- **DB** : SQLAlchemy + Alembic
- **Auth** : JWT via `auth.py`

### Frontend

- **Proxy pattern** : Next.js API route → `buildBackendUrl()` → FastAPI
- **Auth** : `getSessionFromCookie()` → JWT signé → `Authorization: Bearer {token}`
- **UI** : Tailwind CSS, Recharts pour graphiques

### Données

- **Prix** : `Decimal` (précision financière)
- **Dates** : `date` (Python) / `YYYY-MM-DD` (API)
- **Calendrier** : 7/7 (tous les jours, pas seulement jours ouvrés)
- **Prix alignement** : Forward-fill (dernier prix connu)

---

## Limitations actuelles (MVP)

1. **Synchronisation** : Backtest exécuté de manière synchrone (pas de background jobs)
2. **Rate limiting** : Alpha Vantage free tier (4 calls/min)
3. **Universe** : 7 instruments CORE_V1 uniquement
4. **Stratégies** : `equal_weight`, `momentum` uniquement
5. **Rebalancing** : `daily`, `weekly`, `monthly` uniquement
6. **Provider** : Alpha Vantage uniquement (pas de multi-provider)

---

## Prochaines étapes possibles

1. Background jobs (Celery, RQ) pour backfill/backtest long
2. Multi-provider (Polygon, Yahoo Finance, etc.)
3. Stratégies avancées (mean-reversion, factor models)
4. Optimisation (recherche de paramètres)
5. Export résultats (CSV, PDF)

---

## Documents associés

- [Market Data Architecture](./MARKET_DATA_ARCHITECTURE.md)
- [Backtest Engine Architecture](./BACKTEST_ENGINE_ARCHITECTURE.md)
- [Database Schema](./DATABASE_SCHEMA_MARKET_BACKTEST.md)
- [Alpha Vantage Provider](./PROVIDERS_ALPHA_VANTAGE.md)
- [Frontend UI](./FRONTEND_BACKTEST_AND_MARKET_UI.md)
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)






