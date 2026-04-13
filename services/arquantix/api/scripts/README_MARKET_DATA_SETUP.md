# Market Data – Mise en place pour Flutter Markets

Ce guide permet d’avoir des données réelles pour l’écran Markets (market-summary, top-movers, WebSocket).

## Pourquoi les quotes ne bougent plus (market-summary toujours pareil)

L'API **market-summary** lit le **prix** dans la table `market_data_latest_quotes`. Cette table est mise à jour par :
- le worker **Binance WebSocket** (temps réel) : `python3 scripts/run_binance_ws_ingestion.py`
- **fallback automatique** : si la quote est absente ou plus vieille que 60 secondes, l’API appelle Binance REST et met à jour la base. Donc même sans le worker, un appel à `market-summary?symbols=BTCUSDT` renvoie un prix à jour (au coût d’une requête REST par symbole périmé).

Pour des mises à jour continues (sans latence 60s), laisser le worker WebSocket tourner :

```bash
cd api
python3 scripts/run_binance_ws_ingestion.py
```

## 1. Tables obligatoires

Les routes `market-summary` et `top-movers` utilisent :

- `market_data_instruments`
- `market_data_latest_quotes`
- `market_data_bars_5m` (pour les variations 24h et les sparklines ; peut être vide)

Si les tables `latest_quotes` ou `bars_5m` manquent (migrations non appliquées) :

```bash
cd api
python3 scripts/create_market_data_latest_quotes_if_missing.py
```

## 2. Instruments Binance

Créer les instruments avec `provider=binance` et `provider_symbol` (ex. BTCUSDT) :

```bash
cd api
python3 -m scripts.ensure_binance_instruments
```

## 3. Quotes (dernier prix)

Une fois les instruments et la table `market_data_latest_quotes` en place, lancer **une** des options suivantes.

### Option A : une fois (REST)

```bash
cd api
python3 scripts/run_binance_ingestion.py
```

### Option B : en continu (WebSocket Binance → DB)

```bash
cd api
python3 scripts/run_binance_ws_ingestion.py
```

Après ça, **market-summary** et le **WebSocket Flutter** (`/ws/market-data`) ont des données à jour.

## 4. (Optionnel) Candles 5m – variations 24h et sparklines

Sans barres 5m, l’API renvoie quand même le **prix** mais `change_24h_pct` et `sparkline_24h` sont vides. Pour avoir les variations et les mini-courbes :

```bash
cd api
python3 scripts/run_candles_5m_ingestion.py
```

À lancer périodiquement (cron ou en arrière-plan) pour alimenter les 24h.

**Page détail actif (graphique 1j / 1s) :** si l’app affiche « Aucune donnée pour cette période » ou « Service temporairement indisponible », lancer en plus l’ingestion 1h :  
`python3 scripts/run_candles_1h_ingestion.py --limit 300`. Le script `create_market_data_latest_quotes_if_missing.py` crée aussi la table `market_data_bars_1h` si elle manque.

**Graphique 1 mois (chandeliers H4) :** la période « 1m » utilise les barres 4h (`/api/market-data/candles/4h`). Pour remplir ou mettre à jour :

```bash
cd api
python3 scripts/run_candles_backfill.py --timeframe 4h
```

Ou une ingestion ponctuelle : `python3 scripts/run_candles_4h_ingestion.py --limit 500`. Dans l’app, utiliser « Rafraîchir » sur le graphique pour recharger les données.

## 5. Vérifications rapides

- Market-summary :  
  `http://127.0.0.1:8000/api/market-data/market-summary?symbols=BTCUSDT,ETHUSDT`
- Top-movers :  
  `http://127.0.0.1:8000/api/market-data/top-movers?limit=5`
- Flutter : backend sur **8000**, config par défaut → `http://127.0.0.1:8000` (iOS simulateur).

**Si l’app Flutter affiche « Impossible de joindre l’API »** alors que le navigateur atteint `localhost:8000/health`, démarrer l’API en écoutant sur toutes les interfaces :  
`python3 -m uvicorn main:app --reload --port 8000 --host 0.0.0.0`

## Résumé exécuté pour toi

- Script `ensure_binance_instruments.py` créé et exécuté (11 instruments).
- Correction import `List` dans `binance_client.py`.
- Table `market_data_latest_quotes` créée (script `create_market_data_latest_quotes_if_missing.py`), puis table `market_data_bars_5m` ajoutée au même script.
- Un cycle `run_binance_ingestion.py` exécuté → 11 quotes à jour.
- market-summary et top-movers répondent correctement.

Pour avoir **Top Gainers / Top Losers** remplis, il faut des `change_24h_pct` calculés → lancer l’ingestion 5m (étape 4) et la laisser tourner un peu.
