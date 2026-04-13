# Database Schema — Market Data & Backtest

## Base de données

**Nom** : `arquantix_quant`

**Raison** : Séparation des données quantitatives (market data, backtest) de la base principale (admin_users, emails, etc.)

**Configuration** :
- `DATABASE_URL` dans `api/.env.local`
- Alembic migrations : `api/alembic/versions/`
- Pas de FK vers `admin_users` (quant DB isolée)

---

## Tables Market Data

### `market_data_instruments`

**Description** : Catalogue des instruments (actifs) disponibles.

**Colonnes** :

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | `INTEGER` | NO | PK, auto-increment |
| `symbol` | `VARCHAR(20)` | NO | Symbole unique (ex: "BTC", "QQQ") |
| `name` | `VARCHAR(200)` | YES | Nom complet (ex: "Bitcoin") |
| `asset_class` | `VARCHAR(20)` | NO | "equity", "etf", "crypto" |
| `weekend_tradable` | `VARCHAR(10)` | NO | "true" ou "false" (string) |
| `provider` | `VARCHAR(50)` | NO | "alphavantage" (default) |
| `provider_symbol` | `VARCHAR(50)` | YES | Symbole provider (peut différer de symbol) |
| `is_active` | `VARCHAR(10)` | NO | "true" ou "false" (string) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NO | Date création |

**Index** :
- `PRIMARY KEY (id)`
- `UNIQUE (symbol)`
- `INDEX (symbol)`

**Contraintes** :
- `symbol` unique

**Exemple** :
```sql
INSERT INTO market_data_instruments (symbol, name, asset_class, weekend_tradable, provider, provider_symbol, is_active)
VALUES ('BTC', 'Bitcoin', 'crypto', 'true', 'alphavantage', 'BTC', 'true');
```

**CORE_V1 Universe** (7 instruments actifs) :
- BTC, ETH, SOL (crypto, weekend_tradable=true)
- URTH, QQQ, DIA, GLD (etf, weekend_tradable=false)

---

### `market_data_bars_d1`

**Description** : Prix quotidiens (bars D1) par instrument.

**Colonnes** :

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `instrument_id` | `INTEGER` | NO | FK → `market_data_instruments.id` |
| `date` | `DATE` | NO | Date du bar |
| `open` | `NUMERIC(20, 8)` | NO | Prix d'ouverture |
| `high` | `NUMERIC(20, 8)` | NO | Prix maximum |
| `low` | `NUMERIC(20, 8)` | NO | Prix minimum |
| `close` | `NUMERIC(20, 8)` | NO | Prix de clôture |
| `volume` | `BIGINT` | NO | Volume échangé |
| `source` | `VARCHAR(50)` | NO | "alphavantage" (default) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NO | Date insertion |

**Index** :
- `PRIMARY KEY (instrument_id, date)`
- `INDEX (instrument_id)`
- `INDEX (date)`
- `UNIQUE (instrument_id, date)`

**Contraintes** :
- `FOREIGN KEY (instrument_id) REFERENCES market_data_instruments(id)`
- `UNIQUE (instrument_id, date)`

**Convention** : Prix OPEN utilisé pour backtest (open-to-open convention).

**Exemple** :
```sql
INSERT INTO market_data_bars_d1 (instrument_id, date, open, high, low, close, volume, source)
VALUES (1, '2024-01-01', 42000.00, 42500.00, 41500.00, 42200.00, 1000000, 'alphavantage');
```

---

## Tables Backtest

### `backtest_runs`

**Description** : Exécution d'un backtest (métadonnées).

**Colonnes** :

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | `INTEGER` | NO | PK, auto-increment |
| `name` | `VARCHAR(200)` | YES | Nom optionnel du backtest |
| `created_by_user_id` | `INTEGER` | YES | ID utilisateur (pas de FK, quant DB isolée) |
| `created_by_email` | `VARCHAR(255)` | YES | Email utilisateur (pour traçabilité) |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NO | Date création |
| `start_date` | `DATE` | NO | Date début demandée |
| `end_date` | `DATE` | NO | Date fin demandée |
| `effective_start_date` | `DATE` | YES | Date début effective (intersection données) |
| `effective_end_date` | `DATE` | YES | Date fin effective |
| `rebalance` | `VARCHAR(20)` | NO | "daily", "weekly", "monthly" |
| `strategy_type` | `VARCHAR(50)` | NO | "equal_weight", "momentum" |
| `strategy_params_json` | `JSON` | YES | Paramètres stratégie (ex: `{"lookback_days": 20}`) |
| `fees_bps` | `NUMERIC(10, 4)` | NO | Fees par trade (basis points) |
| `slippage_bps` | `NUMERIC(10, 4)` | NO | Slippage sur turnover (basis points) |
| `allow_weekend_trading` | `VARCHAR(10)` | NO | "true" ou "false" (string) |
| `instrument_ids_json` | `JSON` | NO | Array d'instrument IDs (ex: `[1, 2, 3]`) |
| `status` | `VARCHAR(20)` | NO | "PENDING", "SUCCESS", "FAILED" |
| `error_message` | `TEXT` | YES | Message d'erreur si status=FAILED |

**Index** :
- `PRIMARY KEY (id)`
- `INDEX (id)`

**Contraintes** :
- Pas de FK vers `admin_users` (quant DB isolée)

**Exemple** :
```sql
INSERT INTO backtest_runs (
    name, created_by_email, start_date, end_date, rebalance, strategy_type,
    strategy_params_json, fees_bps, slippage_bps, allow_weekend_trading,
    instrument_ids_json, status
)
VALUES (
    'Test BTC+SPY', 'admin@local.dev', '2024-01-01', '2024-12-31',
    'weekly', 'equal_weight', NULL, 0.0, 0.0, 'true',
    '[1, 2]', 'SUCCESS'
);
```

---

### `backtest_portfolio_series`

**Description** : Série temporelle du portefeuille (daily bars).

**Colonnes** :

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `run_id` | `INTEGER` | NO | FK → `backtest_runs.id` |
| `date` | `DATE` | NO | Date du bar |
| `nav_base100` | `NUMERIC(20, 8)` | NO | NAV base100 |
| `portfolio_return` | `NUMERIC(20, 8)` | NO | Return portfolio (open-to-open) |
| `drawdown` | `NUMERIC(20, 8)` | NO | Drawdown (négatif) |
| `turnover` | `NUMERIC(20, 8)` | NO | Turnover (0.5 * sum(|w_new - w_old|)) |
| `costs` | `NUMERIC(20, 8)` | NO | Costs (fees + slippage) |
| `weights_json` | `JSON` | YES | Poids par instrument (ex: `{"1": 0.5, "2": 0.5}`) |
| `tradable_json` | `JSON` | YES | Masque tradability (ex: `{"1": true, "2": false}`) |

**Index** :
- `PRIMARY KEY (run_id, date)`
- `INDEX (run_id)`
- `INDEX (date)`
- `UNIQUE (run_id, date)`

**Contraintes** :
- `FOREIGN KEY (run_id) REFERENCES backtest_runs(id)`
- `UNIQUE (run_id, date)`

**Exemple** :
```sql
INSERT INTO backtest_portfolio_series (
    run_id, date, nav_base100, portfolio_return, drawdown, turnover, costs, weights_json, tradable_json
)
VALUES (
    1, '2024-01-01', 100.0, 0.0, 0.0, 0.0, 0.0,
    '{"1": 0.5, "2": 0.5}', '{"1": true, "2": true}'
);
```

---

### `backtest_instrument_series`

**Description** : Série temporelle par instrument (base100).

**Colonnes** :

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `run_id` | `INTEGER` | NO | FK → `backtest_runs.id` |
| `instrument_id` | `INTEGER` | NO | FK → `market_data_instruments.id` |
| `date` | `DATE` | NO | Date du bar |
| `base100` | `NUMERIC(20, 8)` | NO | Prix base100 |
| `instrument_return` | `NUMERIC(20, 8)` | YES | Return instrument (open-to-open) |

**Index** :
- `PRIMARY KEY (run_id, instrument_id, date)`
- `INDEX (run_id)`
- `INDEX (instrument_id)`
- `INDEX (date)`
- `UNIQUE (run_id, instrument_id, date)`

**Contraintes** :
- `FOREIGN KEY (run_id) REFERENCES backtest_runs(id)`
- `FOREIGN KEY (instrument_id) REFERENCES market_data_instruments(id)`
- `UNIQUE (run_id, instrument_id, date)`

**Exemple** :
```sql
INSERT INTO backtest_instrument_series (
    run_id, instrument_id, date, base100, instrument_return
)
VALUES (1, 1, '2024-01-01', 100.0, 0.0);
```

---

### `backtest_metrics`

**Description** : Métriques calculées (portfolio + instruments).

**Colonnes** :

| Colonne | Type | Nullable | Description |
|---------|------|----------|-------------|
| `id` | `INTEGER` | NO | PK, auto-increment (serial) |
| `run_id` | `INTEGER` | NO | FK → `backtest_runs.id` |
| `scope` | `VARCHAR(20)` | NO | "portfolio" ou "instrument" |
| `instrument_id` | `INTEGER` | YES | FK → `market_data_instruments.id` (NULL pour portfolio) |
| `key` | `VARCHAR(50)` | NO | Nom métrique (ex: "cagr", "sharpe") |
| `value` | `NUMERIC(20, 8)` | NO | Valeur métrique |

**Index** :
- `PRIMARY KEY (id)`
- `INDEX (run_id)`
- `INDEX (instrument_id)`
- `UNIQUE (run_id, scope, instrument_id, key)`

**Contraintes** :
- `FOREIGN KEY (run_id) REFERENCES backtest_runs(id)`
- `FOREIGN KEY (instrument_id) REFERENCES market_data_instruments(id)` (nullable)
- `UNIQUE (run_id, scope, instrument_id, key)`

**Métriques portfolio** : `scope="portfolio"`, `instrument_id=NULL`

**Métriques instrument** : `scope="instrument"`, `instrument_id=<id>`

**Keys possibles** :
- `cagr` : Compound Annual Growth Rate
- `volatility` : Volatilité annualisée
- `sharpe` : Ratio Sharpe (rf=0)
- `max_drawdown` : Drawdown maximum (négatif)
- `calmar` : Ratio Calmar
- `mean_daily_return` : Moyenne returns quotidiens
- `variance_daily_return` : Variance returns quotidiens

**Exemple** :
```sql
-- Portfolio metric
INSERT INTO backtest_metrics (run_id, scope, instrument_id, key, value)
VALUES (1, 'portfolio', NULL, 'cagr', 0.15);

-- Instrument metric
INSERT INTO backtest_metrics (run_id, scope, instrument_id, key, value)
VALUES (1, 'instrument', 1, 'cagr', 0.20);
```

**Pourquoi `instrument_id` nullable ?**

**Raison** : Métriques portfolio n'ont pas d'instrument associé.

**Structure** :
- **Portfolio** : `scope="portfolio"`, `instrument_id=NULL`
- **Instrument** : `scope="instrument"`, `instrument_id=<id>`

**Unique constraint** : Permet `instrument_id=NULL` pour portfolio (PostgreSQL).

---

## Relations entre tables

```
market_data_instruments (1) ──< (N) market_data_bars_d1

backtest_runs (1) ──< (N) backtest_portfolio_series
backtest_runs (1) ──< (N) backtest_instrument_series
backtest_runs (1) ──< (N) backtest_metrics

market_data_instruments (1) ──< (N) backtest_instrument_series
market_data_instruments (1) ──< (N) backtest_metrics (nullable)
```

---

## Pourquoi pas de FK vers `admin_users` ?

**Raison** : Base `arquantix_quant` isolée de la base principale.

**Solution** :
- `created_by_user_id` : `INTEGER` nullable (pas de FK)
- `created_by_email` : `VARCHAR(255)` nullable (pour traçabilité)

**Avantage** : Quant DB peut fonctionner indépendamment de la base admin.

---

## Alembic Migrations

**Emplacement** : `api/alembic/versions/`

**Migrations Market Data & Backtest** :
- Création tables `market_data_instruments`, `market_data_bars_d1`
- Création tables `backtest_runs`, `backtest_portfolio_series`, `backtest_instrument_series`, `backtest_metrics`
- Suppression FK `backtest_runs.created_by_user_id` → `admin_users.id`
- Ajout colonne `backtest_runs.created_by_email`
- Modification `backtest_metrics` : `id` PK, `instrument_id` nullable

**Commande** :
```bash
cd api
alembic upgrade head
```

---

## Exemples de requêtes

### Instruments actifs
```sql
SELECT * FROM market_data_instruments WHERE is_active = 'true';
```

### Bars manquants
```sql
SELECT i.id, i.symbol, COUNT(b.instrument_id) as bars_count
FROM market_data_instruments i
LEFT JOIN market_data_bars_d1 b ON i.id = b.instrument_id
WHERE i.is_active = 'true'
GROUP BY i.id, i.symbol
HAVING COUNT(b.instrument_id) = 0;
```

### Backtest runs récents
```sql
SELECT id, name, status, created_at, start_date, end_date
FROM backtest_runs
ORDER BY created_at DESC
LIMIT 10;
```

### Métriques portfolio
```sql
SELECT key, value
FROM backtest_metrics
WHERE run_id = 1 AND scope = 'portfolio' AND instrument_id IS NULL;
```

### Série portfolio
```sql
SELECT date, nav_base100, portfolio_return, drawdown, turnover, costs
FROM backtest_portfolio_series
WHERE run_id = 1
ORDER BY date ASC;
```

---

## Documents associés

- [Overview](./MARKET_DATA_AND_BACKTEST_OVERVIEW.md)
- [Market Data Architecture](./MARKET_DATA_ARCHITECTURE.md)
- [Backtest Engine Architecture](./BACKTEST_ENGINE_ARCHITECTURE.md)
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)






