# Plan d’implémentation – Module Market Data V1 (Binance + WebSocket)

**Référence :** `docs/audit/MARKET_DATA_AUDIT.md`  
**Objectif :** Définir l’architecture cible, les fichiers à créer/modifier, les migrations et l’ordre d’implémentation pour la V1 (Binance, latest quotes, OHLC, push WebSocket 1–2 s). Aucun code à implémenter dans le cadre de ce document.

---

## 1. Target architecture V1

### 1.1 Vue d’ensemble

- **Source de données :** Binance (REST + WebSocket) pour crypto ; Yahoo inchangé pour D1 / non-crypto.
- **Stockage :** PostgreSQL uniquement (V1).
  - **Instruments :** table existante `market_data_instruments` ; ajout d’instruments avec `provider = "binance"` et `provider_symbol` (ex. BTCUSDT).
  - **Derniers prix :** nouvelle table `market_data_latest_quotes` (un enregistrement par instrument, mis à jour par l’ingestion).
  - **OHLC :** barres D1 existantes `market_data_bars_d1` ; optionnel en V1 : table `market_data_bars_*` pour une autre granularité (ex. 1h) si besoin pour les graphiques.
- **Ingestion :** Process ou tâche en arrière-plan (hors requêtes HTTP) qui :
  - lit les flux Binance (REST pour snapshot, WebSocket pour stream),
  - met à jour `market_data_latest_quotes`,
  - peut alimenter les barres D1 (ou autre) pour les symboles Binance.
- **API :**
  - REST : `GET /api/market-data/quotes/latest` (liste de symboles ou instrument_ids), `GET /api/market-data/instruments/{id}/bars` (existant), éventuellement `GET /api/market-data/klines` pour OHLC multi-timeframe si introduit.
  - WebSocket : un seul endpoint, ex. `WS /ws/market-data` ou `WS /api/market-data/ws`, auquel les clients s’abonnent ; le serveur envoie les derniers prix (depuis la table ou un cache en mémoire) toutes les 1–2 s.
- **Séparation claire :**
  - **Latest quotes** → table dédiée + endpoint REST + payload WebSocket.
  - **OHLC / candlesticks** → tables bars (D1 existant, éventuellement 1h en V1).
  - **Ingestion state** → pas de table dédiée en V1 (optionnel : table `market_data_ingestion_state` en V2 pour last_run, last_symbol, etc.).
  - **Instruments metadata** → table existante `market_data_instruments` ; pas de duplication.

### 1.2 Flux de données

1. **Worker / tâche d’ingestion** (script ou asyncio dans l’app) : connexion au stream Binance (ex. `btcusdt@ticker`), réception des ticks, mapping `symbol Binance → instrument_id`, `UPDATE` ou `INSERT` dans `market_data_latest_quotes`.
2. **REST** : le client appelle `GET /api/market-data/quotes/latest?symbols=BTC,ETH` ; le serveur lit `market_data_latest_quotes` (jointure instruments si besoin) et renvoie JSON.
3. **WebSocket** : le client ouvre `WS /ws/market-data?symbols=BTC,ETH` ; une boucle côté serveur (asyncio) lit périodiquement les dernières quotes (depuis la table ou un cache en mémoire) et envoie un message JSON (ex. `{ "quotes": [ { "symbol": "BTC", "price": "...", "ts": "..." } ] }`) toutes les 1–2 s.

### 1.3 Dépendances à ajouter

- Client HTTP/WebSocket Binance : par ex. `python-binance` ou `binance-connector-python`, ou `ccxt`, ou `websockets` + `aiohttp` pour un client minimal.
- FastAPI supporte WebSocket nativement ; pas de dépendance supplémentaire obligatoire pour le endpoint WS.

---

## 2. Fichiers et dossiers à créer (exacts)

Tous les chemins sont relatifs à la racine du service Arquantix (`services/arquantix/`).

| Fichier / dossier | Rôle |
|-------------------|------|
| `api/services/market_data/binance_client.py` | Client Binance : REST (ticker/klines) + WebSocket (stream ticker) ; normalisation symbol (BTCUSDT ↔ symbol interne). |
| `api/services/market_data/quotes_repo.py` | Repository : lecture/écriture `market_data_latest_quotes` (get by instrument_ids/symbols, upsert). |
| `api/services/market_data/ws_broadcast.py` ou `ws.py` | Logique WebSocket : accepter connexions, gérer la liste de symboles par client, boucle d’envoi périodique (1–2 s) depuis la table ou cache. |
| `api/services/market_data/ingestion_binance.py` ou `ingest_binance.py` | Service d’ingestion : connecter au stream Binance, mapper symbol → instrument_id, appeler `quotes_repo` pour upsert. Peut être lancé comme script ou tâche asyncio. |
| `api/alembic/versions/xxx_add_market_data_latest_quotes.py` | Migration Alembic : création table `market_data_latest_quotes` (colonnes : instrument_id, price, volume optionnel, updated_at, etc.). |
| Optionnel V1 : `api/alembic/versions/xxx_add_market_data_bars_1h.py` | Si besoin d’OHLC 1h pour les graphiques (structure similaire à bars_d1 avec intervalle fixe). |
| `api/scripts/run_binance_ingestion.py` ou intégration dans un `worker.py` | Point d’entrée pour lancer l’ingestion Binance (WebSocket client + écriture en base). |

Fichiers **à ne pas créer** en double : pas de nouveau `routes.py` séparé pour « market_data_v2 » ; étendre `api/services/market_data/routes.py` et, si nécessaire, ajouter un fichier `routes_ws.py` dans le même module et l’enregistrer dans `main.py`.

---

## 3. Fichiers existants à modifier (exacts)

| Fichier | Modifications |
|---------|----------------|
| `api/database.py` | Ajouter le modèle SQLAlchemy `MarketDataLatestQuote` (table `market_data_latest_quotes`) avec relation vers `MarketDataInstrument`. |
| `api/services/market_data/config.py` | Ajouter variables : `BINANCE_BASE_URL`, `BINANCE_WS_URL`, `BINANCE_API_KEY` (optionnel), `BINANCE_API_SECRET` (optionnel), et si besoin `MARKET_DATA_WS_BROADCAST_INTERVAL_SEC`. |
| `api/services/market_data/routes.py` | Ajouter route `GET /api/market-data/quotes/latest` (query params : `symbols` ou `instrument_ids`) ; garder les routes existantes instruments et bars inchangées. Déplacer les schémas Pydantic dans `schemas.py` si le fichier devient lourd. |
| `api/main.py` | Monter l’endpoint WebSocket : soit dans le router market_data (si FastAPI permet d’ajouter une route WS au même router), soit une route `app.websocket("/ws/market-data")` qui délègue à `services.market_data.ws_broadcast`. Démarrer la tâche d’ingestion Binance (asyncio background task) uniquement si une variable d’env l’active (ex. `BINANCE_INGESTION_ENABLED=true`), pour ne pas impacter les déploiements sans Binance. |
| `api/requirements.txt` | Ajouter la dépendance choisie pour Binance (ex. `python-binance` ou `binance-connector-python`) et `websockets` si utilisé explicitement. |

Aucune modification des fichiers Yahoo (`yahoo_client.py`, `yahoo_html_parser.py`, `ingest_service.py`, `bars_d1_repo.py`) **sauf** si on décide de partager une interface commune « provider » en V2.

---

## 4. Modèle de données cible (tables)

### 4.1 Table existante (inchangée)

- **market_data_instruments** : id, symbol, name, asset_class, weekend_tradable, provider, provider_symbol, is_active, created_at.  
  Pour Binance : `provider = 'binance'`, `provider_symbol = 'BTCUSDT'` (ou équivalent).

### 4.2 Nouvelle table : market_data_latest_quotes

- **instrument_id** (PK, FK → market_data_instruments.id)
- **price** (Numeric ou Double)
- **volume** (optionnel, BigInteger ou Null)
- **quote_time** (DateTime with time zone, heure du tick côté exchange)
- **updated_at** (DateTime with time zone, server default now())
- Contrainte unique sur `instrument_id` pour un seul enregistrement par instrument.

### 4.3 Tables OHLC (existantes + optionnel)

- **market_data_bars_d1** : inchangée.
- Optionnel V1 : **market_data_bars_1h** (instrument_id, datetime_utc, open, high, low, close, volume, source) si les graphiques exigent de l’intraday.

---

## 5. Endpoints API cible

### 5.1 REST (à ajouter / existants)

| Méthode | Chemin | Description |
|--------|--------|-------------|
| GET | `/api/market-data/quotes/latest` | Query : `symbols=BTC,ETH` ou `instrument_ids=1,2`. Réponse : liste de { symbol, instrument_id, price, volume?, quote_time, updated_at }. |
| GET | `/api/market-data/instruments` | Existant. Adapter le filtre pour permettre `provider=binance` (ou tous) si besoin. |
| GET | `/api/market-data/instruments/{instrument_id}/bars` | Existant (D1). |

### 5.2 WebSocket

| Type | Chemin | Description |
|------|--------|-------------|
| WS | `/ws/market-data` ou `/api/market-data/ws` | Query ou premier message : liste de symboles (ex. `?symbols=BTC,ETH`). Serveur envoie toutes les 1–2 s un message JSON : `{ "quotes": [ { "symbol", "price", "ts" } ] }`. |

---

## 6. Ordre d’implémentation (séquençage sûr)

1. **Migration + modèle**  
   - Créer la migration Alembic pour `market_data_latest_quotes`.  
   - Ajouter le modèle `MarketDataLatestQuote` dans `database.py`.  
   - Exécuter la migration en dev.

2. **Config**  
   - Étendre `api/services/market_data/config.py` (Binance URLs, clés optionnelles, intervalle WS).

3. **Repository quotes**  
   - Implémenter `quotes_repo.py` (get_latest_quotes, upsert_quote).

4. **Client Binance**  
   - Implémenter `binance_client.py` (REST : dernier prix / klines ; WS : stream ticker). Mapping `provider_symbol` ↔ `instrument_id` via la table instruments.

5. **Ingestion**  
   - Implémenter `ingestion_binance.py` (boucle WebSocket Binance → upsert dans `market_data_latest_quotes`).  
   - Point d’entrée script ou tâche : `run_binance_ingestion.py` ou équivalent.

6. **REST quotes**  
   - Ajouter `GET /api/market-data/quotes/latest` dans `routes.py`, en s’appuyant sur `quotes_repo`.

7. **WebSocket**  
   - Implémenter `ws_broadcast.py` (gestion des connexions, liste symboles par client, boucle d’envoi 1–2 s).  
   - Enregistrer la route WS dans `main.py` (ou dans le router market_data si possible).

8. **Démarrage conditionnel**  
   - Dans `main.py`, au startup, lancer la tâche d’ingestion Binance seulement si `BINANCE_INGESTION_ENABLED=true` (ou équivalent).

9. **Tests**  
   - Tests unitaires : `quotes_repo`, client Binance (mock), endpoint REST quotes.  
   - Test d’intégration WebSocket optionnel (client de test).

10. **Documentation**  
    - Mettre à jour `docs/MARKET_DATA_*.md` ou `docs/audit/` avec les nouveaux endpoints et le format des messages WebSocket.

---

## 7. Améliorations optionnelles V2

- **Redis** : cache des latest quotes (clé par symbole) ; le WebSocket lit Redis au lieu de la DB à chaque broadcast ; réduction de la charge Postgres.
- **OHLC multi-granularité** : tables bars_1m, bars_5m, bars_1h ; ingestion depuis Binance klines.
- **Table d’état d’ingestion** : `market_data_ingestion_state` (provider, symbol, last_run_at, last_error) pour monitoring et reprise.
- **Séparation worker** : déplacer l’ingestion Binance dans un process/container dédié (worker) avec une queue (Redis ou DB) si besoin de scalabilité.
- **Auth sur WebSocket** : authentifier les connexions WS (JWT ou token en query) pour restreindre l’accès aux quotes.
- **Provider abstrait** : interface commune (Yahoo, Binance) pour symbol resolution et fetch, avec implémentations concrètes dans des sous-modules.

---

## 8. Résumé des livrables d’audit

- **Audit détaillé :** `docs/audit/MARKET_DATA_AUDIT.md` (synthèse, constats, réutilisable, manques, risques, recommandations).
- **Plan d’implémentation :** le présent document `docs/audit/MARKET_DATA_IMPLEMENTATION_PLAN.md` (architecture cible, fichiers à créer/modifier, migrations, ordre d’implémentation, V2).

Aucun code n’a été modifié ; seuls les documents d’audit et de plan ont été produits.

---

## 9. Avis GO / NO-GO pour démarrer l’implémentation

**Verdict : GO (conditionnel).**

- **Raisons du GO :** Le domaine market data existant (instruments, barres D1, Yahoo, repos, config) fournit une base solide. Les ajouts (table latest quotes, client Binance, WebSocket, ingestion en arrière-plan) sont délimités et n’imposent pas de refactor global. Le plan d’implémentation est séquencé et réversible (migrations, feature flags possibles).
- **Conditions :** Respecter l’ordre d’implémentation proposé ; ne pas modifier les routes et modèles Yahoo/D1 existants sauf nécessité explicite ; activer l’ingestion Binance uniquement via variable d’environnement pour éviter les effets de bord en production.
- **NO-GO serait justifié si :** le projet décidait de ne pas toucher à la base de données (pas de nouvelle table), de ne pas exposer de WebSocket, ou de reporter toute intégration Binance ; dans ce cas, le plan reste utilisable plus tard.
