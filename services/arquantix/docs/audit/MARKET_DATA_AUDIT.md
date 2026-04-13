# Audit Market Data – Module crypto / wealth

**Date :** 2026-02-18  
**Périmètre :** Backend Arquantix (FastAPI), base PostgreSQL, intégration données de marché (cible : Binance, temps réel + OHLC).  
**Objectif :** Audit du code existant et plan d’implémentation pour un module market data V1 (sans implémenter de code).

---

## 1. Executive summary

Le backend Arquantix dispose **déjà d’un domaine market data** centré sur **Yahoo Finance** : instruments, barres D1 (OHLC), ingestion par script, et API REST protégée (JWT). Il n’y a **pas** d’intégration Binance, **pas** de WebSocket (ni ingestion ni diffusion), **pas** de stockage de « dernier prix » (quotes) en base, **pas** de Redis ni de workers/schedulers dédiés. Une extension vers Binance, flux temps réel et push WebSocket vers le frontend est **faisable** en s’appuyant sur la structure actuelle (instruments, barres D1, config, repositories) et en ajoutant : tables « latest quote » et éventuellement OHLC multi-granularité, client Binance (REST + WebSocket), endpoint WebSocket de diffusion, et un mécanisme d’ingestion en arrière-plan (process séparé ou tâche périodique dans l’app). Un **GO** conditionnel est recommandé : démarrer l’implémentation en suivant le plan proposé, sans refactor global.

---

## 2. Project structure audit

### 2.1 Structure FastAPI

- **Point d’entrée :** `api/main.py` — `create_app(testing=False)` construit l’application, enregistre les routers, CORS, health, exception handler.
- **Pas de dossier `routers/` à la racine de l’API.** Les routes sont dans **`api/services/<domaine>/routes.py`** (ex. `services/bundles/routes.py`, `services/market_data/routes.py`, `services/backtest/routes.py`, etc.).
- **Routers inclus dans `main.py` :** bundles, diagnostics, **market_data**, backtest, ai_email, ai_jurisdiction_configs, persons, jurisdiction_configs, onboarding, aml_risk, field_definitions, finance_strategy_chat, chatbot_epargne, migrations.

### 2.2 Services / modules / core / utils

- **Services :** `api/services/<domaine>/` avec typiquement `routes.py`, parfois `config.py`, clients, repos, engines (ex. `services/market_data/`, `services/backtest/`, `services/aml_risk/`).
- **Core :** `api/core/` — contient `env.py` (chargement dotenv, `is_dev_mode()`, `get_env_info()`). Pas de Pydantic BaseSettings central ; la config est surtout `os.getenv()` (ex. `api/services/market_data/config.py`).
- **Pas de couche « utils » dédiée market data** ; helpers dans les modules concernés.

### 2.3 WebSocket

- **Aucun WebSocket** dans l’API actuelle. Aucune route `@app.websocket` ni dépendance type `websockets`. À ajouter pour la diffusion des prix vers Flutter / Web.

### 2.4 DB et migrations

- **ORM :** SQLAlchemy (déclarative), `api/database.py` : `engine`, `SessionLocal`, `Base`, modèles (dont `MarketDataInstrument`, `MarketDataBarD1`, etc.).
- **Migrations :** Alembic, répertoire `api/alembic/`, `env.py` charge la config depuis l’env. Migrations market data : ex. `dd7124eabc4d_add_market_data_tables.py` (instruments + bars_d1).
- **Pas de SQL brut** pour le domaine market data ; tout passe par les modèles et repos.

### 2.5 Config / settings

- **Chargement env :** `database.py` et `core/env.py` chargent `.env.local` puis `.env` via `dotenv`. Pas de Pydantic Settings global.
- **Market data :** `api/services/market_data/config.py` — `MARKET_DATA_PROVIDER`, `ALPHAVANTAGE_API_KEY` (déprécié, non utilisé).

### 2.6 Background jobs / workers / schedulers

- **Aucun** Celery, APScheduler, ou worker dédié. L’ingestion D1 est faite **manuellement** via script : `api/scripts/load_market_data.py` (Yahoo, barres D1).

### 2.7 Redis

- **Absent** du projet. Une mention dans `api/services/finance_strategy_chat/store.py` indique que le store est conçu pour être remplaçable par Redis plus tard ; aucun usage actuel.

### 2.8 Docker / compose / infra

- **Compose :** à la racine du repo (vancelian-app) : `docker-compose.arquantix.yml` — services PostgreSQL, CMS Strapi, Next.js. **Pas** de service API FastAPI ni Redis dans le fichier lu.
- **Docker :** `services/arquantix/cms/docker-entrypoint.sh` ; pas de Dockerfile API repéré dans la recherche.

### 2.9 Tests

- **Structure :** `api/tests/` — `conftest.py`, nombreux `test_*.py` (bundles, backtest, aml_risk, onboarding, chatbot, jurisdiction_configs, etc.).
- **Market data :** un test dédié : `api/tests/test_yahoo_ingest_smart_update.py`. Aucun test pour les routes market_data (list instruments, bars, etc.).

---

## 3. Data architecture audit

### 3.1 Concepts marché / actifs / instruments

- **Présents.** Modèle `MarketDataInstrument` dans `api/database.py` : `id`, `symbol`, `name`, `asset_class`, `weekend_tradable`, `provider`, `provider_symbol`, `is_active`, `created_at`. Table `market_data_instruments` (schéma `public`).
- **CORE_V1_INSTRUMENTS** en dur dans `api/services/market_data/routes.py` (BTC, ETH, SOL, URTH, QQQ, DIA, GLD) — liste de référence, pas une table.

### 3.2 Tables prix / historiques

- **Barres D1 :** table `market_data_bars_d1` — `(instrument_id, date)` PK, `open`, `high`, `low`, `close`, `volume`, `source`, `created_at`. Une seule granularité (daily).
- **Pas de table** pour « dernier prix » / quote temps réel. Pas de table OHLC 1m/5m/15m/1h.

### 3.3 Intégration exchange

- **Yahoo Finance** : implémentée (`yahoo_client.py`, `yahoo_html_parser.py`, `ingest_service.py`, `load_market_data.py`).
- **Alpha Vantage** : client présent dans `api/services/market_data/client.py` (ex. `get_latest_quote_equity`) ; config marquée dépréciée, non utilisée dans les routes (filtre `provider == "yahoo"`).
- **Binance :** **aucune** intégration dans le codebase.

### 3.4 Couche de normalisation des symboles

- **Partielle.** `MarketDataInstrument` a `symbol` (interne) et `provider_symbol` (ex. Yahoo). Pas de couche explicite « exchange → symbol interne » pour Binance (ex. BTCUSDT → instrument_id / symbol).

### 3.5 WebSocket / pub-sub

- **Aucun** broadcaster WebSocket ni mécanisme pub/sub (Redis ou autre) pour pousser les prix vers les clients.

---

## 4. Integration points (recommandations)

- **Où placer le nouveau code :** dans le module existant `api/services/market_data/` : nouveaux fichiers (ex. `binance_client.py`, `quotes_repo.py`, `ws_broadcast.py`) et éventuellement sous-dossiers si le module grossit (ex. `providers/binance.py`). Éviter de créer un second module « market_data_v2 » pour limiter la duplication.
- **Pattern :** conserver **router + service + repository** : routes dans `routes.py` (ou un fichier dédié `routes_ws.py`), logique métier dans des services, accès DB dans des repos (ex. `bars_d1_repo.py` déjà présent, nouveau `quotes_repo.py` pour latest).
- **Ingestion worker :** pour V1, soit un **process séparé** (script ou petit worker qui tourne en parallèle de l’API) qui lit Binance (REST ou WS), écrit en base (et optionnellement en Redis en V2), soit une **tâche périodique** dans l’app (startup + asyncio loop ou thread) si on veut tout dans le même process. Éviter de bloquer les requêtes HTTP.
- **WebSocket :** l’app FastAPI peut **héberger** l’endpoint WebSocket de diffusion (même process) : les clients se connectent à `/ws/market-data` (ou similaire), un service lit les dernières valeurs (DB ou Redis) et les envoie toutes les 1–2 s. Pas obligatoire de séparer un service WebSocket dédié pour V1.
- **Postgres seul pour V1 :** suffisant pour stocker latest quote (table dédiée) + OHLC existant. Redis peut rester **optionnel** en V1 et être préparé en V2 (ex. clé `market:quote:{symbol}` pour réduire la charge DB sur le path temps réel).

---

## 5. Risks and blockers

- **Incohérences :** `is_active` / `weekend_tradable` stockés en chaîne `"true"`/`"false"` dans la DB ; à garder en tête pour les requêtes et la cohérence avec un éventuel typage strict côté API.
- **Dépendances :** pas de `websockets` ni de client Binance dans les fichiers vus ; à ajouter (ex. `binance-connector` ou `ccxt`, ou requêtes HTTP/WS manuelles).
- **Organisation :** le module market_data mélange routes, schémas Pydantic, et constante CORE_V1 dans le même fichier ; acceptable pour V1, à scinder si le fichier grossit (schemas dans `schemas.py`, constantes dans `constants.py` ou config).
- **Performance :** pas de cache pour les lectures « dernier prix » ; si le WebSocket lit en DB à chaque tick, une table dédiée « latest_quote » avec un row par instrument (ou par symbole) limite les jointures. En V2, Redis devant Postgres réduira la charge.
- **Migrations :** ajout de tables (quotes, éventuellement OHLC 1m/5m) via Alembic ; pas de risque identifié si on reste sur le même schéma `public` et les mêmes conventions de nommage.
- **Collisions de noms :** préfixer les nouvelles tables (ex. `market_data_latest_quotes`) et routes (ex. `/api/market-data/...`) pour éviter les conflits avec les routes existantes.
- **Anti-patterns :** éviter de mettre la logique Binance ou WebSocket directement dans `main.py` ; garder tout dans `services/market_data/` pour maintenabilité.

---

## 6. Reusable existing components

- **Modèles :** `MarketDataInstrument`, `MarketDataBarD1` — réutilisables ; étendre avec `provider = "binance"` et `provider_symbol` (ex. BTCUSDT).
- **Repos :** `api/services/market_data/bars_d1_repo.py` — `get_bars_d1`, `get_close_matrix`, etc. ; à réutiliser pour l’historique OHLC.
- **Ingestion :** `ingest_service.py` (analyse conflits, upsert barres) — pattern réutilisable pour l’ingestion OHLC Binance (avec adaptation source/format).
- **Routes :** `GET/POST /api/market-data/instruments`, `GET /api/market-data/instruments/{id}/bars` — à compléter par des endpoints « latest » et un WebSocket, sans casser les existants.
- **Config :** `config.py` — ajouter `BINANCE_BASE_URL`, `BINANCE_WS_URL`, etc.
- **Script :** `load_market_data.py` — référence pour un futur script ou worker d’ingestion Binance (D1 ou multi-timeframe).

---

## 7. Missing components (à créer pour la cible V1)

- **Client Binance :** REST (dernier prix, klines) + optionnellement WebSocket (stream prix) pour alimenter la couche ingestion / quotes.
- **Table « latest quote » :** stocker dernier prix (et optionnellement volume, timestamp) par instrument ou par symbole.
- **Couche normalisation symboles :** mapping Binance (ex. BTCUSDT) ↔ `MarketDataInstrument.id` ou `symbol` interne.
- **Endpoint(s) REST :** ex. `GET /api/market-data/quotes/latest?symbols=BTC,ETH` ou par `instrument_id`.
- **Endpoint WebSocket :** ex. `WS /ws/market-data` ou `/api/market-data/ws` avec push toutes les 1–2 s (liste de symboles en query ou en message).
- **Mécanisme d’ingestion temps réel :** process ou tâche en arrière-plan qui met à jour la table latest quote (et optionnellement OHLC court terme) à partir de Binance.
- **Tests :** au moins tests unitaires pour le client Binance et les nouveaux endpoints (quotes, WS si possible).

---

## 8. Recommendations

1. **Ne pas refactorer** l’existant (Yahoo, D1) ; ajouter Binance et le flux temps réel à côté.
2. **Introduire une table dédiée** pour les derniers prix (ex. `market_data_latest_quotes`) plutôt que de dériver du dernier bar D1.
3. **Centraliser la config** Binance dans `api/services/market_data/config.py` (ou `core` si partagé).
4. **Documenter** le format des messages WebSocket (JSON avec symbol, price, timestamp) pour les clients Flutter / Web.
5. **Prévoir** en V2 : Redis pour le cache quotes, OHLC multi-granularité (1m, 5m, 1h), et éventuellement séparation de l’ingestion dans un worker dédié.

---

*Document généré dans le cadre de l’audit market data – pas de modification du code métier.*
