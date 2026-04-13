# Architecture Arquantix - Documentation Technique et Fonctionnelle Exhaustive

**Version:** 2.0.0  
**Dernière mise à jour:** 2026-01-10  
**Source de vérité:** Ce document est LA référence absolue pour comprendre Arquantix.

---

## Table des Matières

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Architecture globale](#2-architecture-globale)
3. [Market Data — Concept fondamental](#3-market-data--concept-fondamental)
4. [Ingestion Yahoo Finance](#4-ingestion-yahoo-finance)
5. [Module centralisé des prix (bars_d1_repo)](#5-module-centralisé-des-prix-bars_d1_repo)
6. [Bundles — Concept clé](#6-bundles--concept-clé)
7. [Backtests](#7-backtests)
8. [Charts & Visualisation](#8-charts--visualisation)
9. [Frontend Admin (Next.js)](#9-frontend-admin-nextjs)
10. [Base de données](#10-base-de-données)
11. [Erreurs rencontrées & leçons apprises](#11-erreurs-rencontrées--leçons-apprises)
12. [Règles d'or du projet](#12-règles-dor-du-projet)
13. [Comment reprendre le projet après un arrêt](#13-comment-reprendre-le-projet-après-un-arrêt)
14. [Extensions futures prévues](#14-extensions-futures-prévues)

---

## 1. Vue d'ensemble du projet

### 1.1 Objectifs métier

**Arquantix** est une plateforme de backtesting quantitatif permettant de :

1. **Ingérer des données historiques de marché** via Yahoo Finance (méthode manuelle HTML)
2. **Créer des Bundles** (allocations fixes, composites, ou dynamiques) par Asset Class
3. **Exécuter des backtests** sur des portefeuilles avec différentes stratégies
4. **Visualiser les performances** via des graphiques interactifs
5. **Gérer du contenu CMS** (pages, articles, projets) intégré

### 1.2 Cas d'usage principaux

#### Cas d'usage 1 : Import initial de données
- Utilisateur va sur Yahoo Finance `BTC-USD` historique
- Copie la table HTML (5 ans de données)
- Colle dans `/admin/market-data`
- Le système parse, détecte les conflits, insère les données
- Résultat : Instrument `BTCUSD` disponible pour backtests

#### Cas d'usage 2 : Création d'un Bundle crypto 60/40
- Utilisateur crée Bundle "Crypto Core" (Asset Class: crypto)
- Ajoute BTCUSD (60%) et ETHUSD (40%)
- Sauvegarde (validation : somme = 100%)
- Bundle disponible pour backtests

#### Cas d'usage 3 : Backtest avec Bundle
- Utilisateur sélectionne Bundle "Crypto Core"
- Choisit période 2023-01-01 à 2024-01-01
- Rebalance : Weekly
- Le système :
  - Charge les poids cibles du Bundle (60/40)
  - À chaque rebalance, revient aux poids cibles
  - Entre rebalances, laisse dériver l'allocation
  - Calcule NAV base 100, drawdown, turnover, coûts
- Résultat : Performance du portefeuille avec rebalancing fixe

#### Cas d'usage 4 : Extension d'historique
- Instrument `BTCUSD` existe avec données 2020-2025
- Utilisateur importe nouvelle table HTML 2020-2026 (overlap + nouvelles dates)
- Système détecte overlap et conflits (smart update)
- Options : insert_delta_only, overwrite_overlap, overwrite_all_range
- Utilisateur choisit `insert_delta_only` → Ajoute uniquement les nouvelles dates

### 1.3 Philosophie du produit

#### Principe 1 : Reproductibilité absolue
- **Même entrées = Même sorties**, toujours
- Backtests déterministes (pas de random, pas de time-based seeds variables)
- Logique métier pure (fonctions pures quand possible)

#### Principe 2 : Contrôle total sur les données
- **Ingestion manuelle** (HTML copier-coller) : évite rate limits, contrôle total
- **Smart update** : détection de conflits, choix utilisateur
- **Pas de normalisation silencieuse** : utilisateur doit valider

#### Principe 3 : Séparation stricte des responsabilités
- **Frontend (Next.js)** : UI, proxy API, gestion de contenu CMS
- **Backend (FastAPI)** : Logique métier, validation, accès DB
- **Database (PostgreSQL)** : Persistance, contraintes d'intégrité

#### Principe 4 : Source unique de vérité
- **bars_d1_repo.py** : TOUT passe par lui pour les prix
- **Bundle weights** : source de vérité pour rebalancing fixe
- **Database** : état final (pas de cache incohérent)

### 1.4 Pourquoi ce système existe

**Problème résolu :**
- Besoin de backtester des stratégies quantitatives avec données historiques réelles
- Contraintes : Yahoo Finance rate limits, besoin de contrôle sur les données
- Solution : Ingestion manuelle + smart update + engine déterministe

**Valeur ajoutée :**
- **Bundles** : Permet de modéliser des allocations complexes (composites, dynamiques)
- **Smart update** : Évite les pertes de données accidentelles
- **Charts interactifs** : Visualisation claire des performances

---

## 2. Architecture globale

### 2.1 Vue macro Frontend / Backend / DB

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                       │
│  Port: 3000                                                 │
│  - Site vitrine (pages publiques)                          │
│  - Admin UI (/admin/*)                                      │
│    - Market Data Import (/admin/market-data)                │
│    - Bundle Builder (/admin/bundles)                        │
│    - Backtest Builder (/admin/backtests)                    │
│  - API Routes (proxies vers FastAPI)                       │
│    - /api/market-data/* → FastAPI /api/market-data/*        │
│    - /api/bundles/* → FastAPI /api/bundles/*                │
│    - /api/backtests/* → FastAPI /api/backtests/*            │
│  - CMS intégré (Prisma)                                     │
│    - Pages, articles, projets                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ HTTP + JWT Bearer Token
                        │ (via Next.js API Routes)
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   BACKEND (FastAPI)                         │
│  Port: 8000                                                 │
│  - REST API                                                 │
│  - Services métier:                                         │
│    - market_data/  (ingestion, instruments, bars)           │
│    - bundles/      (CRUD, resolver, preview)                │
│    - backtest/     (engine, routes, repository)             │
│  - Validation Pydantic                                      │
│  - Auth JWT                                                 │
│  - Database Access (SQLAlchemy)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ SQLAlchemy ORM
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                DATABASE (PostgreSQL)                        │
│  Container: arquantix-db                                    │
│  Port: 5443 (host) / 5432 (container)                       │
│                                                            │
│  Base: arquantix (API)                                      │
│  - market_data_instruments                                  │
│  - market_data_bars_d1                                      │
│  - bundles                                                  │
│  - bundle_components / bundle_allocations                   │
│  - bundle_dynamic_rules                                     │
│  - backtest_runs                                            │
│  - backtest_portfolio_series                                │
│  - backtest_instrument_series                               │
│  - backtest_metrics                                         │
│                                                            │
│  Base: arquantix_admin (Web/Prisma)                        │
│  - users, sessions                                          │
│  - pages, sections, section_contents                        │
│  - news, projects                                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Rôle de Next.js

**Responsabilités Frontend :**

1. **UI React** : Composants interactifs, formulaires, graphiques
2. **Pages Admin** : Routes `/admin/*` protégées par session
3. **API Proxy** : Routes `/api/*` qui forwardent vers FastAPI avec JWT
4. **CMS Content** : Gestion de pages/articles via Prisma
5. **State Management** : React hooks (useState, useEffect)
6. **Charts** : Recharts (line charts), TradingView Lightweight Charts (candlestick)

**Technologies :**
- Next.js 14.2.0 (App Router)
- React 18+
- Tailwind CSS + shadcn/ui (Radix UI)
- Recharts + TradingView Lightweight Charts
- Prisma 6.19.1 (pour CMS)

**Structure :**
```
web/src/
├── app/
│   ├── admin/              # Pages admin protégées
│   │   ├── market-data/
│   │   ├── bundles/
│   │   └── backtests/
│   ├── api/                # API Routes (proxies)
│   │   ├── market-data/
│   │   ├── bundles/
│   │   └── backtests/
│   └── (public)/            # Pages publiques
└── components/
    ├── backtests/          # Composants backtest
    ├── bundles/            # Composants bundle
    └── ui/                 # Composants UI (shadcn)
```

### 2.3 Rôle de FastAPI

**Responsabilités Backend :**

1. **REST API** : Endpoints `/api/*` avec validation Pydantic
2. **Business Logic** : Logique métier pure (engine, resolver, ingestion)
3. **Data Validation** : Schemas Pydantic stricts (discriminated unions)
4. **Database Access** : SQLAlchemy ORM avec sessions
5. **Auth** : JWT validation (Bearer token)
6. **Error Handling** : HTTPException avec messages clairs

**Technologies :**
- FastAPI 0.104+
- SQLAlchemy 2.0+
- Pydantic 2.0+ (discriminated unions)
- Python 3.9+
- pandas + numpy (calculs backtest)

**Structure :**
```
api/
├── main.py                 # FastAPI app, router mounting
├── database.py             # SQLAlchemy models, Base
├── auth.py                 # JWT auth, get_current_user
├── services/
│   ├── market_data/
│   │   ├── routes.py       # Endpoints ingestion, instruments
│   │   ├── schemas.py      # Pydantic models
│   │   ├── yahoo_html_parser.py  # HTML parsing
│   │   ├── ingest_service.py     # Smart update logic
│   │   └── bars_d1_repo.py       # Centralized price access
│   ├── bundles/
│   │   ├── routes.py       # CRUD bundles
│   │   ├── resolver.py     # Bundle resolution (fixed/composite/dynamic)
│   │   ├── preview.py      # Preview effective weights
│   │   └── schemas.py      # Pydantic models (discriminated unions)
│   └── backtest/
│       ├── routes.py       # Endpoints backtest
│       ├── engine.py       # Pure backtest logic
│       └── repository.py   # DB persistence
└── alembic/                # Migrations DB
```

### 2.4 Séparation des responsabilités

#### Frontend NE FAIT PAS :
- ❌ Validation métier complexe (juste validation UI de base)
- ❌ Calculs de backtest
- ❌ Résolution de bundles
- ❌ Accès direct à la DB API (toujours via FastAPI)

#### Backend NE FAIT PAS :
- ❌ Gestion de l'UI React
- ❌ Gestion de sessions cookies (c'est Next.js)
- ❌ CMS content management (c'est Prisma/Next.js)

#### Database NE FAIT PAS :
- ❌ Logique métier (uniquement contraintes d'intégrité)
- ❌ Validation applicative (uniquement contraintes DB)

### 2.5 Diagramme logique des flux

#### Flux 1 : Ingestion Market Data (HTML)

```
User (Yahoo Finance) 
  → Copie HTML table
  → Admin UI /admin/market-data
  → POST /api/market-data/yahoo/ingest-html-table
  → FastAPI:
     1. Parse HTML (yahoo_html_parser.py)
     2. Analyze conflicts (ingest_service.py)
     3. Return analysis (dry_run=true)
  → User choisit mode (insert_delta_only / overwrite_overlap / overwrite_all_range)
  → POST /api/market-data/yahoo/ingest-html-table (dry_run=false, mode=...)
  → FastAPI:
     1. Apply ingest (ingest_service.py)
     2. Upsert instrument (market_data_instruments)
     3. Upsert bars (market_data_bars_d1)
  → Response: {instrument, inserted_count, updated_count, chart_series}
  → UI: Affiche chart preview
```

#### Flux 2 : Backtest avec Bundle

```
User (Admin UI /admin/backtests)
  → Sélectionne Asset Class: "crypto"
  → Sélectionne Bundle: "Crypto Core"
  → Bundle Detail chargé:
     GET /api/bundles/{id}
     GET /api/bundles/{id}/preview?date=...
  → Affiche allocations cibles (60% BTCUSD, 40% ETHUSD)
  → Clique "Run Backtest"
  → POST /api/backtests/run
     {
       bundle_id: 1,
       start_date: "2023-01-01",
       end_date: "2024-01-01",
       rebalance: "weekly",
       fees_bps: 0,
       slippage_bps: 0,
       allow_weekend_trading: true
     }
  → FastAPI:
     1. Load bundle (bundles.resolver.resolve_bundle_effective_weights)
     2. Get instrument IDs from bundle
     3. Load prices (bars_d1_repo.get_bars_d1)
     4. Build calendar (daily 7/7)
     5. Run backtest loop (engine.py):
        - À chaque rebalance date:
          a. Load target weights from bundle (fixed)
          b. Check missing prices → skip if needed
          c. Apply tradability constraints (weekend)
          d. Rebalance to target weights (open-to-open)
          e. Calculate NAV, turnover, costs
        - Entre rebalances: drift naturel
     5. Persist results (backtest_runs, backtest_portfolio_series, backtest_metrics)
  → Response: {run_id, status: "SUCCESS"}
  → UI: Redirect to /admin/backtests → Affiche BacktestResults component
```

---

## 3. Market Data — Concept fondamental

### 3.1 Asset Classes

**Liste exhaustive :**

1. **CRYPTO** : Cryptomonnaies (BTCUSD, ETHUSD, SOLUSD, etc.)
   - Weekend tradable : **true** (par défaut)
   - Exemples : BTCUSD, ETHUSD, SOLUSD
   - Format instrument_code : Normalisé sans séparateurs (BTCUSD, pas BTC-USD)

2. **ETF** : Exchange-Traded Funds (URTH, QQQ, DIA, GLD, etc.)
   - Weekend tradable : **false** (par défaut)
   - Exemples : URTH (MSCI World), QQQ (Nasdaq), DIA (Dow Jones), GLD (Gold)

3. **INDEX** : Indices (MSCI World, NASDAQ 100, etc.)
   - Weekend tradable : **false** (par défaut)
   - Exemples : MSCIWORLD, NASDAQ100

4. **COMMODITIES** : Matières premières (GOLD, SILVER, etc.)
   - Weekend tradable : **false** (par défaut)
   - Exemples : GOLD, SILVER
   - Note : Anciennement "METAL", renommé en "COMMODITIES"

5. **FOREX** : Paires de devises (EURUSD, USDJPY, GBPUSD, etc.)
   - Weekend tradable : **false** (par défaut)
   - Format instrument_code : Normalisé sans séparateurs (EURUSD, pas EUR-USD ou EURUSD=X)
   - Format provider_symbol : Yahoo format (EURUSD=X, EUR-USD)
   - Exemples : EURUSD, USDJPY, GBPUSD

**Règles propres à chaque classe :**

#### Weekend Trading

**CRYPTO** :
- `weekend_tradable = "true"` par défaut
- Rebalancing possible le samedi/dimanche
- Pas de freeze des positions le weekend

**ETF, INDEX, COMMODITIES, FOREX** :
- `weekend_tradable = "false"` par défaut
- Rebalancing bloqué le weekend (sauf si `allow_weekend_trading=true` dans backtest)
- Positions freeze le weekend si `allow_weekend_trading=false`

**Impact sur backtests :**
- Si `allow_weekend_trading=false` et date = weekend et instrument `weekend_tradable="false"` :
  - Instrument non tradable → freeze poids précédents
  - Turnover calculé uniquement sur instruments tradables

### 3.2 Instruments

#### Définition

Un **Instrument** est une représentation d'un actif financier dans Arquantix :
- Un instrument = une ligne dans `market_data_instruments`
- Un instrument peut avoir plusieurs bars (dans `market_data_bars_d1`)
- Un instrument appartient à UN asset class
- Un instrument a UN provider (`"yahoo"` uniquement actuellement)

#### Champs DB (market_data_instruments)

```sql
CREATE TABLE market_data_instruments (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,        -- Code interne (ex: "BTCUSD")
    name VARCHAR(200),                         -- Nom optionnel
    asset_class VARCHAR(20) NOT NULL,          -- "crypto", "etf", "index", "commodities", "forex"
    weekend_tradable VARCHAR(10) NOT NULL,     -- "true" ou "false" (STRING!)
    provider VARCHAR(50) NOT NULL,             -- "yahoo" (uniquement)
    provider_symbol VARCHAR(50),               -- Symbole Yahoo (ex: "BTC-USD", "EURUSD=X")
    is_active VARCHAR(10) NOT NULL,            -- "true" ou "false" (STRING!)
    archived_at TIMESTAMP NULL,                -- Date d'archivage (soft delete)
    created_at TIMESTAMP NOT NULL
);
```

#### instrument_code vs provider_symbol

**`symbol` (instrument_code interne) :**
- Code normalisé utilisé dans Arquantix
- Format : Pas de séparateurs, uppercase (ex: `BTCUSD`, `EURUSD`)
- Unique : Contrainte UNIQUE en DB
- Utilisé dans : Backtests, Bundles, Charts

**`provider_symbol` :**
- Symbole Yahoo Finance original
- Format : Peut contenir séparateurs (ex: `BTC-USD`, `EURUSD=X`)
- Optionnel : Peut être NULL (défaut = `symbol`)
- Utilisé uniquement pour : Référence Yahoo Finance

**Exemples :**

| Instrument | symbol (interne) | provider_symbol (Yahoo) | asset_class |
|------------|------------------|-------------------------|-------------|
| Bitcoin | BTCUSD | BTC-USD | crypto |
| Ethereum | ETHUSD | ETH-USD | crypto |
| Euro/USD | EURUSD | EURUSD=X | forex |
| Gold ETF | GLD | GLD | etf |

#### Normalisation des tickers

**Règle générale :**
- Supprimer tous les séparateurs (`-`, `=`, `X`)
- Convertir en uppercase
- Exemples :
  - `BTC-USD` → `BTCUSD`
  - `EURUSD=X` → `EURUSD`
  - `EUR-USD` → `EURUSD`

**Cas spéciaux FOREX :**
- Format Yahoo : `EURUSD=X` ou `EUR-USD`
- Normalisé : `EURUSD`
- Si `provider_symbol` non fourni, défaut = `{symbol}=X` (Yahoo format)

**Pourquoi normaliser ?**
- Cohérence : même format pour tous les instruments
- Recherche : plus facile de trouver `BTCUSD` que `BTC-USD`
- URLs : pas de caractères spéciaux dans les codes

#### Cas Forex (EURUSD, USDJPY)

**Particularités :**
1. **Format interne** : `EURUSD` (pas de séparateur)
2. **Format Yahoo** : `EURUSD=X` ou `EUR-USD`
3. **Normalisation automatique** :
   - Input : `EURUSD=X` → symbol: `EURUSD`, provider_symbol: `EURUSD=X`
   - Input : `EUR-USD` → symbol: `EURUSD`, provider_symbol: `EURUSD=X` (défaut)

**Auto-détection :**
- Si ticker se termine par `=X` → FOREX
- Si ticker format `XXX-YYY` (7 chars avec `-`) et alpha uniquement → FOREX
- Exemple : `EURUSD=X`, `EUR-USD` → asset_class = `FOREX`

### 3.3 Table market_data_bars_d1

#### Rôle

La table `market_data_bars_d1` est **LA source de vérité** pour tous les prix historiques dans Arquantix :
- Utilisée par : Backtests, Charts, Preview, Performance
- Format : D1 (daily bars) uniquement
- Convention : Open-to-Open (rebalancing au prix d'ouverture)

#### Structure

```sql
CREATE TABLE market_data_bars_d1 (
    instrument_id INTEGER NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume BIGINT NOT NULL,
    source VARCHAR(50) NOT NULL,              -- "yahoo" (uniquement)
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (instrument_id, date),
    UNIQUE (instrument_id, date),
    FOREIGN KEY (instrument_id) REFERENCES market_data_instruments(id)
);
```

#### Clé primaire

**Clé primaire composite :** `(instrument_id, date)`

**Implications :**
- Un instrument ne peut avoir qu'UN seul bar par date
- Upsert : Si bar existe → UPDATE, sinon → INSERT
- Pas de doublons possibles (contrainte UNIQUE)

#### Champs critiques

**`open`, `high`, `low`, `close` :**
- Type : `NUMERIC(20, 8)` (précision 8 décimales)
- Unité : Prix dans la devise de base (USD pour la plupart)
- Utilisation : `open` pour rebalancing, `close` pour calculs de performance

**`volume` :**
- Type : `BIGINT` (entier)
- Unité : Nombre d'unités échangées
- Utilisation : Affichage charts, filtrage (optionnel)

**`source` :**
- Valeur : `"yahoo"` uniquement (pour l'instant)
- Rôle : Traçabilité (savoir d'où viennent les données)
- Filtrage : Utilisé dans `bars_d1_repo` pour garantir cohérence

**⚠️ IMPORTANT : Pas de `adj_close`**
- `adj_close` est parsé depuis Yahoo HTML mais **NON stocké** en DB
- Raison : Réduction de complexité, `close` suffit pour la plupart des cas
- Si besoin futur : Ajouter colonne via migration Alembic

#### Source de vérité

**Tous les accès aux prix passent par `bars_d1_repo.py` :**
- `get_bars_d1()` : Liste de bars
- `get_ohlc_matrix()` : Dict[instrument_id][date] = {open, high, low, close, volume}
- `get_close_matrix()` : Dict[instrument_id][date] = close_price
- `get_price_dataframe()` : DataFrame pandas pour resolver/preview

**Pourquoi centraliser ?**
- DRY : Pas de duplication de logique de chargement
- Cohérence : Même format de données pour tous les usages
- Performance : Un seul point d'optimisation (indexes, queries)

#### Pourquoi D1 uniquement (pour l'instant)

**Raisons :**
1. **Simplicité** : Un seul timeframe à gérer
2. **Cas d'usage** : Backtests de stratégies long-terme (weekly/monthly rebalance)
3. **Yahoo Finance** : Données D1 facilement accessibles via HTML
4. **Performance** : Moins de données = requêtes plus rapides

**Extensions futures :**
- H1, H4 : Possible via nouvelle table `market_data_bars_h1`, `market_data_bars_h4`
- M15, M30 : Possible mais nécessite autre source de données (Yahoo ne fournit pas)

---

## 4. Ingestion Yahoo Finance

### 4.1 Pourquoi Yahoo

**Avantages :**
1. **Gratuit** : Pas d'API key requise (pour HTML)
2. **Couverture large** : Crypto, ETF, Indices, Commodities, Forex
3. **Historique long** : Données remontant à plusieurs décennies
4. **Stable** : Format HTML relativement stable
5. **Accessible** : Pas de rate limits stricts (HTML copier-coller)

**Alternatives rejetées :**
- **Alpha Vantage** : Déprécié (rate limits, clés API, couverture limitée)
- **APIs payantes** (Bloomberg, Refinitiv) : Coût prohibitif
- **Scraping automatique** : Fragile (changes de HTML, rate limits, blocage)

### 4.2 Méthodes supportées

#### Méthode 1 : HTML Table (MÉTHODE CANONIQUE)

**Statut :** ✅ Méthode principale, recommandée

**Processus :**
1. User va sur `https://finance.yahoo.com/quote/{TICKER}/history`
2. Sélectionne période (1M, 3M, 1Y, 5Y, MAX, ou custom)
3. Copie le tableau HTML (sélectionner tout le `<table>`)
4. Colle dans Admin UI `/admin/market-data` → Section "Import via HTML Table"
5. Remplit :
   - Instrument Code (ex: `BTCUSD`)
   - Asset Class (ex: `CRYPTO`)
   - Provider Symbol (optionnel, ex: `BTC-USD`)
6. Clique "Validate" → Système analyse (dry_run)
7. Si conflits → Choisit mode (insert_delta_only, overwrite_overlap, overwrite_all_range)
8. Clique action → Système applique (dry_run=false)

**Avantages :**
- Contrôle total : User choisit exactement quelles données importer
- Pas de rate limits : Copier-coller = pas d'appels API
- Reproductibilité : Même table HTML = même résultat
- Smart update : Détection de conflits avant import

#### Méthode 2 : CSV (Fallback)

**Statut :** ✅ Disponible, mais moins utilisée

**Processus :**
1. User télécharge CSV depuis Yahoo Finance (bouton "Download")
2. Upload fichier CSV dans Admin UI
3. Système parse CSV (colonnes : Date, Open, High, Low, Close, Adj Close, Volume)
4. Upsert direct (pas de smart update pour CSV)

**Limitations :**
- Pas de smart update (pas de détection de conflits)
- Format CSV peut varier (selon région Yahoo)
- Moins de contrôle que HTML

#### Méthode 3 : URL (Legacy)

**Statut :** ⚠️ Legacy, déprécié (mais fonctionnel)

**Processus :**
1. User paste URL Yahoo Finance history (ex: `https://finance.yahoo.com/quote/BTC-USD/history?period1=...&period2=...`)
2. Système extrait `ticker`, `period1`, `period2`
3. Tente téléchargement CSV ou JSON chart
4. Parse et upsert

**Limitations :**
- Rate limits possibles (appels API Yahoo)
- Blocage possible (User-Agent, cookies)
- Moins fiable que HTML copier-coller

**Recommandation :** Utiliser HTML Table de préférence.

### 4.3 Ingestion HTML (méthode canonique)

#### Copy/paste depuis Yahoo

**Format attendu :**
```html
<table class="W(100%) M(0)">
  <thead>
    <tr>
      <th>Date</th>
      <th>Open</th>
      <th>High</th>
      <th>Low</th>
      <th>Close</th>
      <th>Adj Close</th>
      <th>Volume</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Jan 8, 2026</td>
      <td>189.11</td>
      <td>190.45</td>
      <td>188.90</td>
      <td>189.95</td>
      <td>189.95</td>
      <td>172,073,400</td>
    </tr>
    <!-- ... plus de lignes ... -->
  </tbody>
</table>
```

**Actions utilisateur :**
1. Aller sur Yahoo Finance
2. Cliquer droit sur le tableau → "Inspecter"
3. Sélectionner l'élément `<table>`
4. Copier HTML (Ctrl+C / Cmd+C)
5. Coller dans textarea Admin UI

**⚠️ IMPORTANT :**
- Copier TOUT le tableau (pas juste les données)
- Inclure `<table>` et `</table>`
- Inclure `<thead>` et `<tbody>`

#### Parsing HTML

**Module :** `api/services/market_data/yahoo_html_parser.py`

**Fonction principale :** `parse_yahoo_html_table(html: str) -> Tuple[List[ParsedBar], List[ParsedEvent], List[SkippedRow]]`

**Algorithme :**

```python
def parse_yahoo_html_table(html: str):
    # 1. Parse HTML avec BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # 2. Trouve le premier <table>
    table = soup.find('table')
    if not table:
        raise ValueError("No <table> element found")
    
    # 3. Itère les lignes <tr> dans <tbody>
    tbody = table.find('tbody')
    if not tbody:
        raise ValueError("No <tbody> element found")
    
    bars = []
    events = []
    skipped = []
    
    for row_idx, tr in enumerate(tbody.find_all('tr')):
        cells = tr.find_all('td')
        
        # 4. Détecte type de ligne
        if len(cells) == 2:  # Ligne événement (dividend, split)
            # Format: <td>Date</td><td colspan="6">0.01 Dividend</td>
            event_type, event_value = parse_event_row(cells)
            events.append(ParsedEvent(date, event_type, event_value))
            skipped.append(SkippedRow(row_idx, raw, reason="Event row"))
            continue
        
        if len(cells) != 7:  # Ligne invalide
            skipped.append(SkippedRow(row_idx, raw, reason="Invalid column count"))
            continue
        
        # 5. Parse les 7 colonnes
        try:
            date_str = cells[0].get_text().strip()
            date = parse_date(date_str)  # "Jan 8, 2026" → date(2026, 1, 8)
            
            open_str = cells[1].get_text().strip()
            open_price = Decimal(open_str.replace(',', ''))
            
            high_str = cells[2].get_text().strip()
            high_price = Decimal(high_str.replace(',', ''))
            
            low_str = cells[3].get_text().strip()
            low_price = Decimal(low_str.replace(',', ''))
            
            close_str = cells[4].get_text().strip()
            close_price = Decimal(close_str.replace(',', ''))
            
            adj_close_str = cells[5].get_text().strip()
            adj_close = Decimal(adj_close_str.replace(',', ''))  # Parsé mais non stocké
            
            volume_str = cells[6].get_text().strip()
            volume = int(volume_str.replace(',', ''))
            
            # 6. Validation
            if not date or not close_price:
                skipped.append(SkippedRow(row_idx, raw, reason="Missing required fields"))
                continue
            
            # Fallback: high/low = close si manquant
            if not high_price:
                high_price = close_price
            if not low_price:
                low_price = close_price
            
            bars.append(ParsedBar(date, open_price, high_price, low_price, close_price, volume))
            
        except (ValueError, AttributeError) as e:
            skipped.append(SkippedRow(row_idx, raw, reason=f"Parse error: {e}"))
            continue
    
    return bars, events, skipped
```

#### Validation des colonnes

**Colonnes requises :**
1. **Date** : Obligatoire, format "Jan 8, 2026" ou ISO "2026-01-08"
2. **Close** : Obligatoire, numeric
3. **Open** : Obligatoire, numeric
4. **High** : Optionnel (fallback = close si manquant)
5. **Low** : Optionnel (fallback = close si manquant)
6. **Adj Close** : Optionnel (parsé mais non stocké)
7. **Volume** : Obligatoire, integer (peut être 0)

**Règles de validation :**
- Date invalide → Skip row, ajouter à `skipped`
- Prix manquant (sauf high/low) → Skip row
- Prix négatif → Skip row (ou warning ?)
- Volume négatif → Skip row

#### Mapping OHLCV

**Mapping direct :**
- HTML `Open` → DB `open` (NUMERIC)
- HTML `High` → DB `high` (NUMERIC, fallback = close)
- HTML `Low` → DB `low` (NUMERIC, fallback = close)
- HTML `Close` → DB `close` (NUMERIC)
- HTML `Volume` → DB `volume` (BIGINT, remove commas)
- HTML `Adj Close` → **PAS stocké** (ignoré)

**Normalisation :**
- Supprimer virgules dans nombres : `"172,073,400"` → `172073400`
- Convertir en Decimal pour OHLC (précision)
- Convertir en int pour Volume

### 4.4 Smart Update (CRITIQUE)

**Module :** `api/services/market_data/ingest_service.py`

#### dry_run

**Comportement par défaut :** `dry_run=true`

**Phase 1 : Analyse (dry_run=true)**
```
POST /api/market-data/yahoo/ingest-html-table
{
  "html": "<table>...</table>",
  "instrument_code": "BTCUSD",
  "asset_class": "CRYPTO",
  "dry_run": true  // Par défaut
}
```

**Réponse :**
```json
{
  "status": "ok" | "conflict",
  "instrument": {...},
  "rows_parsed": 1500,
  "rows_skipped": 0,
  "analysis": {
    "incoming_count": 1500,
    "incoming_range": {"min": "2020-01-01", "max": "2025-01-10"},
    "existing_count": 1200,
    "existing_range": {"min": "2020-01-01", "max": "2024-12-31"},
    "overlap_count": 1200,
    "mismatch_count": 0,  // 0 = pas de conflit
    "delta_count": 300,   // Nouvelles dates
    "has_conflict": false
  },
  "actions_available": ["insert_delta_only"]
}
```

**Si conflit détecté (`has_conflict=true`) :**
```json
{
  "status": "conflict",
  "analysis": {
    "mismatch_count": 5,
    "mismatches": [
      {"date": "2024-12-31", "field": "close", "existing": 189.50, "incoming": 189.95}
    ],
    "has_conflict": true
  },
  "actions_available": ["insert_delta_only", "overwrite_overlap", "overwrite_all_range"]
}
```

**Phase 2 : Application (dry_run=false, mode requis)**

Si `has_conflict=false` et utilisateur clique "Apply Delta" :
```
POST /api/market-data/yahoo/ingest-html-table
{
  "dry_run": false,
  "mode": "insert_delta_only"  // Auto-sélectionné si pas de conflit
}
```

Si `has_conflict=true` et utilisateur choisit action :
```
POST /api/market-data/yahoo/ingest-html-table
{
  "dry_run": false,
  "mode": "overwrite_overlap"  // Choix utilisateur
}
```

#### overlap detection

**Algorithme :**

```python
def analyze_ingest_conflicts(db, instrument_id, incoming_bars):
    # 1. Charger bars existants dans la plage de dates entrantes
    min_date = min(bar.date for bar in incoming_bars)
    max_date = max(bar.date for bar in incoming_bars)
    
    existing_bars = db.query(MarketDataBarD1).filter(
        and_(
            MarketDataBarD1.instrument_id == instrument_id,
            MarketDataBarD1.date >= min_date,
            MarketDataBarD1.date <= max_date
        )
    ).all()
    
    # 2. Construire dicts date -> bar
    existing_dict = {bar.date: bar for bar in existing_bars}
    incoming_dict = {bar.date: bar for bar in incoming_bars}
    
    # 3. Trouver overlap (dates communes)
    overlap_dates = set(existing_dict.keys()) & set(incoming_dict.keys())
    
    # 4. Comparer valeurs sur overlap
    mismatches = []
    for date in overlap_dates:
        existing = existing_dict[date]
        incoming = incoming_dict[date]
        
        if existing.open != incoming.open:  # Comparaison quantize
            mismatches.append(ConflictMismatch(date, "open", existing.open, incoming.open))
        # ... idem pour high, low, close, volume
    
    return IngestAnalysis(
        overlap_count=len(overlap_dates),
        mismatch_count=len(mismatches),
        has_conflict=(len(mismatches) > 0)
    )
```

#### delta only

**Mode :** `insert_delta_only`

**Comportement :**
- Insère uniquement les dates qui n'existent pas déjà
- **Ne modifie PAS** les dates existantes (même si valeurs différentes)
- Idempotent : Peut être appelé plusieurs fois sans effet

**Algorithme :**
```python
def apply_ingest(db, instrument_id, incoming_bars, mode="insert_delta_only"):
    if mode == "insert_delta_only":
        for bar in incoming_bars:
            existing = db.query(MarketDataBarD1).filter(
                and_(
                    MarketDataBarD1.instrument_id == instrument_id,
                    MarketDataBarD1.date == bar.date
                )
            ).first()
            
            if not existing:  # Date n'existe pas
                new_bar = MarketDataBarD1(...)
                db.add(new_bar)
        
        db.commit()
        return {"inserted_count": X, "updated_count": 0}
```

**Cas d'usage :**
- Extension d'historique (2020-2025 → 2020-2026)
- Import initial (pas d'overlap)
- Mise à jour incrémentale mensuelle

#### overwrite overlap

**Mode :** `overwrite_overlap`

**Comportement :**
- **UPDATE** les dates existantes avec nouvelles valeurs
- **INSERT** les dates manquantes
- Mode "upsert intelligent" : Écrasement contrôlé

**Algorithme :**
```python
def apply_ingest(db, instrument_id, incoming_bars, mode="overwrite_overlap"):
    if mode == "overwrite_overlap":
        for bar in incoming_bars:
            existing = db.query(MarketDataBarD1).filter(...).first()
            
            if existing:  # Date existe → UPDATE
                existing.open = bar.open
                existing.high = bar.high
                existing.low = bar.low
                existing.close = bar.close
                existing.volume = bar.volume
                updated_count += 1
            else:  # Date n'existe pas → INSERT
                new_bar = MarketDataBarD1(...)
                db.add(new_bar)
                inserted_count += 1
        
        db.commit()
        return {"inserted_count": X, "updated_count": Y}
```

**Cas d'usage :**
- Correction de données (valeurs Yahoo corrigées)
- Remplacement de données erronées
- Mise à jour avec source plus fiable

#### overwrite full range

**Mode :** `overwrite_all_range`

**Comportement :**
- **DELETE** tous les bars existants dans la plage de dates entrantes
- **INSERT** tous les bars entrants (remplacement complet)
- **⚠️ DESTRUCTIF** : Perte de données en dehors de la plage

**Algorithme :**
```python
def apply_ingest(db, instrument_id, incoming_bars, mode="overwrite_all_range"):
    if mode == "overwrite_all_range":
        # 1. DELETE tous les bars dans la plage
        deleted = db.query(MarketDataBarD1).filter(
            and_(
                MarketDataBarD1.instrument_id == instrument_id,
                MarketDataBarD1.date >= min_date,
                MarketDataBarD1.date <= max_date
            )
        ).delete()
        
        # 2. INSERT tous les bars entrants
        for bar in incoming_bars:
            new_bar = MarketDataBarD1(...)
            db.add(new_bar)
        
        db.commit()
        return {"inserted_count": X, "deleted_count": Y}
```

**⚠️ AVERTISSEMENT :**
- Ce mode **supprime** toutes les données dans la plage, même celles non présentes dans les données entrantes
- Exemple : Si données existantes 2020-2026, et données entrantes 2023-2024, alors données 2025-2026 seront **supprimées**
- Utiliser uniquement si **certain** que les données entrantes couvrent toute la plage

**Cas d'usage :**
- Remplacement complet de source de données
- Correction massive de plage spécifique
- Migration vers nouveau format

#### Règles de cohérence des prix

**Précision de comparaison :**

```python
DECIMAL_PRECISION = Decimal('0.000001')  # 6 décimales

def quantize_decimal(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)
```

**Règles :**
- **OHLC** : Comparaison avec `quantize` à 6 décimales
  - Exemple : `189.500000` vs `189.500001` → **identique** (différence < 1e-6)
  - Exemple : `189.500000` vs `189.500010` → **différent** (différence >= 1e-6)
- **Volume** : Comparaison exacte (int, pas de tolérance)
  - Exemple : `172073400` vs `172073401` → **différent**

**Pourquoi cette précision ?**
- Évite faux positifs dus aux arrondis float
- Permet détecter vraies différences de prix
- Balance entre précision et tolérance aux arrondis

#### Gestion des conflits

**Workflow utilisateur :**

1. **User paste HTML** → Clic "Validate"
2. **Backend analyse** (dry_run=true) → Retourne analyse
3. **UI affiche :**
   - Si `has_conflict=false` : "OK, X nouvelles dates" + Bouton "Apply Delta"
   - Si `has_conflict=true` : "X conflits détectés" + Liste mismatches + 3 boutons :
     - "Add Delta Only" (insert_delta_only)
     - "Overwrite Overlap" (overwrite_overlap)
     - "Overwrite All Range" (overwrite_all_range) [⚠️ avec warning]
4. **User choisit action** → Clic bouton
5. **Backend applique** (dry_run=false, mode=X) → Retourne résultats
6. **UI affiche :** "X rows inserted, Y rows updated"

**Règles de décision :**

- **Si pas de conflit** : `insert_delta_only` automatique (safe)
- **Si conflit mineur (< 5 mismatches)** : Proposer `overwrite_overlap` (correction probable)
- **Si conflit majeur (> 50 mismatches)** : Avertir utilisateur, demander confirmation explicite
- **Mode destructif** : Toujours demander confirmation explicite

### 4.5 Erreurs possibles & gestion

#### 409 Conflict

**Quand :** Smart update détecte des conflits (`has_conflict=true`)

**Réponse :**
```json
{
  "status": "conflict",
  "status_code": 409,
  "analysis": {
    "mismatch_count": 5,
    "mismatches": [...]
  }
}
```

**Action utilisateur :** Choisir mode de résolution (insert_delta_only, overwrite_overlap, overwrite_all_range)

#### 422 Unprocessable Entity

**Quand :** Validation Pydantic échoue (champs manquants, types invalides)

**Réponse :**
```json
{
  "detail": [
    {
      "loc": ["body", "instrument_code"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Action développeur :** Vérifier schéma Pydantic, corriger payload frontend

**Action utilisateur :** Vérifier formulaire, remplir tous les champs requis

#### Données insuffisantes

**Quand :** HTML parse retourne 0 bars valides

**Réponse :**
```json
{
  "status": "error",
  "detail": "No valid bars found in HTML table"
}
```

**Causes possibles :**
- Table HTML invalide (pas de `<table>` ou `<tbody>`)
- Format de date non reconnu
- Toutes les lignes skipées (parsing errors)

**Action :** Vérifier HTML collé, réessayer avec table complète

#### Incohérences de prix

**Quand :** Prix manquants ou négatifs après parsing

**Comportement :**
- Ligne skipée → Ajoutée à `skipped` array avec raison
- Continuation du parsing (pas d'arrêt)
- Retour dans réponse : `{"rows_skipped": X, "skipped": [...]}`

**Exemples de raisons :**
- `"Missing required fields"` : Date ou close manquant
- `"Parse error: invalid date format"` : Date non parsable
- `"Invalid column count"` : Ligne événement (dividend/split)

**Action utilisateur :** Vérifier `skipped` array dans réponse, corriger HTML si nécessaire

---

## 5. Module centralisé des prix (bars_d1_repo)

### 5.1 Pourquoi il existe

**Problème résolu :**
- Avant : Code dupliqué pour charger les prix dans preview, backtest, charts
- Après : **Une seule source de vérité** pour tous les accès aux prix

**Avantages DRY (Don't Repeat Yourself) :**
1. **Cohérence** : Même format de données partout
2. **Maintenance** : Un seul endroit à modifier si schéma change
3. **Performance** : Optimisations centralisées (indexes, queries)
4. **Tests** : Tests unitaires plus faciles (une seule fonction à mocker)

### 5.2 Fonctions exposées

**Module :** `api/services/market_data/bars_d1_repo.py`

#### `get_bars_d1(db, instrument_ids, start_date, end_date) -> List[MarketDataBarD1]`

**Rôle :** Récupère les bars D1 bruts depuis la DB

**Utilisation :** Charts, export, validation

**Exemple :**
```python
bars = get_bars_d1(db, [1, 2], date(2023, 1, 1), date(2024, 1, 1))
# Retourne : [MarketDataBarD1(...), ...]
```

#### `get_ohlc_matrix(db, instrument_ids, start_date, end_date) -> Dict[int, Dict[date, Dict[str, float]]]`

**Rôle :** Matrice OHLCV pour calculs backtest

**Format :**
```python
{
  instrument_id: {
    date: {
      'open': 189.11,
      'high': 190.45,
      'low': 188.90,
      'close': 189.95,
      'volume': 172073400
    }
  }
}
```

**Utilisation :** Backtest engine, bundle preview (dynamic)

#### `get_close_matrix(db, instrument_ids, start_date, end_date) -> Dict[int, Dict[date, float]]`

**Rôle :** Matrice de prix de clôture uniquement

**Format :**
```python
{
  instrument_id: {
    date: 189.95  # close price
  }
}
```

**Utilisation :** Performance calculations, simple charts

#### `get_price_dataframe(db, instrument_ids, start_date, end_date) -> pd.DataFrame`

**Rôle :** DataFrame pandas pour resolver/preview

**Format :**
```
   date       instrument_id  open    high    low     close   volume
0  2023-01-01  1             189.11  190.45  188.90  189.95  172073400
1  2023-01-02  1             189.95  191.20  189.50  190.80  165432100
```

**Utilisation :** Bundle resolver (dynamic), preview effective weights

#### `get_available_date_range(db, instrument_ids) -> Dict[int, Tuple[Optional[date], Optional[date]]]`

**Rôle :** Plage de dates disponible pour chaque instrument

**Retourne :** `{instrument_id: (min_date, max_date)}`

**Utilisation :** Validation coverage, UI affichage range

#### `check_data_coverage(db, instrument_ids, start_date, end_date, min_coverage_pct=0.95) -> Tuple[bool, List[str]]`

**Rôle :** Vérifie si la couverture de données est suffisante

**Retourne :** `(is_sufficient, warnings_list)`

**Utilisation :** Pre-validation avant backtest

### 5.3 Pourquoi TOUT passe par lui

**Règle stricte :**
- ❌ **NE JAMAIS** accéder directement à `MarketDataBarD1` en dehors de `bars_d1_repo`
- ✅ **TOUJOURS** utiliser les fonctions de `bars_d1_repo`

**Exceptions (justifiées) :**
- `ingest_service.py` : Upsert direct (nécessaire pour l'insertion)
- Tests unitaires : Mocker les fonctions de `bars_d1_repo`

**Bénéfices :**
- **Source unique** : Un seul point de modification
- **Cohérence** : Même logique de filtrage (source="yahoo", is_active)
- **Performance** : Queries optimisées, indexes utilisés

### 5.4 Preview / Backtest / Charts = même source

**Avant (duplication) :**
```python
# Preview
bars = db.query(MarketDataBarD1).filter(...).all()

# Backtest
bars = db.query(MarketDataBarD1).filter(...).all()

# Charts
bars = db.query(MarketDataBarD1).filter(...).all()
```

**Après (centralisé) :**
```python
# Preview
bars = get_bars_d1(db, instrument_ids, start_date, end_date)

# Backtest
bars = get_bars_d1(db, instrument_ids, start_date, end_date)

# Charts
bars = get_bars_d1(db, instrument_ids, start_date, end_date)
```

**Résultat :** Si besoin de modifier le filtrage (ex: ajouter filtre `source="yahoo"`), un seul endroit à modifier.

---

## 6. Bundles — Concept clé

### 6.1 Définition

Un **Bundle** est une allocation cible définie pour un Asset Class :
- Un Bundle = un ensemble d'instruments (ou d'autres bundles) avec poids cibles (0-100%)
- Les poids doivent sommer à 100% (validation stricte)
- Un Bundle appartient à UN asset class
- Les instruments d'un Bundle doivent appartenir au même asset class que le Bundle

**Utilisation :**
- Backtests : Utiliser un Bundle force `rebalance_mode="fixed_target_weights"`
- Preview : Afficher les poids effectifs (résolus)
- Charts : Visualiser la performance d'un Bundle

### 6.2 Types de Bundles

#### Type 1 : fixed_instruments (Défaut)

**Définition :** Bundle avec instruments directs et poids fixes

**Exemple :**
```
Bundle: "Crypto Core"
  - BTCUSD: 60%
  - ETHUSD: 40%
```

**Comportement :**
- Poids fixes, jamais recalculés
- Source de vérité : `bundle_components` table
- Résolution : Directe (pas de calcul)

**Table DB :** `bundle_components` avec `component_type='instrument'`

#### Type 2 : composite_fixed

**Définition :** Bundle contenant d'autres bundles (composés)

**Exemple :**
```
Bundle: "All Crypto"
  - Bundle "Crypto Core" (60%)  → résolu en: BTCUSD 36%, ETHUSD 24%
  - Bundle "Crypto Alt" (40%)   → résolu en: SOLUSD 40%
Final effective: BTCUSD 36%, ETHUSD 24%, SOLUSD 40%
```

**Comportement :**
- Résolution récursive : Résoudre chaque child bundle, puis multiplier poids
- Détection de cycles : A→B→A rejeté avec erreur claire
- Validation finale : Somme effective = 100%

**Table DB :** `bundle_components` avec `component_type='bundle'` et `child_bundle_id`

**Résolution :**
```python
def resolve_bundle_to_instrument_weights(bundle_id):
    # 1. Load components
    # 2. Pour chaque component:
    #    - Si instrument: poids direct
    #    - Si bundle: résoudre récursivement, multiplier poids
    # 3. Normaliser (somme = 1.0)
    # 4. Valider (somme ≈ 100% avec tolérance)
    return {instrument_id: weight}
```

#### Type 3 : dynamic

**Définition :** Bundle dont les poids sont calculés dynamiquement à chaque rebalance via un DSL (Domain Specific Language)

**Exemple :**
```json
{
  "type": "weights",
  "items": [
    {
      "instrument_code": "BTCUSD",
      "expr": {
        "op": "normalize_to_one",
        "values": [
          {"op": "sma", "instrument_code": "BTCUSD", "field": "close", "window": 20}
        ]
      }
    }
  ]
}
```

**Comportement :**
- Poids recalculés à chaque rebalance date
- Nécessite prix historiques (lookback)
- Règles JSON DSL (pas d'exécution Python arbitraire)
- Validation : Poids doivent sommer à 1.0 après `normalize_to_one`

**Table DB :** `bundle_dynamic_rules` avec `rule_json` (JSON)

**Résolution :**
```python
def resolve_dynamic_bundle_weights(bundle_id, as_of_date, price_matrix):
    # 1. Load rule JSON
    # 2. Pour chaque item:
    #    - Évaluer expression DSL
    #    - Appliquer normalize_to_one si requis
    # 3. Retourner {instrument_id: weight}
    return {instrument_id: weight}
```

### 6.3 Bundle Components

**Table unifiée :** `bundle_components`

**Champs :**
- `bundle_id` : FK vers `bundles.id`
- `component_type` : `'instrument'` ou `'bundle'`
- `instrument_id` : FK vers `market_data_instruments.id` (si `component_type='instrument'`)
- `child_bundle_id` : FK vers `bundles.id` (si `component_type='bundle'`)
- `weight` : NUMERIC(10, 4) (pourcentage 0-100)
- `position_order` : INTEGER (optionnel, pour ordre d'affichage)

**Contraintes :**
- XOR : `instrument_id IS NOT NULL XOR child_bundle_id IS NOT NULL`
- Unique : `(bundle_id, component_type, instrument_id, child_bundle_id)` (contrainte DB)
- Validation Pydantic : Discriminated union (voir section 11)

**Exemples :**

**Fixed instruments :**
```
bundle_id=1, component_type='instrument', instrument_id=1, weight=60.0
bundle_id=1, component_type='instrument', instrument_id=2, weight=40.0
```

**Composite :**
```
bundle_id=2, component_type='bundle', child_bundle_id=1, weight=60.0
bundle_id=2, component_type='instrument', instrument_id=3, weight=40.0
```

### 6.4 Pondérations

**Validation des poids :**

**Règle stricte :** Somme des poids = 100.0 (tolérance 0.01%)

**Validation backend (Pydantic) :**
```python
@field_validator('components')
def validate_weights_sum(cls, v):
    total = sum(float(item.weight) for item in v)
    if abs(total - 100.0) > 0.01:
        raise ValueError(f"Component weights must sum to 100.0 (current: {total:.4f})")
    return v
```

**Validation frontend :**
- Live validation : Affiche total en temps réel
- Bouton "Normalize" : Normalise automatiquement (mais doit être cliqué explicitement)
- Disable submit : Si somme != 100%, bouton désactivé

**Pas de normalisation automatique :**
- ❌ Backend ne normalise pas automatiquement (utilisateur doit corriger)
- ✅ Frontend peut proposer normalisation (mais explicite)

### 6.5 Bundles dynamiques (DSL)

#### JSON Rules

**Structure :**
```json
{
  "type": "weights",
  "items": [
    {
      "instrument_code": "BTCUSD",
      "expr": {
        "op": "normalize_to_one",
        "values": [
          {"op": "sma", "instrument_code": "BTCUSD", "field": "close", "window": 20}
        ]
      }
    },
    {
      "instrument_code": "ETHUSD",
      "expr": {
        "op": "normalize_to_one",
        "values": [
          {"op": "sma", "instrument_code": "ETHUSD", "field": "close", "window": 20}
        ]
      }
    }
  ]
}
```

**Opérations supportées :**

1. **`const`** : Valeur constante
   ```json
   {"op": "const", "value": 0.5}
   ```

2. **`price`** : Prix historique
   ```json
   {"op": "price", "instrument_code": "BTCUSD", "field": "close", "lag": 0}
   ```

3. **`returns`** : Rendements sur fenêtre
   ```json
   {"op": "returns", "instrument_code": "BTCUSD", "window": 20}
   ```

4. **`sma`** : Simple Moving Average
   ```json
   {"op": "sma", "instrument_code": "BTCUSD", "field": "close", "window": 20}
   ```

5. **`ratio`** : Ratio entre deux valeurs
   ```json
   {"op": "ratio", "a": {...}, "b": {...}}
   ```

6. **`add`, `sub`, `mul`, `div`** : Opérations arithmétiques
   ```json
   {"op": "add", "a": {...}, "b": {...}}
   ```

7. **`clip`** : Limiter entre min et max
   ```json
   {"op": "clip", "value": {...}, "min": 0, "max": 1}
   ```

8. **`if`** : Condition
   ```json
   {"op": "if", "cond": {...}, "then": {...}, "else": {...}}
   ```

9. **`normalize_to_one`** : Normaliser pour sommer à 1.0 (OBLIGATOIRE pour weights)
   ```json
   {"op": "normalize_to_one", "values": [...]}
   ```

#### Exemples

**Exemple 1 : Momentum simple (SMA ratio)**
```json
{
  "type": "weights",
  "items": [
    {
      "instrument_code": "BTCUSD",
      "expr": {
        "op": "normalize_to_one",
        "values": [
          {
            "op": "ratio",
            "a": {"op": "price", "instrument_code": "BTCUSD", "field": "close", "lag": 0},
            "b": {"op": "sma", "instrument_code": "BTCUSD", "field": "close", "window": 20}
          }
        ]
      }
    }
  ]
}
```
→ Poids proportionnel au ratio prix actuel / SMA 20

**Exemple 2 : Returns-based (rendements sur 20 jours)**
```json
{
  "type": "weights",
  "items": [
    {
      "instrument_code": "BTCUSD",
      "expr": {
        "op": "normalize_to_one",
        "values": [
          {"op": "returns", "instrument_code": "BTCUSD", "window": 20}
        ]
      }
    }
  ]
}
```
→ Poids proportionnel aux rendements 20 jours

#### Lookback inference

**Module :** `api/services/bundles/dsl_analyzer.py`

**Fonction :** `infer_dynamic_requirements(rule_json) -> (lookback_days, uses_prices)`

**Algorithme :**
- Parse récursif de l'arbre d'expression
- Détecte opérations nécessitant prix (`sma`, `price`, `returns`)
- Calcule `max_window` (fenêtre maximale nécessaire)
- Retourne `lookback_days = max_window + 10` (buffer)

**Utilisation :**
- Preview : Charge les prix nécessaires (pas plus, pas moins)
- Backtest : Valide que les données sont disponibles

#### Règles sans prix

**Possible :** Bundles dynamiques avec poids constants (pas de prix nécessaires)

**Exemple :**
```json
{
  "type": "weights",
  "items": [
    {
      "instrument_code": "BTCUSD",
      "expr": {"op": "const", "value": 0.6}
    },
    {
      "instrument_code": "ETHUSD",
      "expr": {"op": "const", "value": 0.4}
    }
  ]
}
```

**Note :** Si tous les poids sont `const`, le bundle équivaut à `fixed_instruments` (mais peut être converti dynamiquement plus tard).

#### Détection des cycles

**Algorithme (DFS avec visited set) :**

```python
def resolve_bundle_to_instrument_weights(bundle_id, visited=None):
    if visited is None:
        visited = set()
    
    if bundle_id in visited:
        raise BundleCycleError(f"Cycle detected: bundle {bundle_id} referenced recursively")
    
    visited.add(bundle_id)
    
    # ... résolution récursive ...
    
    return weights
```

**Exemple de cycle :**
- Bundle A contient Bundle B (60%)
- Bundle B contient Bundle A (40%)
- → **REJETÉ** avec erreur claire

### 6.6 Resolver

**Module :** `api/services/bundles/resolver.py`

#### `resolve_bundle_effective_weights(bundle_id, date, price_matrix) -> Dict[int, float]`

**Rôle :** Orchestrateur principal qui résout un bundle en poids effectifs d'instruments

**Algorithme :**
```python
def resolve_bundle_effective_weights(bundle_id, date, price_matrix):
    # 1. Load bundle
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    
    # 2. Selon type:
    if bundle.type == 'fixed_instruments':
        return resolve_bundle_to_instrument_weights(bundle_id)  # Poids fixes
    
    elif bundle.type == 'composite_fixed':
        return resolve_bundle_to_instrument_weights(bundle_id)  # Résolution récursive
    
    elif bundle.type == 'dynamic':
        return resolve_dynamic_bundle_weights(bundle_id, date, price_matrix)  # DSL evaluation
    
    else:
        raise ValueError(f"Unknown bundle type: {bundle.type}")
```

**Ordre d'exécution :**
1. **Load bundle** depuis DB
2. **Selon type** : Appeler la fonction de résolution appropriée
3. **Validation finale** : Somme des poids ≈ 1.0 (tolérance 0.01)
4. **Retour** : `{instrument_id: weight}` (0.0 à 1.0)

#### Source de vérité

**Pour fixed/composite :**
- Source : Table `bundle_components`
- Résolution : Directe ou récursive
- Poids : Jamais recalculés (fixes)

**Pour dynamic :**
- Source : Table `bundle_dynamic_rules.rule_json`
- Résolution : Évaluation DSL à la date demandée
- Poids : Recalculés à chaque appel (date peut changer)

**Validation finale :**
- Tous les types : Somme des poids effectifs ≈ 1.0
- Si non validé → `BundleWeightValidationError`

#### Validation finale

**Règle :** Après résolution, les poids doivent sommer à 1.0 (tolérance 0.01)

**Algorithme :**
```python
total = sum(weights.values())
if abs(total - 1.0) > 0.01:
    raise BundleWeightValidationError(f"Weights sum to {total} (expected 1.0)")
```

**Normalisation (si nécessaire) :**
- Si total > 0 : Normaliser `weight / total` pour chaque poids
- Si total = 0 : Erreur (pas de poids valides)

**Note :** La normalisation n'est appliquée qu'après résolution complète, pas pendant.

---

## 7. Backtests

### 7.1 Philosophie

#### Reproductibilité

**Principe absolu :** Même entrées = Même sorties, toujours.

**Garanties :**
- Pas de random : Pas de générateur aléatoire, pas de time-based seeds variables
- Pas de dépendances externes variables : Prix chargés depuis DB (source fixe)
- Ordre déterministe : Rebalances dans l'ordre chronologique strict
- Calculs purs : Fonctions pures quand possible (pas de side effects)

**Pourquoi c'est critique :**
- Comparaison de stratégies : Doit pouvoir reproduire exactement les mêmes résultats
- Debugging : Même problème = même résultat (pas de flou dû au hasard)
- Audit : Traçabilité complète (chaque calcul peut être rejoué)

#### Déterminisme

**Algorithme déterministe :**
```python
def run_backtest(start_date, end_date, instruments, strategy, rebalance_freq):
    # 1. Build calendar (daily, 7/7)
    calendar = build_calendar(start_date, end_date)  # Déterministe
    
    # 2. Load prices (from DB, source fixe)
    prices = get_ohlc_matrix(db, instrument_ids, start_date, end_date)  # Déterministe
    
    # 3. Compute returns (open-to-open)
    returns = compute_returns(prices)  # Déterministe
    
    # 4. Run loop (daily)
    for date in calendar:
        # Compute target weights (déterministe selon strategy)
        target_weights = compute_target_weights(date, strategy, prices, returns)
        
        # Apply tradability constraints (déterministe selon weekend_tradable)
        weights, turnover = apply_tradability_constraints(date, target_weights, prev_weights)
        
        # Rebalance (déterministe : même prix = même résultat)
        nav = rebalance(weights, prices[date], nav_prev, fees, slippage)
    
    return nav_series, weights_series, metrics
```

**Points de déterminisme :**
- Calendar : Même période = même dates
- Prices : Même DB = mêmes prix
- Strategy : Même logique = mêmes target weights
- Tradability : Même règles = mêmes contraintes
- Costs : Même turnover = mêmes coûts

#### Lisibilité

**Code lisible :**
- Fonctions pures (pas de side effects)
- Noms explicites : `compute_target_weights`, `apply_tradability_constraints`
- Séparation des responsabilités : Engine (logique pure) vs Repository (persistence)
- Pas de magic numbers : Constantes nommées (`DECIMAL_PRECISION = Decimal('0.000001')`)

### 7.2 Entrées d'un backtest

**Schéma Pydantic :** `BacktestCreateRequest`

**Champs obligatoires :**

1. **`start_date`** : Date de début (ISO format "YYYY-MM-DD")
   - Type : `date`
   - Validation : Doit être <= `end_date`

2. **`end_date`** : Date de fin (ISO format "YYYY-MM-DD")
   - Type : `date`
   - Validation : Doit être >= `start_date`

3. **`instrument_ids` OU `bundle_id`** (XOR)
   - Si `bundle_id` fourni : Utilise les instruments du bundle (résolus)
   - Si `instrument_ids` fourni : Utilise ces instruments directement
   - Validation : Au moins un doit être fourni

**Champs optionnels :**

4. **`rebalance`** : Fréquence de rebalancement
   - Valeurs : `"daily"`, `"weekly"`, `"monthly"`
   - Défaut : `"weekly"` (si bundle sélectionné), sinon dépend de l'UI
   - Impact : Dates de rebalancement calculées selon cette fréquence

5. **`strategy`** : Stratégie d'allocation (si `bundle_id` absent)
   - Type : `"equal_weight"` ou `"momentum"`
   - Params : `lookback_days` (si momentum)
   - Note : Si `bundle_id` fourni, strategy est ignorée (forced to `fixed_target_weights`)

6. **`fees_bps`** : Frais en basis points (0-10000)
   - Type : `Decimal`
   - Défaut : `0.0`
   - Calcul : `fees = (fees_bps / 10000) * turnover`

7. **`slippage_bps`** : Slippage en basis points (0-10000)
   - Type : `Decimal`
   - Défaut : `0.0`
   - Calcul : `slippage = (slippage_bps / 10000) * turnover`

8. **`allow_weekend_trading`** : Autoriser trading le weekend
   - Type : `bool`
   - Défaut : `true`
   - Impact : Si `false`, freeze non-tradable instruments le weekend

**Exemple payload :**
```json
{
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "bundle_id": 1,
  "rebalance": "weekly",
  "fees_bps": 10.0,
  "slippage_bps": 5.0,
  "allow_weekend_trading": true
}
```

### 7.3 Rebalancing

#### Equal weight

**Stratégie :** `strategy_type = "equal_weight"`

**Algorithme :**
```python
def compute_target_weights_equal_weight(date, eligible_instruments):
    n = len(eligible_instruments)
    if n == 0:
        return {}
    weight = 1.0 / n
    return {inst_id: weight for inst_id in eligible_instruments}
```

**Comportement :**
- À chaque rebalance : Poids uniforme (1/N) pour tous les instruments éligibles
- Entre rebalances : Drift naturel selon performances
- Pas de lookback : Pas besoin d'historique

#### Fixed target weights (Bundle)

**Stratégie :** `rebalance_mode = "fixed_target_weights"` (forcé si `bundle_id` fourni)

**Algorithme :**
```python
def compute_target_weights_fixed(fixed_weights, eligible_instruments):
    # Filter to eligible instruments (have prices available)
    target_weights = {
        inst_id: weight
        for inst_id, weight in fixed_weights.items()
        if inst_id in eligible_instruments
    }
    
    # Normalize to sum to 1.0 (if some instruments filtered out)
    total = sum(target_weights.values())
    if total > 0:
        target_weights = {k: v / total for k, v in target_weights.items()}
    
    return target_weights
```

**Comportement :**
- À chaque rebalance : Retour aux poids cibles du bundle (source de vérité)
- Entre rebalances : Drift naturel selon performances
- Bundle weights : Jamais recalculés (fixes)

**Exemple :**
- Bundle : BTCUSD 60%, ETHUSD 40%
- Après une semaine : Drift à 70%/30%
- Au rebalance : Retour à 60%/40% (target weights du bundle)

#### Momentum

**Stratégie :** `strategy_type = "momentum"` (requiert `lookback_days`)

**Algorithme :**
```python
def compute_target_weights_momentum(date, open_prices, returns, lookback_days, eligible_instruments):
    # Score = (price[t] / price[t-lookback]) - 1
    scores = {}
    for inst_id in eligible_instruments:
        current_price = open_prices.loc[date, inst_id]
        lookback_price = open_prices.loc[date - lookback_days, inst_id]
        score = (current_price / lookback_price) - 1.0
        scores[inst_id] = max(0, score)  # Long-only (negative scores = 0)
    
    # Weights proportional to scores (normalized to sum to 1)
    total_score = sum(scores.values())
    if total_score == 0:
        return equal_weight(...)  # Fallback
    
    weights = {inst_id: score / total_score for inst_id, score in scores.items()}
    return weights
```

**Comportement :**
- À chaque rebalance : Poids proportionnels aux scores de momentum
- Scores : Ratio prix actuel / prix il y a N jours - 1
- Long-only : Scores négatifs → poids = 0
- Fallback : Si tous scores <= 0, égal weight

#### Drift entre rebalances

**Comportement :**
- Entre rebalances : Les poids ne changent PAS (drift naturel)
- La NAV évolue selon : `NAV[t] = NAV[t-1] * (1 + portfolio_return - costs)`
- L'allocation dérive selon les performances relatives

**Exemple :**
- Rebalance Lundi : BTCUSD 60%, ETHUSD 40%
- Lundi-Vendredi : BTC +5%, ETH +2%
- Vendredi (avant rebalance) : BTCUSD ~62%, ETHUSD ~38% (drift)
- Rebalance Lundi suivant : Retour à 60%/40% (target weights)

#### Missing price → skip rebalance

**Règle critique :** Si un instrument requis n'a pas de prix open à la date de rebalance, **skip le rebalance** ce jour.

**Algorithme :**
```python
def check_missing_prices(rebalance_date, required_instruments, open_prices):
    missing = []
    for inst_id in required_instruments:
        if inst_id not in open_prices.columns or pd.isna(open_prices.loc[rebalance_date, inst_id]):
            missing.append(inst_id)
    
    if missing:
        log.warning(f"Skipped rebalance on {rebalance_date}: missing prices for instruments {missing}")
        return True  # Skip rebalance
    
    return False  # Continue rebalance
```

**Comportement :**
- Skip : Garde les poids précédents
- Turnover : 0 ce jour (pas de trades)
- NAV : Continue avec drift naturel
- Warning : Log ajouté pour traçabilité

**Cas d'usage :**
- Jour férié : Prix manquants → skip rebalance
- Données incomplètes : Prix manquants pour certains instruments → skip
- Date future : Prix manquants → skip (normal)

### 7.4 Backtest avec Bundle

**Règle stricte :** Si `bundle_id` fourni, `rebalance_mode` est forcé à `"fixed_target_weights"`.

**Algorithme :**
```python
def run_backtest(request: BacktestCreateRequest):
    # 1. Load bundle if provided
    if request.bundle_id:
        bundle = db.query(Bundle).filter(Bundle.id == request.bundle_id).first()
        
        # Resolve bundle to instrument weights
        if bundle.type == 'fixed_instruments' or bundle.type == 'composite_fixed':
            fixed_weights = resolve_bundle_to_instrument_weights(bundle.id)
        elif bundle.type == 'dynamic':
            # Dynamic: resolve at each rebalance date
            fixed_weights = None  # Will be resolved dynamically
        else:
            raise ValueError(f"Unknown bundle type: {bundle.type}")
        
        # Force rebalance_mode
        rebalance_mode = "fixed_target_weights"
        instrument_ids = list(fixed_weights.keys()) if fixed_weights else []
    else:
        fixed_weights = None
        rebalance_mode = "strategy_based"
        instrument_ids = request.instrument_ids
    
    # 2. Load prices
    prices = get_ohlc_matrix(db, instrument_ids, request.start_date, request.end_date)
    
    # 3. Run backtest loop
    for date in calendar:
        if date in rebalance_dates:
            # Compute target weights
            if rebalance_mode == "fixed_target_weights":
                if bundle.type == 'dynamic':
                    # Resolve dynamic bundle at this date
                    fixed_weights = resolve_bundle_effective_weights(bundle.id, date, prices)
                
                target_weights = compute_target_weights_fixed(fixed_weights, eligible_instruments)
            else:
                target_weights = compute_target_weights(date, strategy, prices, returns)
            
            # Rebalance
            weights, turnover = apply_tradability_constraints(...)
            nav = rebalance(weights, prices[date], nav_prev, fees, slippage)
        else:
            # Drift naturel (pas de rebalance)
            nav = nav_prev * (1 + portfolio_return)
```

**Strategy verrouillée :**
- Si bundle sélectionné : Strategy UI est disabled, affiche "Strategy defined by bundle allocation"
- Backend : Ignore `strategy` si `bundle_id` fourni

**Pourquoi :**
- Cohérence : Bundle définit l'allocation, pas une stratégie générique
- UX : Évite confusion (utilisateur ne peut pas sélectionner strategy incompatible)

**Implications UX :**
- Badge affiché : "Rebalancing: Fixed Target Weights"
- Table "Target Allocation" : Affiche les poids du bundle
- Strategy dropdown : Disabled si bundle sélectionné

---

## 8. Charts & Visualisation

### 8.1 Line vs Candlestick

#### Line Chart

**Format :** Ligne continue avec points de données

**Données :** `[{date, close}]` ou `[{date, open}]` ou `[{date, adj_close}]`

**Bibliothèque :** Recharts (existant) ou TradingView Lightweight Charts

**Utilisation :**
- Backtest results : NAV base 100
- Performance historique : Close prices
- Bundle preview : Close prices des instruments

**Avantages :**
- Simple : Affichage clair de tendance
- Performant : Moins de données à rendre

#### Candlestick Chart

**Format :** Chandeliers OHLC (Open, High, Low, Close)

**Données :** `[{time (UNIX seconds), open, high, low, close, volume}]`

**Bibliothèque :** TradingView Lightweight Charts (remplace Recharts pour candlestick)

**Endpoint :** `GET /api/market-data/candles?instrument_code=BTCUSD&provider=yahoo&start=2023-01-01&end=2024-01-01&tf=1d`

**Format réponse :**
```json
[
  {
    "time": 1704067200,  // UNIX seconds
    "open": 189.11,
    "high": 190.45,
    "low": 188.90,
    "close": 189.95,
    "volume": 172073400
  }
]
```

**Utilisation :**
- Single instrument : Affichage OHLC pour un instrument
- Market data preview : Visualisation des prix Yahoo importés

**Limitations :**
- **Candle interdit pour bundle** : Un bundle = plusieurs instruments, candlestick = un seul instrument
- **Single instrument uniquement** : Affichage candlestick uniquement si `selectedInstrumentIds.length === 1`

#### Switch Line / Candle

**UI Component :** `AssetPriceChart`

**Props :**
```typescript
interface AssetPriceChartProps {
  instrumentCode: string
  provider: "yahoo"
  startDate: string  // YYYY-MM-DD
  endDate: string    // YYYY-MM-DD
  viewMode: "line" | "candle"  // Toggle
  allowCandlestick?: boolean  // Enable/disable candlestick option
}
```

**Comportement :**
- Default : `viewMode="line"`
- Toggle : Switch "Line" / "Candle" (si `allowCandlestick=true`)
- If bundle : `allowCandlestick=false` (candlestick désactivé)

### 8.2 Base 100

**Normalisation :** Toutes les séries sont normalisées à base 100 pour comparaison

**Algorithme :**
```python
def normalize_to_base100(series, base=100):
    if len(series) == 0:
        return []
    
    first_value = series[0]
    if first_value == 0:
        return [0] * len(series)
    
    return [(value / first_value) * base for value in series]
```

**Utilisation :**
- Backtest NAV : `nav_base100` stocké en DB (base 100)
- Performance charts : Toutes les séries en base 100 pour comparaison
- Instrument series : `base100` stocké pour chaque instrument

**Avantages :**
- Comparabilité : Toutes les séries commencent à 100, facile de comparer performances
- Normalisation : Indépendant de l'échelle de prix (BTC ~$40000 vs ETH ~$2000)

### 8.3 Série unique vs multiple

#### Single Chart

**Format :** Une seule série affichée

**Utilisation :**
- Backtest NAV : Portfolio NAV uniquement
- Single instrument : Un seul instrument sélectionné

**Avantages :**
- Clarté : Focus sur une seule série
- Performance : Moins de données à rendre

#### Small Multiples

**Format :** Plusieurs graphiques côte à côte (un par instrument)

**Utilisation :**
- Backtest instruments : Un graphique par instrument du backtest
- Performance historique : Un graphique par instrument

**Avantages :**
- Comparaison : Visualiser plusieurs instruments simultanément
- Détails : Chaque instrument a son propre graphique (échelle indépendante)

**UI Toggle :**
```typescript
<select value={layout} onChange={...}>
  <option value="single">Single Chart</option>
  <option value="multiples">Small Multiples</option>
</select>
```

---

## 9. Frontend Admin (Next.js)

### 9.1 Pages

#### `/admin/market-data`

**Rôle :** Import de données historiques Yahoo Finance

**Fonctionnalités :**
- **HTML Table Import** : Textarea pour coller HTML, validate button, action buttons (insert_delta_only, overwrite_overlap, overwrite_all_range)
- **Asset Class Selection** : Dropdown (CRYPTO, ETF, INDEX, COMMODITIES, FOREX)
- **Instrument Code Input** : Text input (normalisé, uppercase)
- **Provider Symbol Input** : Text input optionnel (Yahoo format)
- **Results Display** : Analysis results, conflict details, skipped rows, events detected
- **Chart Preview** : Line chart (Open/Close/Adj Close), base 100 toggle, last 30 rows table

**États critiques :**
- `htmlTable` : État textarea HTML
- `htmlResult` : Résultat de l'analyse/ingestion
- `isLoading` : Loading state (validate/apply)
- `isApplying` : Applying state (mode application)
- `chartData` : Données pour chart preview

**Validations :**
- Button "Validate" disabled si : `!htmlTable.trim() || !htmlInstrumentCode.trim() || !htmlAssetClass`
- Asset Class requis : Dropdown avec placeholder "Select..."
- Instrument Code requis : Input avec placeholder "BTCUSD"

#### `/admin/bundles`

**Rôle :** Gestion des bundles (CRUD)

**Fonctionnalités :**
- **List Bundles** : Table avec filtres (asset_class, active), actions (edit, delete)
- **Create Bundle** : Form avec name, asset_class, type (fixed/composite/dynamic), components, dynamic_rule (JSON)
- **Edit Bundle** : Même form, pré-rempli avec données existantes
- **Validation Live** : Somme des poids affichée, disabled submit si != 100%
- **Components UI** : Add/remove components, type selector (instrument/bundle), weight input, instrument/bundle selector

**États critiques :**
- `bundleAllocations` : Allocations normalisées (pour affichage)
- `bundleAllocLoading` : Loading state (fetch allocations)
- `bundleAllocError` : Error state (failed to load)
- `components` : Liste des composants du bundle
- `dynamicRuleJson` : JSON string pour dynamic rule (si type=dynamic)

**Validations :**
- Weights sum : Live validation, disabled submit si != 100% (tolérance 0.01%)
- Discriminated union : Component type = instrument → instrument_code requis, child_bundle_id interdit
- Component type = bundle → child_bundle_id requis, instrument_code interdit
- Dynamic rule : Requis si type=dynamic, JSON valide

#### `/admin/backtests`

**Rôle :** Backtest builder et results

**Fonctionnalités :**
- **BacktestBuilder** : Left panel (configuration)
  - Asset Class & Bundle Selection
  - Instruments Selection (par catégorie, checkboxes, select all category)
  - Date Range (start/end)
  - Strategy Selection (equal_weight/momentum, disabled si bundle)
  - Rebalance Selection (daily/weekly/monthly)
  - Costs (fees_bps, slippage_bps)
  - Weekend Trading Toggle
  - Buttons : "Voir historiques", "Run Backtest"
  - Chart (si single instrument sélectionné, line/candle toggle)
- **BacktestResults** : Right panel (results)
  - Tabs : Chart, Stats, Weights (Debug)
  - Layout Toggle : Single Chart / Small Multiples
  - Performance metrics : CAGR, Volatility, Sharpe, Max Drawdown, Calmar

**États critiques :**
- `selectedAssetClass` : Asset class sélectionné
- `selectedBundleId` : Bundle sélectionné (null si manual selection)
- `selectedInstrumentIds` : IDs des instruments sélectionnés
- `bundleDetail` : Détails du bundle (pour affichage allocations)
- `bundleAllocations` : Allocations du bundle (normalisées)
- `isLoading` : Loading state (run backtest)
- `isLoadingHistory` : Loading state (view history)

**Validations :**
- Run Backtest : Requiert `bundle_id` OU `instrument_ids` (au moins un)
- Date Range : `start_date < end_date`
- Strategy : Momentum requiert `lookback_days`

### 9.2 États critiques

#### Loading States

**Pattern :** Toujours afficher un état de chargement pendant les opérations async

**Exemples :**
- `isLoading` : Bouton "Validate" → "Analyzing..."
- `isApplying` : Bouton "Add Delta Only" → "Applying..."
- `isLoadingInstruments` : Dropdown instruments → "Loading..."
- `bundleAllocLoading` : Table allocations → "Loading bundle allocation..."

**UX :** Disable les boutons pendant loading pour éviter double submission

#### Error States

**Pattern :** Afficher erreurs clairement avec messages actionnables

**Exemples :**
- `bundleAllocError` : Afficher erreur + bouton "Retry"
- `toastError` : Toast notification avec message détaillé
- Validation errors : Liste des erreurs Pydantic (field + message + index)

**UX :** Toujours fournir un moyen de réessayer ou corriger

#### Empty States

**Pattern :** Afficher message clair si pas de données

**Exemples :**
- Pas d'instruments : "No instruments available for this asset class"
- Pas de bundles : "No bundles available"
- Pas de résultats : "Run a backtest or click 'Voir historiques' to see results here"

**UX :** Message explicite + action suggérée si possible

#### Fallback

**Pattern :** Toujours avoir un fallback si données manquantes

**Exemples :**
- `bundleAllocations` undefined → `const allocs = bundleAllocations ?? []`
- `instrument.find()` null → Afficher `instrument_code` ou "Unknown"
- Preview failed → Fallback à `components` si disponible

### 9.3 Proxy API Next.js

**Pourquoi il existe :**
- Sécurité : Cacher `BACKEND_URL` et API keys côté client
- Auth : Ajouter JWT token automatiquement (extrait de session cookie)
- Logging : Log requests/responses côté serveur
- Error handling : Transformer erreurs backend en format frontend

**Pattern :**
```typescript
// web/src/app/api/market-data/yahoo/ingest-html-table/route.ts
export async function POST(req: Request) {
  // 1. Get session from cookie
  const session = await getSessionFromCookie(req)
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  
  // 2. Create JWT token
  const token = jwt.sign({ sub: session.userEmail }, JWT_SECRET)
  
  // 3. Forward request to FastAPI
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8000"
  const response = await fetch(`${backendUrl}/api/market-data/yahoo/ingest-html-table`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(await req.json()),
  })
  
  // 4. Transform response
  const data = await response.json()
  
  if (!response.ok) {
    // Log error for debugging
    console.error(`[Ingest HTML] Backend error (${response.status}):`, JSON.stringify(data).substring(0, 500))
    
    // Forward error to frontend
    return NextResponse.json(data, { status: response.status })
  }
  
  // 5. Return success
  return NextResponse.json(data)
}
```

**Propagation des erreurs :**
- 422 (Validation) : Forward JSON `{detail: [...]}` tel quel
- 409 (Conflict) : Forward JSON `{status: "conflict", analysis: {...}}` tel quel
- 500 (Internal) : Log error, return generic message (pas d'exposition stack trace)

**Logging :**
- Request : Log URL, method, payload (masqué si sensible)
- Response : Log status, first 500 chars d'erreur
- Errors : Log stack trace côté serveur uniquement

---

## 10. Base de données

### 10.1 Tables clés

#### Market Data

**`market_data_instruments`** :
- PK : `id` (INTEGER)
- Unique : `symbol` (VARCHAR(20))
- Champs : `symbol`, `name`, `asset_class`, `weekend_tradable` (STRING "true"/"false"), `provider`, `provider_symbol`, `is_active` (STRING "true"/"false"), `archived_at`, `created_at`
- Indexes : `id`, `symbol`, `provider`, `is_active`

**`market_data_bars_d1`** :
- PK : `(instrument_id, date)` (composite)
- Unique : `(instrument_id, date)`
- FK : `instrument_id` → `market_data_instruments.id`
- Champs : `instrument_id`, `date` (DATE), `open`, `high`, `low`, `close` (NUMERIC(20,8)), `volume` (BIGINT), `source`, `created_at`
- Indexes : `instrument_id`, `date`, `(instrument_id, date)`

#### Bundles

**`bundles`** :
- PK : `id` (INTEGER)
- Unique : `(name, asset_class)`
- Champs : `id`, `name`, `asset_class`, `type` ("fixed_instruments", "composite_fixed", "dynamic"), `description`, `is_active` (STRING), `created_at`, `updated_at`, `created_by_email`
- Indexes : `id`, `asset_class`, `type`, `is_active`

**`bundle_components`** :
- PK : `id` (INTEGER)
- Unique : `(bundle_id, component_type, instrument_id, child_bundle_id)`
- FK : `bundle_id` → `bundles.id`, `instrument_id` → `market_data_instruments.id`, `child_bundle_id` → `bundles.id`
- Champs : `id`, `bundle_id`, `component_type` ("instrument" ou "bundle"), `instrument_id` (nullable), `child_bundle_id` (nullable), `weight` (NUMERIC(10,4)), `position_order`, `created_at`
- Contrainte : `instrument_id IS NOT NULL XOR child_bundle_id IS NOT NULL` (logique applicative, pas DB)
- Indexes : `bundle_id`, `instrument_id`, `child_bundle_id`

**`bundle_dynamic_rules`** :
- PK : `id` (INTEGER)
- FK : `bundle_id` → `bundles.id` (CASCADE)
- Champs : `id`, `bundle_id`, `rule_type` ("formula_dsl"), `rule_json` (JSON), `version`, `is_active` (STRING), `created_at`, `updated_at`
- Indexes : `bundle_id`

#### Backtests

**`backtest_runs`** :
- PK : `id` (INTEGER)
- FK : `bundle_id` → `bundles.id` (SET NULL)
- Champs : `id`, `name`, `created_by_user_id`, `created_by_email`, `created_at`, `start_date`, `end_date`, `effective_start_date`, `effective_end_date`, `rebalance` ("daily"/"weekly"/"monthly"), `rebalance_mode` ("strategy_based"/"fixed_target_weights"), `strategy_type` ("equal_weight"/"momentum"), `strategy_params_json` (JSON), `bundle_id`, `fees_bps`, `slippage_bps`, `allow_weekend_trading` (STRING), `instrument_ids_json` (JSON), `status` ("PENDING"/"SUCCESS"/"FAILED"), `error_message`
- Indexes : `id`, `bundle_id`, `status`, `created_at`

**`backtest_portfolio_series`** :
- PK : `(run_id, date)` (composite)
- Unique : `(run_id, date)`
- FK : `run_id` → `backtest_runs.id` (CASCADE)
- Champs : `run_id`, `date` (DATE), `nav_base100` (NUMERIC(20,8)), `portfolio_return` (NUMERIC(20,8)), `drawdown` (NUMERIC(20,8)), `turnover` (NUMERIC(20,8)), `costs` (NUMERIC(20,8)), `weights_json` (JSON), `tradable_json` (JSON)
- Indexes : `run_id`, `date`, `(run_id, date)`

**`backtest_instrument_series`** :
- PK : `(run_id, instrument_id, date)` (composite)
- Unique : `(run_id, instrument_id, date)`
- FK : `run_id` → `backtest_runs.id`, `instrument_id` → `market_data_instruments.id`
- Champs : `run_id`, `instrument_id`, `date` (DATE), `base100` (NUMERIC(20,8)), `instrument_return` (NUMERIC(20,8))
- Indexes : `run_id`, `instrument_id`, `date`

**`backtest_metrics`** :
- PK : `id` (INTEGER)
- Unique : `(run_id, scope, instrument_id, key)`
- FK : `run_id` → `backtest_runs.id`, `instrument_id` → `market_data_instruments.id`
- Champs : `id`, `run_id`, `scope` ("portfolio" ou "instrument"), `instrument_id` (nullable, NULL pour portfolio), `key` ("cagr", "volatility", "sharpe", "max_drawdown", "calmar"), `value` (NUMERIC(20,8))
- Indexes : `run_id`, `scope`, `instrument_id`, `key`

### 10.2 Relations

**Market Data → Bundles :**
- `bundle_components.instrument_id` → `market_data_instruments.id` (CASCADE)
- Un instrument peut être dans plusieurs bundles

**Bundles → Backtests :**
- `backtest_runs.bundle_id` → `bundles.id` (SET NULL)
- Un bundle peut être utilisé dans plusieurs backtests
- Si bundle supprimé, `bundle_id` devient NULL (backtest reste mais sans bundle)

**Market Data → Backtests :**
- `backtest_instrument_series.instrument_id` → `market_data_instruments.id`
- Un instrument peut être dans plusieurs backtests

**Bundles → Bundles (Composite) :**
- `bundle_components.child_bundle_id` → `bundles.id` (CASCADE)
- Un bundle peut contenir d'autres bundles (composite)
- Cycle détecté logiquement (pas de contrainte DB)

### 10.3 Contraintes

**Unique Constraints :**
- `market_data_instruments.symbol` : UNIQUE (pas de doublons)
- `market_data_bars_d1(instrument_id, date)` : UNIQUE (un seul bar par date par instrument)
- `bundles(name, asset_class)` : UNIQUE (pas de bundles du même nom dans la même asset class)
- `bundle_components(bundle_id, component_type, instrument_id, child_bundle_id)` : UNIQUE (pas de composant dupliqué)

**Foreign Key Constraints :**
- CASCADE : Si instrument supprimé, supprimer bars (normally instruments not deleted, archived)
- CASCADE : Si bundle supprimé, supprimer components et dynamic_rules
- SET NULL : Si bundle supprimé, `backtest_runs.bundle_id` devient NULL

**Check Constraints (logiques, pas DB) :**
- `bundle_components` : `(instrument_id IS NOT NULL) XOR (child_bundle_id IS NOT NULL)` (validation applicative)
- `bundle_components.weight` : `weight >= 0 AND weight <= 100` (validation applicative)
- `bundles.components` : Somme des poids ≈ 100% (validation applicative)

### 10.4 Migrations Alembic importantes

**Migration 1 : Initial schema**
- Création tables `market_data_instruments`, `market_data_bars_d1`, `backtest_runs`, etc.

**Migration 2 : Add bundles**
- Création tables `bundles`, `bundle_allocations` (legacy)

**Migration 3 : Add bundle_id to backtest_runs**
- Ajout `bundle_id` (nullable, FK), `rebalance_mode` (nullable, default 'strategy_based')

**Migration 4 : Add bundle_components and bundle_dynamic_rules**
- Création `bundle_components` (unified table)
- Création `bundle_dynamic_rules` (dynamic bundles support)
- Migration de `bundle_allocations` vers `bundle_components`

**Migration 5 : Add archived_at to market_data_instruments**
- Ajout colonne `archived_at` (TIMESTAMP NULL) pour soft delete

**Migration 6 : Add FOREX asset class**
- Pas de migration DB nécessaire (asset_class est VARCHAR), mais documentation mise à jour

**Application :**
```bash
cd api
alembic upgrade head
```

---

## 11. Erreurs rencontrées & leçons apprises

### 11.1 map on undefined

**Erreur :** `TypeError: Cannot read properties of undefined (reading 'map')`

**Contexte :** `BacktestBuilder.tsx` ligne `bundleDetail.allocations.map(...)`

**Root cause :** `bundleDetail.allocations` peut être `undefined` pour bundles composite/dynamic (pas de champ `allocations`, utilise `components`)

**Fix :**
```typescript
// Avant
{bundleDetail.allocations.map(...)}

// Après
const allocs = bundleAllocations ?? []
{allocs.map(...)}
```

**Leçon :** Toujours défendre contre `undefined` avec `?? []` ou `?.map(...)`

### 11.2 422 validation errors

**Erreur :** `422 (Unprocessable Entity)` sans message clair affiché à l'utilisateur

**Root cause :** Frontend ne parse pas correctement le format FastAPI `{detail: [...]}`

**Fix :**
```typescript
// Avant
catch (error) {
  toast.error("Invalid request data")
}

// Après
catch (error) {
  const data = await error.json()
  if (data.detail && Array.isArray(data.detail)) {
    const errors = data.detail.map((e: any) => 
      `${e.loc.join('.')}: ${e.msg}`
    ).join(', ')
    toast.error(errors)
  } else {
    toast.error(data.message || "Invalid request data")
  }
}
```

**Leçon :** Toujours parser les erreurs FastAPI `detail` array pour afficher messages clairs

### 11.3 XOR validators

**Erreur :** `422` lors création bundle composite (instrument component avec `child_bundle_id` présent)

**Root cause :** Validation Pydantic non stricte (champs optionnels acceptés même s'ils ne devraient pas l'être)

**Fix :** Discriminated union avec Pydantic
```python
# Avant
class BundleComponentIn(BaseModel):
    component_type: str
    instrument_code: Optional[str] = None
    child_bundle_id: Optional[int] = None

# Après
class InstrumentComponentBase(BaseModel):
    component_type: Literal["instrument"]
    instrument_code: str  # Required
    model_config = {"extra": "forbid"}  # Reject child_bundle_id

class BundleComponentBase(BaseModel):
    component_type: Literal["bundle"]
    child_bundle_id: int  # Required
    model_config = {"extra": "forbid"}  # Reject instrument_code

BundleComponentIn = Annotated[
    Union[InstrumentComponentBase, BundleComponentBase],
    Discriminator('component_type')
]
```

**Leçon :** Utiliser discriminated unions Pydantic pour validation stricte XOR

### 11.4 provider mismatch

**Erreur :** Instruments non visibles dans backtest builder malgré données en DB

**Root cause :** Filtrage strict `provider='yahoo'` et `is_active='true'`, mais certains instruments ont `provider='alphavantage'` (legacy)

**Fix :** Migration de données + cleanup script
```python
# Update legacy instruments
db.query(MarketDataInstrument).filter(
    MarketDataInstrument.provider != "yahoo"
).update({"provider": "yahoo", "is_active": "false"})
```

**Leçon :** Toujours valider les filtres de données en production (legacy data peut violer assumptions)

### 11.5 Pourquoi ces bugs sont arrivés

**Patterns communs :**
1. **Manque de défensive programming** : Assumptions que données sont toujours présentes
2. **Validation insuffisante** : Schémas Pydantic non stricts (champs optionnels acceptés)
3. **Legacy data** : Anciennes données ne respectent pas nouvelles contraintes
4. **Error handling incomplet** : Erreurs backend non parsées correctement côté frontend

**Prévention :**
- Toujours défendre contre `undefined`/`null`
- Validation stricte (discriminated unions)
- Migration scripts pour legacy data
- Tests d'intégration (end-to-end)

---

## 12. Règles d'or du projet

### 12.1 Ce qu'il ne faut JAMAIS faire

1. **❌ NE JAMAIS modifier directement `MarketDataBarD1` en dehors de `bars_d1_repo.py`**
   - Utiliser toujours `get_bars_d1()`, `get_ohlc_matrix()`, etc.
   - Exception : `ingest_service.py` (nécessaire pour upsert)

2. **❌ NE JAMAIS changer le type de `weekend_tradable` ou `is_active` (doit rester STRING "true"/"false")**
   - Raison : Compatibilité legacy, contraintes DB
   - Si besoin booléen : Convertir côté applicatif

3. **❌ NE JAMAIS normaliser automatiquement les poids de bundle (somme != 100%)**
   - L'utilisateur doit corriger explicitement
   - Backend rejette si somme != 100% (tolérance 0.01%)

4. **❌ NE JAMAIS skip rebalance silencieusement (sans log)**
   - Toujours logger warning : `"Skipped rebalance on {date}: missing prices for {instruments}"`

5. **❌ NE JAMAIS écraser des données existantes sans smart update (dry_run)**
   - Toujours analyser d'abord (dry_run=true)
   - Demander confirmation si conflits détectés

6. **❌ NE JAMAIS utiliser Strapi ou CMS externe**
   - Tout est géré en interne (Next.js + Prisma + FastAPI)

### 12.2 Ce qui est source de bugs

1. **Assumptions sur données présentes :**
   - `bundleDetail.allocations` peut être `undefined` → Toujours `?? []`
   - `instrument.find()` peut être `null` → Toujours fallback

2. **Validation non stricte :**
   - Champs optionnels acceptés même s'ils ne devraient pas l'être → Discriminated unions

3. **Legacy data :**
   - Anciennes données ne respectent pas nouvelles contraintes → Migration scripts

4. **Error handling incomplet :**
   - Erreurs backend non parsées → Parser `detail` array FastAPI

### 12.3 Invariants à respecter

1. **Invariant 1 :** Si `bundle_id` fourni, `rebalance_mode = "fixed_target_weights"` (forcé)
2. **Invariant 2 :** Bundle weights somme ≈ 100% (tolérance 0.01%)
3. **Invariant 3 :** Un instrument = un seul bar par date (contrainte UNIQUE)
4. **Invariant 4 :** Bundle components : `(instrument_id IS NOT NULL) XOR (child_bundle_id IS NOT NULL)`
5. **Invariant 5 :** Tous les prix passent par `bars_d1_repo.py` (source unique)
6. **Invariant 6 :** Backtests déterministes (mêmes entrées = mêmes sorties)

---

## 13. Comment reprendre le projet après un arrêt

### 13.1 CHECKLIST : Services à lancer

**Étape 1 : Vérifier Docker**
```bash
docker ps | grep arquantix-db
# Doit afficher : arquantix-db running, healthy, port 5443
```

**Étape 2 : Démarrer base de données (si arrêtée)**
```bash
docker start arquantix-db
docker ps | grep arquantix-db  # Vérifier "healthy"
```

**Étape 3 : Vérifier configurations .env**
```bash
# api/.env
DATABASE_URL=postgresql://arquantix:arquantix@localhost:5443/arquantix
JWT_SECRET_KEY=...

# web/.env
DATABASE_URL=postgresql://arquantix:arquantix@localhost:5443/arquantix_admin
BACKEND_URL=http://localhost:8000
```

**Étape 4 : Démarrer API (FastAPI)**
```bash
cd api
python3 -m uvicorn main:app --reload --port 8000
# Vérifier : http://localhost:8000/docs accessible
```

**Étape 5 : Démarrer Web (Next.js)**
```bash
cd web
npm run dev
# Vérifier : http://localhost:3000 accessible
```

**Ou utiliser script automatique :**
```bash
./scripts/arquantix-start.sh
```

### 13.2 Endpoints à tester

**Health checks :**
```bash
# API
curl http://localhost:8000/health
# Attendu : {"status": "ok", "service": "arquantix-api"}

# Web
curl http://localhost:3000
# Attendu : Page HTML (Next.js)
```

**API endpoints critiques :**
```bash
# Instruments (avec auth)
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/market-data/instruments?provider=yahoo&is_active=true

# Bundles
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/bundles

# Backtests
curl -H "Authorization: Bearer $JWT_TOKEN" http://localhost:8000/api/backtests
```

### 13.3 Pages à vérifier

1. **`/admin/login`** : Login fonctionne, redirige vers `/admin`
2. **`/admin/market-data`** : Page charge, dropdown asset class fonctionne
3. **`/admin/bundles`** : Liste bundles charge, create/edit fonctionne
4. **`/admin/backtests`** : Backtest builder charge, instruments affichés, run backtest fonctionne

**Tests manuels :**
- [ ] Login admin
- [ ] Market data : Paste HTML table, validate, apply
- [ ] Bundles : Create fixed bundle, create composite bundle, create dynamic bundle
- [ ] Backtests : Run backtest with bundle, run backtest with manual instruments, view results

### 13.4 Tests critiques

**Tests unitaires :**
```bash
cd api
python -m pytest tests/test_bundle_validation.py -v
python -m pytest tests/test_fixed_target_weights.py -v
python -m pytest tests/test_yahoo_ingest_smart_update.py -v
```

**Tests d'intégration :**
```bash
python -m pytest tests/test_backtest_with_bundle.py -v
```

**Tests manuels :**
- [ ] Ingest HTML table : Conflict detection fonctionne
- [ ] Bundle resolution : Fixed, composite, dynamic fonctionnent
- [ ] Backtest : Fixed target weights rebalancing fonctionne
- [ ] Charts : Line et candlestick fonctionnent

### 13.5 Fichiers à relire en priorité

**Si problème Market Data :**
1. `api/services/market_data/routes.py` (endpoints)
2. `api/services/market_data/ingest_service.py` (smart update)
3. `api/services/market_data/bars_d1_repo.py` (accès prix)
4. `web/src/app/admin/market-data/page.tsx` (UI)

**Si problème Bundles :**
1. `api/services/bundles/resolver.py` (résolution)
2. `api/services/bundles/routes.py` (endpoints)
3. `api/services/bundles/schemas.py` (validation Pydantic)
4. `web/src/app/admin/bundles/new/page.tsx` (UI)

**Si problème Backtests :**
1. `api/services/backtest/engine.py` (logique pure)
2. `api/services/backtest/routes.py` (endpoints)
3. `web/src/components/backtests/BacktestBuilder.tsx` (UI)

---

## 14. Extensions futures prévues

### 14.1 Bundles dynamiques avancés

**Objectif :** Support de règles DSL plus complexes

**Exemples :**
- **Volatility targeting** : Ajuster poids selon volatilité
- **Correlation-based** : Poids inversement proportionnels à corrélation
- **Risk parity** : Poids égaux en risque (pas en capital)

**DSL extensions :**
```json
{
  "op": "vol_target",
  "instrument_code": "BTCUSD",
  "target_vol": 0.15,
  "window": 20
}
```

### 14.2 Allocation conditionnelle

**Objectif :** Poids variables selon conditions (if/else avancé)

**Exemple :**
```json
{
  "op": "if",
  "cond": {"op": "gt", "a": {"op": "sma", ...}, "b": 20000},
  "then": 0.6,
  "else": 0.4
}
```

### 14.3 Multi-timeframe

**Objectif :** Support de timeframes autres que D1 (H1, H4, M15, M30)

**Changements nécessaires :**
- Nouvelles tables : `market_data_bars_h1`, `market_data_bars_h4`, etc.
- Migration : Import depuis nouvelles sources
- Engine : Adaptation pour différents timeframes

### 14.4 Risk parity

**Objectif :** Allocation égale en risque (pas en capital)

**Algorithme :**
- Calculer volatilité de chaque instrument
- Poids inversement proportionnels à volatilité
- Normaliser pour somme = 1.0

### 14.5 Corrélation

**Objectif :** Utiliser corrélations dans allocations

**Exemple :**
- Instruments hautement corrélés → Réduire poids
- Instruments faiblement corrélés → Augmenter poids (diversification)

### 14.6 Vol targeting

**Objectif :** Maintenir volatilité cible du portefeuille

**Algorithme :**
- Calculer volatilité actuelle du portefeuille
- Si volatilité > target : Réduire leverage
- Si volatilité < target : Augmenter leverage (si possible)

---

## Conclusion

Cette documentation est **LA source de vérité** pour comprendre Arquantix. Elle couvre :

- ✅ Architecture globale (Frontend/Backend/DB)
- ✅ Market Data (Asset Classes, Instruments, Bars D1, Ingestion Yahoo)
- ✅ Bundles (Fixed, Composite, Dynamic, Resolver)
- ✅ Backtests (Engine, Rebalancing, Métriques)
- ✅ Charts & Visualisation
- ✅ Frontend Admin (Pages, États, Proxy API)
- ✅ Base de données (Schéma, Relations, Migrations)
- ✅ Erreurs rencontrées & Correctifs
- ✅ Règles d'or & Invariants
- ✅ Comment reprendre le projet
- ✅ Extensions futures

**⚠️ IMPORTANT :** Cette documentation doit être mise à jour à chaque modification majeure du système. Elle est destinée à être lue par des humains ET des LLMs (ChatGPT, Cursor AI) pour comprendre le projet sans contexte préalable.

**Dernière mise à jour :** 2026-01-10


