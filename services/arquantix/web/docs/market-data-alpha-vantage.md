# Market Data - Alpha Vantage Integration

Documentation du module Market Data intégrant Alpha Vantage API pour récupérer des données de marché (equity, ETF, crypto).

## 📋 Vue d'ensemble

Le module Market Data permet de :
- Stocker des instruments (symboles) avec métadonnées (asset class, weekend tradable, etc.)
- Récupérer des données historiques depuis Alpha Vantage (D1 bars)
- Mettre à jour quotidiennement les données pour tous les instruments actifs
- Backfill historique pour un instrument donné
- Convention D1 "open-to-open" : chaque bar représente une journée de trading

## 🔧 Configuration

### Variables d'environnement

**Backend** (`api/.env`) :
```bash
# Market Data
ALPHAVANTAGE_API_KEY=your-api-key-here
MARKET_DATA_PROVIDER=alphavantage  # Optionnel, défaut: "alphavantage"
```

**Frontend** : Pas nécessaire (API key jamais exposée, appels via proxy Next.js)

**Source** : `api/services/market_data/config.py`

### Obtention d'une clé API Alpha Vantage

1. Créer un compte sur https://www.alphavantage.co/support/#api-key
2. Copier la clé API (format: `ABC123XYZ...`)
3. Ajouter dans `api/.env` : `ALPHAVANTAGE_API_KEY=ABC123XYZ...`

**Limites** :
- **Free tier** : 5 appels par minute, 500 appels par jour
- **Premium tier** : 75 appels par minute, illimité par jour

**Source** : Documentation Alpha Vantage

## 📊 Modèle de données

### Instruments (`market_data_instruments`)

Chaque instrument représente un symbole tradable :

- `id` : ID unique (auto-increment)
- `symbol` : Symbole (ex: "SPY", "BTC", "ETH")
- `name` : Nom complet (ex: "SPDR S&P 500 ETF")
- `asset_class` : "equity", "etf", ou "crypto"
- `weekend_tradable` : `true` si tradable le weekend (crypto), `false` sinon
- `provider` : "alphavantage" (par défaut)
- `provider_symbol` : Symbole utilisé par Alpha Vantage (peut différer de `symbol`)
- `is_active` : `true` si actif (inclus dans update quotidien), `false` sinon
- `created_at` : Date de création

### Bars D1 (`market_data_bars_d1`)

Chaque bar représente une journée de trading (convention "open-to-open") :

- `instrument_id` : FK vers `market_data_instruments.id`
- `date` : Date du bar (YYYY-MM-DD)
- `open` : Prix d'ouverture
- `high` : Prix maximum
- `low` : Prix minimum
- `close` : Prix de clôture
- `volume` : Volume échangé
- `source` : "alphavantage" (par défaut)
- `created_at` : Date d'insertion

**Clé primaire** : `(instrument_id, date)` (unique constraint)

**Source** : `api/database.py` lignes 196-228

## 🚀 Endpoints API

### Backend FastAPI

Tous les endpoints sont protégés par `Depends(get_current_user)` (JWT Bearer Token).

#### GET `/api/market-data/instruments`

Liste tous les instruments.

**Query Parameters** :
- `is_active` (boolean, optional) : Filtrer par statut actif
- `asset_class` (string, optional) : Filtrer par classe d'actif ("equity", "etf", "crypto")

**Response** :
```json
[
  {
    "id": 1,
    "symbol": "SPY",
    "name": "SPDR S&P 500 ETF",
    "asset_class": "etf",
    "weekend_tradable": false,
    "provider": "alphavantage",
    "provider_symbol": "SPY",
    "is_active": true,
    "created_at": "2026-01-09T12:00:00Z"
  },
  ...
]
```

**Source** : `api/services/market_data/routes.py` lignes 48-82

#### POST `/api/market-data/instruments/seed`

Seed les instruments du univers CORE_V1.

**Request** :
```json
{
  "universe": "CORE_V1"
}
```

**CORE_V1** : SPY, QQQ, DIA, ACWI, GLD, BTC, ETH, SOL, BNB, XRP

**Response** : Liste des instruments créés (même format que GET `/instruments`)

**Source** : `api/services/market_data/routes.py` lignes 85-130

#### POST `/api/market-data/instruments/{instrument_id}/backfill`

Backfill historique pour un instrument.

**Request** :
```json
{
  "start_date": "2020-01-01",
  "end_date": "2024-12-31"
}
```

**Response** :
```json
{
  "ok": true,
  "instrument_id": 1,
  "symbol": "SPY",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "bars_inserted": 1250,
  "bars_updated": 0,
  "total_bars": 1250
}
```

**Note** : Utilise `outputsize="full"` pour récupérer toutes les données historiques disponibles (20+ ans pour equity/ETF).

**Source** : `api/services/market_data/routes.py` lignes 133-220

#### POST `/api/market-data/update-daily`

Met à jour quotidiennement tous les instruments actifs.

Fetches latest data (compact = last 100 days) et met à jour/insère les bars pour aujourd'hui et hier uniquement.

**Response** :
```json
{
  "ok": true,
  "total_instruments": 10,
  "results": [
    {
      "symbol": "SPY",
      "updated": 2,
      "status": "success"
    },
    ...
  ]
}
```

**Source** : `api/services/market_data/routes.py` lignes 223-300

#### GET `/api/market-data/instruments/{instrument_id}/bars`

Récupère les bars D1 pour un instrument dans une plage de dates.

**Query Parameters** :
- `start` (required) : Date de début (YYYY-MM-DD)
- `end` (required) : Date de fin (YYYY-MM-DD)

**Response** :
```json
{
  "symbol": "SPY",
  "bars": [
    {
      "date": "2024-01-01T00:00:00Z",
      "open": "450.25",
      "high": "452.10",
      "low": "449.80",
      "close": "451.50",
      "volume": 50000000,
      "source": "alphavantage"
    },
    ...
  ],
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T00:00:00Z",
  "count": 252
}
```

**Source** : `api/services/market_data/routes.py` lignes 303-350

#### GET `/api/market-data/instruments/{instrument_id}/quote`

Récupère la dernière cotation pour un instrument.

**Response** :
```json
{
  "symbol": "SPY",
  "latest_price": "451.50",
  "latest_date": "2024-12-31T00:00:00Z",
  "change": "1.25",
  "change_percent": "0.28"
}
```

**Note** : Pour equity/ETF, utilise `GLOBAL_QUOTE`. Pour crypto, utilise le dernier bar de la base de données.

**Source** : `api/services/market_data/routes.py` lignes 353-420

### Frontend Next.js (Proxy Routes)

Toutes les routes proxy suivent le pattern :
1. Vérification session cookie (`getSessionFromCookie()`)
2. Création JWT depuis session
3. Proxy vers FastAPI avec `Authorization: Bearer <JWT>`

**Routes disponibles** :
- `GET /api/market-data/instruments` → Proxy vers `GET /api/market-data/instruments`
- `POST /api/market-data/seed` → Proxy vers `POST /api/market-data/instruments/seed`
- `POST /api/market-data/backfill` → Proxy vers `POST /api/market-data/instruments/{id}/backfill`
- `POST /api/market-data/update-daily` → Proxy vers `POST /api/market-data/update-daily`
- `GET /api/market-data/bars` → Proxy vers `GET /api/market-data/instruments/{id}/bars`

**Source** : `web/src/app/api/market-data/`

## 🔄 Convention D1 "Open-to-Open"

**Définition** : Chaque bar D1 représente une journée de trading complète, de l'ouverture à la clôture.

**Exemple** :
- Bar du 2024-01-02 : représente la journée du 2 janvier 2024
  - `open` : Prix à l'ouverture du 2 janvier
  - `close` : Prix à la clôture du 2 janvier
  - `high` / `low` : Max/min de la journée

**Weekend Trading** :
- **Equity/ETF** : `weekend_tradable=false` → Pas de bars le samedi/dimanche
- **Crypto** : `weekend_tradable=true` → Bars 7j/7 (même le weekend)

**Source** : Convention standard de trading

## ⚠️ Limites Alpha Vantage

### Rate Limits

- **Free tier** : 5 appels par minute, 500 appels par jour
- **Premium tier** : 75 appels par minute, illimité par jour

**Gestion** : Le client Alpha Vantage (`api/services/market_data/client.py`) implémente un rate limiter simple :
- Limite : 4 appels par minute (pour être sûr avec free tier)
- Attente automatique si limite atteinte

**Source** : `api/services/market_data/client.py` lignes 12-30

### Erreurs Communes

1. **"API call frequency is 5 calls per minute"** : Rate limit atteint
   - **Solution** : Attendre 1 minute ou upgrade vers premium

2. **"Invalid API call"** : Symbole invalide ou fonction incorrecte
   - **Solution** : Vérifier le symbole et l'asset_class

3. **"Thank you for using Alpha Vantage!"** : Rate limit quotidien atteint (free tier)
   - **Solution** : Attendre le lendemain ou upgrade vers premium

**Source** : `api/services/market_data/client.py` lignes 50-60

## 📝 Workflow Recommandé

### 1. Seed Instruments

```bash
# Via API
POST /api/market-data/instruments/seed
{ "universe": "CORE_V1" }
```

Créé les 10 instruments du univers CORE_V1.

### 2. Backfill Historique

```bash
# Pour chaque instrument
POST /api/market-data/instruments/{id}/backfill
{
  "start_date": "2020-01-01",
  "end_date": "2024-12-31"
}
```

**Note** : Avec free tier, le backfill peut prendre du temps (rate limit 5/min). Recommandé d'utiliser premium tier pour backfill massif.

### 3. Update Quotidien

```bash
# Une fois par jour (via cron ou ECS scheduled task)
POST /api/market-data/update-daily
```

Met à jour tous les instruments actifs (aujourd'hui + hier).

### 4. Récupérer Bars

```bash
# Pour backtest ou analyse
GET /api/market-data/instruments/{id}/bars?start=2024-01-01&end=2024-12-31
```

## 🔐 Sécurité

- **API Key** : Jamais exposée au frontend (uniquement backend)
- **Auth** : Tous les endpoints protégés par JWT (`Depends(get_current_user)`)
- **Proxy** : Frontend utilise proxy Next.js (jamais appels directs depuis client)

**Source** : Pattern identique à Email Builder (`api/services/ai_email/routes.py`)

## 🐛 Troubleshooting

### "ALPHAVANTAGE_API_KEY not configured"

**Cause** : Variable d'environnement manquante

**Solution** :
1. Vérifier `api/.env` contient `ALPHAVANTAGE_API_KEY=...`
2. Redémarrer le serveur FastAPI

### "Rate limit exceeded"

**Cause** : Trop d'appels API récents

**Solution** :
1. Attendre 1 minute (free tier)
2. Vérifier le rate limiter dans `client.py`
3. Upgrade vers premium tier si nécessaire

### "Instrument not found"

**Cause** : Instrument non seedé ou ID incorrect

**Solution** :
1. Vérifier que l'instrument existe : `GET /api/market-data/instruments`
2. Seed si nécessaire : `POST /api/market-data/instruments/seed`

## 📚 Références

- **Alpha Vantage API Docs** : https://www.alphavantage.co/documentation/
- **Module Email Builder** : `api/services/ai_email/` (pattern de référence)
- **Audit Architecture** : `AUDIT_ARCHITECTURE_MARKET_DATA_BACKTEST.md`

---

**Dernière mise à jour** : 2026-01-09






