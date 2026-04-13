# ARQUANTIX — Vue d'ensemble

**Date**: 2026-01-10  
**Source**: Codebase analysé (`api/`, `web/`, `docs/`)  
**Statut**: Documentation canonique (basée uniquement sur le code existant)

---

## 1. Vision & objectifs

### À quoi sert Arquantix

Arquantix est une plateforme de **backtesting quantitatif** avec gestion de bundles d'actifs. Le projet permet de :

- **Gérer des instruments financiers** (crypto, ETF, forex, indices, commodities) avec données historiques D1
- **Créer des bundles** (portefeuilles d'instruments) avec allocations fixes ou dynamiques
- **Exécuter des backtests** sur des instruments individuels ou des bundles
- **Visualiser les performances** via graphiques (line chart, candlestick)

**Fichiers clés**:
- `api/main.py` - API principale FastAPI
- `api/database.py` - Modèles SQLAlchemy
- `web/src/app/admin/finance/page.tsx` - Page admin Finance

### Problèmes résolus

1. **Centralisation des données de marché**: Une seule source de vérité (`market_data_bars_d1`)
2. **Validation stricte des allocations**: Bundles = allocations figées (100% obligatoire)
3. **Backtests sur bundles**: Utilisation automatique des allocations définies (pas d'equal weight)

### Ce que le projet N'EST PAS

⚠️ **UNKNOWN (needs confirmation)**: Fonctionnalités futures non vérifiables dans le code actuel :
- Exécution live (trading réel)
- Strategies quantitatives avancées (seulement equal_weight, momentum, bundle_strategy)
- Backtests asynchrones (TODO dans `api/services/backtest/routes.py:151`)

---

## 2. Architecture globale

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    ARQUANTIX ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐
│   Frontend      │         │   Next.js       │         │   FastAPI    │
│   Next.js       │◄───────►│   API Routes    │◄───────►│   Backend    │
│   Admin Panel   │         │   (Proxy + JWT) │         │   (Python)   │
└─────────────────┘         └─────────────────┘         └──────┬───────┘
     │                                                          │
     │                                                          │
     │                                              ┌───────────▼──────────┐
     │                                              │   PostgreSQL         │
     │                                              │   arquantix_quant    │
     │                                              │                      │
     │                                              │  - market_data_*     │
     │                                              │  - bundles           │
     │                                              │  - backtest_*        │
     │                                              └──────────────────────┘
     │
     │  ┌─────────────────────────────────────────┐
     └─►│   Pages Admin:                           │
        │   - /admin/finance (Market Data/Bundles/ │
        │     Backtests)                           │
        │   - /admin/market-data                   │
        │   - /admin/bundles                       │
        │   - /admin/backtests                     │
        └──────────────────────────────────────────┘
```

### Rôle de chaque brique

**Frontend (Next.js)**:
- `web/src/app/admin/*` - Pages admin (React Server/Client Components)
- `web/src/components/finance/*` - Composants Finance (MarketDataTab, BundlesTab, BacktestsTab)
- `web/src/app/api/*` - Routes API Next.js (proxy vers FastAPI avec JWT)

**Backend (FastAPI)**:
- `api/main.py` - Application FastAPI, CORS, routers
- `api/services/*` - Modules par domaine (market_data, bundles, backtest)
- `api/database.py` - Modèles SQLAlchemy, session factory

**Base de données**:
- PostgreSQL (`arquantix_quant`)
- Tables principales: `market_data_instruments`, `market_data_bars_d1`, `bundles`, `bundle_components`, `backtest_runs`, etc.
- Schéma: `public`

**Docker**:
- Container `arquantix-db` (PostgreSQL sur port 5443)

### Flux de données

**1. Création d'un bundle**:
```
Frontend (BundlesTab.tsx)
  → POST /api/bundles (Next.js proxy)
  → Validation Zod (allocations: record<string, number>)
  → POST /api/bundles (FastAPI)
  → Validation Pydantic (BundleCreate)
  → Insert bundles + bundle_components
  → Return BundleResponse
```

**2. Exécution d'un backtest**:
```
Frontend (BacktestsTab.tsx)
  → POST /api/backtests/run
  → FastAPI: routes.py (create_backtest_run)
  → Load bundle allocations si bundle_id
  → executor.py (execute_backtest)
  → repository.py (load_open_bars depuis market_data_bars_d1)
  → Calcul weights (equal_weight/momentum/bundle_strategy)
  → Store results (portfolio_series, instrument_series, metrics)
```

**3. Affichage de données de marché**:
```
Frontend (MarketDataTab.tsx)
  → GET /api/market-data/instruments?is_active=true
  → GET /api/market-data/instruments/{id}/bars?start=...&end=...
  → FastAPI: routes.py
  → Query market_data_bars_d1
  → Return bars (open, high, low, close, volume)
```

---

## 3. Glossaire minimal

| Terme | Définition | Fichier de référence |
|-------|------------|---------------------|
| **Instrument** | Actif financier (BTC, ETH, QQQ, etc.) | `api/database.py:MarketDataInstrument` |
| **Bundle** | Portefeuille d'instruments avec allocations | `api/database.py:MarketDataBundle` |
| **Allocation** | Poids en pourcentage (0-100) d'un instrument dans un bundle | `api/database.py:BundleComponent.weight` |
| **Bar D1** | Donnée OHLCV quotidienne | `api/database.py:MarketDataBarD1` |
| **Backtest Run** | Exécution d'un backtest (status: PENDING/SUCCESS/FAILED) | `api/database.py:BacktestRun` |
| **Strategy Type** | Type de stratégie: `equal_weight`, `momentum`, `bundle_strategy` | `api/services/backtest/executor.py:93-144` |
| **Rebalance** | Fréquence de rééquilibrage: `daily`, `weekly`, `monthly` | `api/services/backtest/executor.py:146-157` |
| **Provider** | Source de données (actuellement: `yahoo`) | `api/services/market_data/yahoo_client.py` |
| **Asset Class** | Classe d'actif: `crypto`, `etf`, `forex`, `index`, `commodities` | `api/services/market_data/routes.py:19-27` |

---

## 4. Structure des répertoires

```
arquantix/
├── api/                          # Backend FastAPI
│   ├── services/                 # Modules par domaine
│   │   ├── market_data/          # Instruments, bars, Yahoo Finance
│   │   ├── bundles/              # CRUD bundles
│   │   ├── backtest/             # Backtest executor, routes, repository
│   │   └── diagnostics/          # Diagnostic endpoints
│   ├── alembic/versions/         # Migrations DB
│   ├── database.py               # Modèles SQLAlchemy
│   ├── main.py                   # FastAPI app
│   └── scripts/                  # Scripts utilitaires
├── web/                          # Frontend Next.js
│   ├── src/app/admin/            # Pages admin
│   │   ├── finance/page.tsx      # Page Finance (tabs)
│   │   ├── market-data/          # Page Market Data
│   │   ├── bundles/              # Page Bundles (deprecated, voir finance)
│   │   └── backtests/            # Page Backtests (deprecated, voir finance)
│   ├── src/components/finance/   # Composants Finance
│   │   ├── MarketDataTab.tsx     # Tab Market Data
│   │   ├── BundlesTab.tsx        # Tab Bundles
│   │   └── BacktestsTab.tsx      # Tab Backtests
│   └── src/app/api/              # Routes API Next.js (proxy)
├── docs/canonical/               # Documentation canonique
└── scripts/                      # Scripts de démarrage
    └── arquantix-start.sh        # Démarrage complet
```

---

## 5. Versions & dépendances clés

**Backend**:
- Python 3.9+
- FastAPI
- SQLAlchemy
- Alembic (migrations)
- pandas, numpy, yfinance
- `api/requirements.txt`

**Frontend**:
- Next.js 14+ (App Router)
- React 18+
- TypeScript
- shadcn/ui (composants)
- recharts, lightweight-charts (graphiques)
- `web/package.json`

**Base de données**:
- PostgreSQL (container Docker `arquantix-db`, port 5443)
- Schéma: `public`

---

## 6. Prochaines étapes de lecture

1. **[Frontend Next.js](10_FRONTEND_NEXTJS.md)** - Structure, pages, proxy API
2. **[Backend FastAPI](20_BACKEND_FASTAPI.md)** - Services, routes, schémas
3. **[Market Data](30_MARKET_DATA.md)** - Instruments, bars, ingestion Yahoo
4. **[Bundles](40_BUNDLES.md)** - Types, components, resolver
5. **[Backtests](50_BACKTESTS.md)** - Exécution, stratégies, résultats
6. **[Database](60_DATABASE_ALEMBIC.md)** - Tables, migrations, contraintes
7. **[Runbook Dev](70_RUNBOOK_DEV.md)** - Démarrage, debug, checklist


