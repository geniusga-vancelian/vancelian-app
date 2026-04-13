# AUDIT COMPLET — Market Data Arquantix

**Date** : 2026-01-09  
**Périmètre** : vancelian-app/services/arquantix  
**Objectif** : Comprendre l'état actuel du système Market Data avant toute modification

---

## 1. STACK TECHNIQUE

### 1.1 Frontend (Next.js)

**Version** : Next.js 14.2.0 (d'après `web/package.json`)

**Router** : **App Router** (confirmé par structure `web/src/app/`)
- Pages dans `web/src/app/`
- API Routes dans `web/src/app/api/`
- Layout dans `web/src/app/admin/layout.tsx`

**Framework UI** : 
- **Tailwind CSS** 3.4.13
- **shadcn/ui** (composants Radix UI)
- **Recharts** 3.6.0 (graphiques)

**ORM Frontend** : **Prisma** 6.19.1
- Schéma : `web/prisma/schema.prisma`
- Client : `web/src/lib/prisma.ts`
- Migrations : `web/prisma/migrations/`

**Base de données Frontend** :
- Nom : `arquantix_admin` (d'après README.md)
- Port : `5443` (localhost)
- Tables : `users`, `sessions`, `pages`, `sections`, `section_contents`, `media`, etc.

### 1.2 Backend (FastAPI)

**Version** : FastAPI 0.109.0

**Structure des services** :
```
api/services/
├── market_data/        # Module Market Data
│   ├── routes.py       # Endpoints FastAPI
│   ├── schemas.py      # Pydantic models
│   ├── client.py       # Alpha Vantage client
│   ├── yahoo_client.py # Yahoo Finance client
│   └── config.py       # Configuration
├── backtest/           # Module Backtest Engine
├── ai_email/           # Module Email Builder
├── translate.py        # Module Auto-Translate
└── diagnostics/        # Module Diagnostics
```

**ORM Backend** : **SQLAlchemy** 2.0.25
- Modèles : `api/database.py`
- Session : `SessionLocal` (sessionmaker)
- Migrations : **Alembic** 1.13.1
- Migrations : `api/alembic/versions/`

**Base de données Backend** :
- Nom : **`arquantix`** (par défaut, d'après `database.py` ligne 25)
- Port : `5443` (localhost)
- **Note importante** : Il existe aussi `arquantix_quant` mentionnée dans la doc, mais les modèles Market Data sont dans la base principale `arquantix`

**Connexion DB** :
- Variable : `DATABASE_URL` (env var)
- Format : `postgresql://user:password@host:port/dbname`
- Default : `postgresql://arquantix:arquantix@localhost:5433/arquantix`

### 1.3 Authentification

**Frontend → Backend** :
1. Frontend : Session cookie (`arq_admin_session`) via Prisma `Session` table
2. Next.js API Route : `getSessionFromCookie()` → extrait `userEmail`
3. JWT signing : `jwt.sign({ sub: userEmail, email: userEmail }, secret, { expiresIn: '1h' })`
4. Backend : `Depends(get_current_user)` valide JWT Bearer token

**Secret partagé** :
- Backend : `JWT_SECRET_KEY` (env var)
- Frontend : `JWT_SECRET_KEY` ou `AUTH_SECRET` (fallback: `'dev-secret-change-me'`)

---

## 2. MARKET DATA — ÉTAT ACTUEL

### 2.1 Tables de Base de Données

#### Table `market_data_instruments`

**Schéma** (d'après `api/database.py` lignes 212-227 et migration `dd7124eabc4d`) :

| Colonne | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | `INTEGER` | NO | PK, auto-increment, indexé |
| `symbol` | `VARCHAR(20)` | NO | Symbole unique (ex: "BTC", "AAPL") |
| `name` | `VARCHAR(200)` | YES | Nom complet (nullable) |
| `asset_class` | `VARCHAR(20)` | NO | "equity", "etf", "crypto" |
| `weekend_tradable` | `VARCHAR(10)` | NO | "true" ou "false" (string, default: "false") |
| `provider` | `VARCHAR(50)` | NO | "alphavantage" ou "yahoo" (default: "alphavantage") |
| `provider_symbol` | `VARCHAR(50)` | YES | Symbole provider (ex: "BTC-USD" pour Yahoo) |
| `is_active` | `VARCHAR(10)` | NO | "true" ou "false" (string, default: "true") |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NO | Date création (server default) |

**Contraintes** :
- `PRIMARY KEY (id)`
- `UNIQUE (symbol)`
- `INDEX (id)`
- `INDEX (symbol)`

**Schema** : `public`

#### Table `market_data_bars_d1`

**Schéma** (d'après `api/database.py` lignes 230-246 et migration `dd7124eabc4d`) :

| Colonne | Type | Nullable | Description |
|--------|------|----------|-------------|
| `instrument_id` | `INTEGER` | NO | FK → `market_data_instruments.id`, PK partielle |
| `date` | `DATE` | NO | Date du bar, PK partielle |
| `open` | `NUMERIC(20, 8)` | NO | Prix d'ouverture |
| `high` | `NUMERIC(20, 8)` | NO | Prix maximum |
| `low` | `NUMERIC(20, 8)` | NO | Prix minimum |
| `close` | `NUMERIC(20, 8)` | NO | Prix de clôture |
| `volume` | `BIGINT` | NO | Volume échangé |
| `source` | `VARCHAR(50)` | NO | "alphavantage" ou "yahoo" (default: "alphavantage") |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NO | Date insertion (server default) |

**Contraintes** :
- `PRIMARY KEY (instrument_id, date)`
- `UNIQUE (instrument_id, date)` (nom: `uq_market_data_bars_d1_instrument_date`)
- `FOREIGN KEY (instrument_id) REFERENCES market_data_instruments(id)`
- `INDEX (instrument_id)`
- `INDEX (date)`

**Schema** : `public`

**⚠️ IMPORTANT** :
- **PAS de colonne `adj_close`** dans la table
- Le client Yahoo récupère `adj_close` mais ne le stocke PAS en DB
- Seuls `open`, `high`, `low`, `close`, `volume` sont stockés
- L'endpoint `/instruments/{instrument_code}/series` retourne `adj_close=None` (ligne 1495)

#### Tables Corporate Actions (Dividends / Splits)

**❌ AUCUNE TABLE IDENTIFIÉE**

Recherche effectuée :
- Aucune table `market_data_dividends`, `market_data_splits`, `market_data_corporate_actions`
- Aucune référence dans les modèles SQLAlchemy
- Aucune migration Alembic pour corporate actions

**Conclusion** : Les dividendes et splits ne sont **PAS stockés** dans la base de données actuellement.

### 2.2 Endpoints Existants

#### Endpoints Alpha Vantage (Provider principal)

**Router** : `/api/market-data` (d'après `routes.py` ligne 50)

1. **`GET /api/market-data/instruments`**
   - Liste tous les instruments
   - Query params : `is_active`, `asset_class`
   - Protection : `Depends(get_current_user)`

2. **`POST /api/market-data/instruments/seed`**
   - Seed CORE_V1 universe (7 instruments)
   - Body : `{ universe: "CORE_V1" }`

3. **`POST /api/market-data/instruments/{instrument_id}/backfill`**
   - Backfill historique pour un instrument
   - Body : `{ start_date: "YYYY-MM-DD", end_date: "YYYY-MM-DD" }`
   - Utilise Alpha Vantage API

4. **`POST /api/market-data/update-daily`**
   - Mise à jour incrémentale (aujourd'hui + hier)
   - Pour tous instruments actifs

5. **`GET /api/market-data/instruments/{instrument_id}/bars`**
   - Récupère bars D1 dans une plage de dates
   - Query params : `start`, `end` (YYYY-MM-DD)

6. **`GET /api/market-data/instruments/{instrument_id}/quote`**
   - Dernière cotation

7. **`GET /api/market-data/missing`**
   - Liste instruments sans bars

8. **`POST /api/market-data/backfill-missing`**
   - Backfill tous instruments manquants
   - Body : `{ days: int, symbols?: List[str], force: bool }`

9. **`POST /api/market-data/validate-provider`**
   - Valide Alpha Vantage pour symboles AVANT insertion

10. **`GET /api/market-data/performance`**
    - Historique performance (base100) pour instruments
    - Query params : `instrument_ids`, `start`, `end`, `base`

#### Endpoints Yahoo Finance (Nouveau)

11. **`POST /api/market-data/yahoo/ingest-from-url`**
    - Ingest depuis URL Yahoo Finance
    - Body : `{ url: string, instrument_code: string, asset_class?: string, weekend_tradable?: bool }`
    - Retourne : `YahooIngestResponse` avec `chart_series` (30 derniers points)

12. **`POST /api/market-data/yahoo/ingest-csv`**
    - Ingest depuis CSV upload (multipart)
    - Form data : `file`, `instrument_code`, `asset_class?`, `weekend_tradable?`, `provider_symbol?`

13. **`GET /api/market-data/instruments/{instrument_code}/series`**
    - Récupère série pour chart (par code, pas ID)
    - Query params : `start?`, `end?` (default: 90 derniers jours)
    - Retourne : `{ instrument, start_date, end_date, count, series: ChartSeriesPoint[] }`

### 2.3 Client Yahoo Finance

**Fichier** : `api/services/market_data/yahoo_client.py`

**Fonctionnalités** :
- `parse_yahoo_url()` : Extrait ticker + period1/period2 de l'URL
- `build_download_urls()` : Construit URLs CSV et Chart JSON
- `download_csv()` : Télécharge et parse CSV
- `download_chart_json()` : Télécharge et parse Chart JSON (fallback)
- `fetch_data()` : Essaie CSV d'abord, puis Chart JSON

**Endpoints utilisés** :
- CSV : `https://query1.finance.yahoo.com/v7/finance/download/{ticker}?period1=...&period2=...&interval=1d&events=history&includeAdjustedClose=true`
- Chart : `https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?period1=...&period2=...&interval=1d&events=history&includeAdjustedClose=true`

**Gestion d'erreurs** :
- Détection HTML error page (cookie/crumb requis)
- Fallback CSV → Chart JSON
- Messages d'erreur clairs

**⚠️ LIMITATION** :
- Pas de gestion de cookie/crumb Yahoo (peut échouer si Yahoo bloque)
- Pas de retry automatique (seulement fallback CSV → Chart)

---

## 3. FRONT ADMIN

### 3.1 Pages Admin Market Data

#### Page `/admin/market-data`

**Fichier** : `web/src/app/admin/market-data/page.tsx`

**Fonctionnalités** :
1. **Formulaire upload** :
   - Input : Yahoo Finance URL
   - Input : Instrument Code
   - Select : Asset Class (CRYPTO/ETF/INDEX/METAL, auto-détect si ticker finit par -USD)
   - Button : "Upload Data" → `POST /api/market-data/yahoo/ingest-from-url`
   - File input : Upload CSV → `POST /api/market-data/yahoo/ingest-csv`

2. **Résultats** :
   - Résumé import (instrument, rows_upserted, date range, source)
   - Chart Recharts avec switch Open/Close/Adj Close
   - Toggle Base 100
   - Tableau preview (derniers 10 rows)
   - Button "Reload" → `GET /api/market-data/instruments/{code}/series`

**État** :
- `yahooUrl`, `instrumentCode`, `assetClass`, `weekendTradable`
- `result` : `YahooIngestResponse | null`
- `chartData` : `ChartSeriesPoint[]`
- `priceType` : `'open' | 'close' | 'adj_close'`
- `base100` : `boolean`

**Auto-détection** :
- Si URL contient ticker finissant par `-USD` → `assetClass = 'CRYPTO'`, `weekendTradable = true`
- Auto-remplissage `instrumentCode` si vide

#### Page `/admin/backtests`

**Fichier** : `web/src/app/admin/backtests/page.tsx`

**Composants utilisés** :
- `MarketDataBackfill` : Panel backfill Alpha Vantage
- `BacktestBuilder` : Builder backtest
- `BacktestResults` : Résultats backtest

**Note** : Cette page contient aussi un panel Market Data (via `MarketDataBackfill`), mais c'est pour Alpha Vantage, pas Yahoo.

### 3.2 Composants Frontend

**Répertoire** : `web/src/components/backtests/`

**Composants Market Data** :
- `MarketDataBackfill.tsx` : Panel backfill Alpha Vantage (validation, backfill missing, etc.)
- **PAS de composant dédié Yahoo** : La page `/admin/market-data` est self-contained

**Composants Backtest** :
- `BacktestBuilder.tsx` : Formulaire création backtest
- `BacktestResults.tsx` : Affichage résultats
- `BacktestChart.tsx` : Graphique Recharts
- `BacktestStatsTable.tsx` : Tableau métriques
- `HistoryChart.tsx` : Graphique historique
- `HistoryStatsTable.tsx` : Stats historique

### 3.3 Routes Proxy Next.js

**Répertoire** : `web/src/app/api/market-data/`

**Routes Yahoo** :
- `/api/market-data/yahoo/ingest-from-url/route.ts` : Proxy POST
- `/api/market-data/yahoo/ingest-csv/route.ts` : Proxy POST (multipart)
- `/api/market-data/instruments/[instrument_code]/series/route.ts` : Proxy GET

**Pattern** :
1. `getSessionFromCookie()` → vérifie session
2. `jwt.sign()` → crée JWT depuis `userEmail`
3. `buildBackendUrl()` → construit URL FastAPI
4. `fetch()` avec `Authorization: Bearer {token}`
5. Retourne réponse JSON (préserve status code backend)

**Routes Alpha Vantage** (existantes) :
- `/api/market-data/missing/route.ts`
- `/api/market-data/backfill-missing/route.ts`
- `/api/market-data/validate-provider/route.ts`
- `/api/market-data/performance/route.ts`
- `/api/market-data/instruments/route.ts`
- `/api/market-data/seed/route.ts`
- `/api/market-data/bars/route.ts`
- `/api/market-data/update-daily/route.ts`

### 3.4 Navigation Admin

**Fichier** : `web/src/app/admin/layout.tsx`

**Menu** :
- Dashboard (`/admin`)
- Menu & Pages (`/admin/pages`)
- Media (`/admin/media`)
- Projects (`/admin/projects`)
- Articles (`/admin/articles`)
- Help Center (`/admin/help`)
- Emails (`/admin/emails`)
- **Backtests** (`/admin/backtests`) — avec TrendingUp icon
- **Market Data** (`/admin/market-data`) — avec BarChart3 icon
- Diagnostics (`/admin/diagnostics`)
- Settings (`/admin/settings`)

---

## 4. INGESTION ACTUELLE

### 4.1 Types d'Import Implémentés

#### A) Alpha Vantage (Provider principal)

**Client** : `api/services/market_data/client.py`

**Fonctionnalités** :
- Rate limiting : 4 calls/minute (free tier)
- Fonctions :
  - `get_daily_equity_adjusted()` : ETFs/equities (TIME_SERIES_DAILY_ADJUSTED)
  - `get_daily_crypto()` : Crypto (DIGITAL_CURRENCY_DAILY)
- Parsing robuste avec fallback clés

**Endpoints utilisés** :
- `POST /api/market-data/instruments/{id}/backfill` : Backfill un instrument
- `POST /api/market-data/backfill-missing` : Backfill tous instruments manquants
- `POST /api/market-data/update-daily` : Update quotidien

**Stabilité** : **✅ STABLE**
- Rate limiting géré
- Gestion d'erreurs complète
- Validation préalable disponible

#### B) Yahoo Finance (Nouveau)

**Client** : `api/services/market_data/yahoo_client.py`

**Fonctionnalités** :
- Parser URL Yahoo Finance
- Download CSV (prioritaire)
- Fallback Chart JSON
- Gestion HTML error page (cookie/crumb)

**Endpoints utilisés** :
- `POST /api/market-data/yahoo/ingest-from-url` : Import depuis URL
- `POST /api/market-data/yahoo/ingest-csv` : Import depuis CSV upload

**Stabilité** : **⚠️ FRAGILE**
- **Problème cookie/crumb** : Yahoo peut bloquer les requêtes sans cookie valide
- **Pas de retry** : Si CSV et Chart JSON échouent, erreur immédiate
- **Pas de gestion User-Agent** : Utilise httpx par défaut (peut être bloqué)
- **Fallback CSV upload** : Disponible mais manuel

**Points d'échec identifiés** :
1. **429 Rate Limit** : Yahoo peut rate-limiter (pas de gestion dans le code)
2. **HTML Error Page** : Si cookie/crumb requis → erreur "HTML error page"
3. **JSON Parse Error** : Si Chart JSON malformé → crash
4. **Network Timeout** : Timeout 30s, pas de retry

### 4.2 Flux d'Ingestion Yahoo

**Flux actuel** :

```
1. Admin UI (/admin/market-data)
   ↓
2. User paste URL + instrument_code
   ↓
3. POST /api/market-data/yahoo/ingest-from-url (Next.js proxy)
   ↓
4. Next.js route → JWT → FastAPI
   ↓
5. YahooFinanceClient.parse_yahoo_url() → extract ticker
   ↓
6. YahooFinanceClient.fetch_data() :
   - Essaie download_csv()
   - Si échec → download_chart_json()
   ↓
7. Parse bars (CSV ou JSON)
   ↓
8. Upsert instrument (find or create)
   ↓
9. Upsert bars (by instrument_id + date)
   ↓
10. Return YahooIngestResponse avec chart_series (30 derniers)
   ↓
11. Frontend affiche chart immédiatement
```

**Points de fragilité** :
- **Étape 6** : Si Yahoo bloque (cookie/crumb) → erreur, pas de retry
- **Étape 8-9** : Transaction DB, rollback en cas d'erreur
- **Étape 10** : `adj_close` récupéré mais **PAS stocké en DB**

### 4.3 Données Récupérées vs Stockées

**Récupérées depuis Yahoo** :
- `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`

**Stockées en DB** :
- `date`, `open`, `high`, `low`, `close`, `volume`
- **`adj_close` : ❌ NON STOCKÉ**

**Impact** :
- Le calcul de "total return" (avec dividendes) nécessite `adj_close`
- Actuellement, `adj_close` est disponible uniquement dans `chart_series` (30 derniers points) retourné par l'endpoint
- L'endpoint `/instruments/{code}/series` retourne `adj_close=None` (ligne 1495)

---

## 5. CONTRAINTES IMPORTANTES

### 5.1 Ce que le Système FAIT DÉJÀ Correctement

**✅ Alpha Vantage Integration** :
- Rate limiting automatique (4 calls/min)
- Validation préalable des symboles
- Backfill séquentiel avec gestion d'erreurs
- Commit par instrument (pas de rollback global)

**✅ Yahoo Finance URL Parser** :
- Extraction robuste du ticker depuis URL
- Support period1/period2 dans URL
- Auto-override period2 = now()

**✅ Upsert Logic** :
- Pas de doublons (unique constraint `instrument_id + date`)
- Update si bar existe, insert sinon
- Transaction DB avec rollback en cas d'erreur

**✅ Frontend UX** :
- Auto-détection asset class depuis ticker
- Chart immédiat après import
- Gestion d'erreurs avec messages clairs
- Fallback CSV upload disponible

**✅ Séparation des Bases** :
- Frontend : `arquantix_admin` (Prisma)
- Backend : `arquantix` (SQLAlchemy)
- Pas de FK entre quant DB et admin DB (isolé)

### 5.2 Ce qui NE DOIT PAS être Cassé

**⚠️ CRITIQUE** :

1. **Convention Open-to-Open** :
   - Les backtests utilisent `open` (prix d'ouverture)
   - Ne PAS changer cette convention

2. **Weekend Tradability** :
   - Les backtests dépendent de `weekend_tradable` (string "true"/"false")
   - Ne PAS changer le format (string, pas boolean)

3. **Unique Constraint** :
   - `(instrument_id, date)` est la clé primaire
   - L'upsert dépend de cette contrainte
   - Ne PAS modifier

4. **Provider Field** :
   - Permet de distinguer "alphavantage" vs "yahoo"
   - Utilisé pour traçabilité
   - Ne PAS supprimer

5. **Source Field** :
   - Dans `market_data_bars_d1.source`
   - Permet de savoir d'où viennent les données
   - Ne PAS supprimer

### 5.3 Ce qui est Volontairement "Manuel"

**Vision produit** :

1. **Import Yahoo = Manuel** :
   - L'utilisateur doit coller l'URL ou uploader CSV
   - Pas d'automatisation (pas de cron, pas de background jobs)
   - **C'est volontaire** : contrôle total sur les données importées

2. **Pas de Corporate Actions en DB** :
   - Dividendes et splits ne sont PAS stockés
   - Seulement les prix OHLCV
   - **Raison probable** : MVP, focus sur les prix uniquement

3. **Pas d'adj_close en DB** :
   - `adj_close` est récupéré mais non stocké
   - Disponible uniquement dans `chart_series` (30 derniers points)
   - **Raison probable** : Économie d'espace, pas nécessaire pour backtests (qui utilisent `open`)

4. **Validation Préalable Manuelle** :
   - L'utilisateur doit valider Alpha Vantage avant backfill massif
   - Pas d'auto-validation
   - **C'est volontaire** : éviter les erreurs coûteuses

---

## 6. SYNTHÈSE

### 6.1 Diagramme Logique

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND (Next.js)                                           │
│ /admin/market-data                                           │
│   - Formulaire: URL + instrument_code                        │
│   - Chart Recharts (Open/Close/Adj Close)                   │
│   - Toggle Base 100                                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ POST /api/market-data/yahoo/ingest-from-url
                 │ (Next.js API Route avec JWT)
                 │
┌────────────────▼────────────────────────────────────────────┐
│ NEXT.JS PROXY                                                │
│ /api/market-data/yahoo/ingest-from-url/route.ts             │
│   - getSessionFromCookie()                                   │
│   - jwt.sign() → JWT                                         │
│   - buildBackendUrl() → FastAPI                              │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ POST /api/market-data/yahoo/ingest-from-url
                 │ Authorization: Bearer {JWT}
                 │
┌────────────────▼────────────────────────────────────────────┐
│ BACKEND (FastAPI)                                            │
│ api/services/market_data/routes.py                          │
│   - Depends(get_current_user) → valide JWT                  │
│   - YahooFinanceClient.parse_yahoo_url()                    │
│   - YahooFinanceClient.fetch_data()                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ YahooFinanceClient
                 │
┌────────────────▼────────────────────────────────────────────┐
│ YAHOO FINANCE API                                            │
│ query1.finance.yahoo.com/v7/finance/download/{ticker}      │
│ query2.finance.yahoo.com/v8/finance/chart/{ticker}          │
│   - CSV (prioritaire)                                        │
│   - Chart JSON (fallback)                                    │
│   ⚠️ Peut bloquer (cookie/crumb)                             │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Parse CSV/JSON → bars[]
                 │
┌────────────────▼────────────────────────────────────────────┐
│ PARSER                                                       │
│ yahoo_client.py                                              │
│   - Parse date, open, high, low, close, adj_close, volume  │
│   - Skip nulls (dividends/splits rows)                      │
│   - Return List[Dict]                                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Upsert logic
                 │
┌────────────────▼────────────────────────────────────────────┐
│ DATABASE (PostgreSQL)                                        │
│ arquantix.market_data_instruments                           │
│   - Find or create by symbol                                │
│ arquantix.market_data_bars_d1                               │
│   - Upsert by (instrument_id, date)                         │
│   - Store: open, high, low, close, volume                   │
│   - ❌ adj_close NOT stored                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Return YahooIngestResponse
                 │ (with chart_series: 30 last points)
                 │
┌────────────────▼────────────────────────────────────────────┐
│ FRONTEND                                                     │
│   - Display chart immediately                                │
│   - Show summary (rows, date range, source)                 │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Liste État Actuel

#### ✅ OK Tel Quel

1. **Structure DB** :
   - Tables `market_data_instruments` et `market_data_bars_d1` bien définies
   - Contraintes uniques correctes
   - Index appropriés

2. **Alpha Vantage Integration** :
   - Rate limiting fonctionnel
   - Gestion d'erreurs complète
   - Validation préalable disponible

3. **Yahoo URL Parser** :
   - Extraction ticker robuste
   - Support period1/period2

4. **Upsert Logic** :
   - Pas de doublons
   - Transaction DB avec rollback

5. **Frontend UX** :
   - Auto-détection asset class
   - Chart immédiat
   - Gestion d'erreurs claire

6. **Authentification** :
   - Flow session cookie → JWT fonctionnel
   - Protection endpoints correcte

#### ⚠️ Fragile

1. **Yahoo Finance API** :
   - **Cookie/Crumb** : Yahoo peut bloquer sans cookie valide
   - **Pas de retry** : Si CSV et Chart JSON échouent → erreur
   - **Pas de User-Agent** : httpx par défaut peut être bloqué
   - **Rate limiting** : Pas de gestion (peut recevoir 429)

2. **adj_close Non Stocké** :
   - Récupéré mais perdu après import
   - Disponible uniquement dans `chart_series` (30 points)
   - Impact : Impossible de calculer "total return" historique complet

3. **Pas de Corporate Actions** :
   - Dividendes et splits non stockés
   - Impact : Impossible de calculer "total return" avec dividendes

4. **Gestion d'Erreurs Yahoo** :
   - Messages d'erreur clairs mais pas de retry automatique
   - Fallback CSV upload = manuel

#### ❌ Manquant

1. **Table Corporate Actions** :
   - Pas de table pour dividendes
   - Pas de table pour splits
   - **Impact** : Impossible de calculer "total return" avec dividendes

2. **Colonne adj_close en DB** :
   - `adj_close` récupéré mais non stocké
   - **Impact** : Perte d'information après import

3. **Retry Logic Yahoo** :
   - Pas de retry automatique
   - Pas de gestion cookie/crumb
   - **Impact** : Échecs fréquents si Yahoo bloque

4. **User-Agent Yahoo** :
   - Pas de User-Agent personnalisé
   - **Impact** : Peut être bloqué par Yahoo

5. **Validation Yahoo Préalable** :
   - Pas d'endpoint de validation Yahoo (contrairement à Alpha Vantage)
   - **Impact** : Erreurs découvertes seulement à l'import

---

## 7. POINTS D'ATTENTION SPÉCIFIQUES

### 7.1 Base de Données

**⚠️ AMBIGUITÉ** : 
- Documentation mentionne `arquantix_quant` pour données quantitatives
- Mais les modèles Market Data sont dans la base principale `arquantix`
- **À CONFIRMER** : Quelle base est réellement utilisée en production ?

**Vérification** :
- `api/database.py` ligne 25 : Default = `arquantix`
- Scripts `create_db_quant.py`, `switch_env_to_quant.py` existent mais ne sont peut-être pas utilisés
- **INCONNU** : Quelle base est utilisée actuellement

### 7.2 adj_close

**État actuel** :
- Récupéré depuis Yahoo (CSV et Chart JSON)
- Disponible dans `YahooIngestResponse.chart_series` (30 derniers points)
- **NON stocké** en DB (`market_data_bars_d1` n'a pas cette colonne)
- Endpoint `/instruments/{code}/series` retourne `adj_close=None`

**Impact** :
- Pour calculer "total return" avec dividendes, il faut `adj_close`
- Actuellement, seulement 30 points disponibles dans `chart_series`
- **INCONNU** : Est-ce volontaire (économie d'espace) ou oubli ?

### 7.3 Corporate Actions

**État actuel** :
- Yahoo CSV contient des lignes "dividends" et "splits" (parsées mais skipées)
- Yahoo Chart JSON peut contenir `indicators.adjclose` (utilisé pour `adj_close`)
- **AUCUNE table** pour stocker dividendes/splits

**Impact** :
- Impossible de calculer "total return" avec dividendes historiques
- Impossible de tracker les événements corporatifs
- **INCONNU** : Est-ce dans le scope MVP ou future feature ?

### 7.4 Gestion d'Erreurs Yahoo

**Points d'échec identifiés** :

1. **Cookie/Crumb Requis** :
   - Yahoo peut retourner HTML error page
   - Message : "Yahoo Finance returned HTML error page (may require cookie/crumb)"
   - **Solution actuelle** : Fallback CSV upload manuel

2. **Rate Limiting** :
   - Pas de gestion (peut recevoir 429)
   - **Solution actuelle** : Aucune

3. **Network Timeout** :
   - Timeout 30s, pas de retry
   - **Solution actuelle** : Aucune

4. **JSON Parse Error** :
   - Si Chart JSON malformé → crash
   - **Solution actuelle** : Try/except basique

---

## 8. RECOMMANDATIONS POUR LA SUITE

**Max 10 lignes** :

1. **Ajouter colonne `adj_close`** dans `market_data_bars_d1` (migration Alembic) pour permettre calcul "total return" complet.

2. **Créer table `market_data_corporate_actions`** (date, type, value) pour stocker dividendes et splits séparément.

3. **Améliorer Yahoo client** : Ajouter User-Agent, retry logic (3 tentatives), gestion cookie/crumb basique.

4. **Ajouter endpoint validation Yahoo** : `POST /api/market-data/yahoo/validate` pour tester symboles avant import massif.

5. **Documenter décision** : Clarifier si `adj_close` et corporate actions sont dans le scope MVP ou future feature.

---

**Fin du rapport d'audit**

