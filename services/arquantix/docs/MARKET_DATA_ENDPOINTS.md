# Market Data API Endpoints

**Source de vérité pour les endpoints Market Data**

## Endpoints Disponibles

### 1. GET `/api/market-data/instruments`

Liste tous les instruments de market data.

**Query Parameters:**
- `is_active` (optional, bool): Filtrer par statut actif (default: true)
- `asset_class` (optional, str): Filtrer par classe d'actif (equity, etf, crypto, commodities)
- `provider` (optional, str): Filtrer par provider (ex: "yahoo")
- `has_bars` (optional, bool): Filtrer aux instruments ayant au moins un bar (default: None)

**Exemple:**
```bash
curl -X GET "http://localhost:8000/api/market-data/instruments?provider=yahoo&has_bars=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Réponse:**
```json
[
  {
    "id": 1,
    "symbol": "BTCUSD",
    "name": "Bitcoin",
    "asset_class": "crypto",
    "weekend_tradable": true,
    "provider": "yahoo",
    "provider_symbol": "BTC-USD",
    "is_active": true,
    "created_at": "2026-01-01T00:00:00"
  }
]
```

---

### 2. GET `/api/market-data/instruments/{instrument_code}/series`

Récupère la série temporelle d'un instrument.

**Path Parameters:**
- `instrument_code` (str): Code de l'instrument (ex: "BTCUSD")

**Query Parameters:**
- `start` (optional, str): Date de début (YYYY-MM-DD, default: 90 jours avant end)
- `end` (optional, str): Date de fin (YYYY-MM-DD, default: aujourd'hui)

**Exemple:**
```bash
curl -X GET "http://localhost:8000/api/market-data/instruments/BTCUSD/series?start=2025-01-01&end=2026-01-01" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Réponse:**
```json
[
  {
    "date": "2025-01-01",
    "open": 42000.0,
    "close": 43000.0,
    "adj_close": null,
    "volume": 1000000
  }
]
```

---

### 3. GET `/api/market-data/candles`

Récupère les bougies OHLC pour TradingView charts.

**Query Parameters:**
- `instrument_code` (required, str): Code de l'instrument
- `provider` (optional, str): Provider (default: "yahoo")
- `start` (optional, str): Date de début (YYYY-MM-DD)
- `end` (optional, str): Date de fin (YYYY-MM-DD)
- `tf` (optional, str): Timeframe (default: "1d", seul supporté actuellement)

**Exemple:**
```bash
curl -X GET "http://localhost:8000/api/market-data/candles?instrument_code=BTC-USD&start=2025-01-01&end=2026-01-01&tf=1d" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Réponse:**
```json
[
  {
    "time": 1704067200,
    "open": 42000.0,
    "high": 45000.0,
    "low": 41000.0,
    "close": 43000.0,
    "volume": 1000000
  }
]
```

**Note:** `time` est en UNIX seconds (UTC).

---

### 4. POST `/api/market-data/yahoo/ingest-from-url`

Ingère des données historiques depuis une URL Yahoo Finance.

**Body:**
```json
{
  "url": "https://finance.yahoo.com/quote/BTC-USD/history",
  "instrument_code": "BTCUSD",
  "asset_class": "CRYPTO",
  "weekend_tradable": true
}
```

**Exemple:**
```bash
curl -X POST "http://localhost:8000/api/market-data/yahoo/ingest-from-url" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://finance.yahoo.com/quote/BTC-USD/history",
    "instrument_code": "BTCUSD",
    "asset_class": "CRYPTO"
  }'
```

**Réponse:**
```json
{
  "instrument": {...},
  "rows_upserted": 365,
  "start_date": "2025-01-01",
  "end_date": "2026-01-01",
  "source": "csv",
  "chart_series": [...]
}
```

---

### 5. POST `/api/market-data/yahoo/ingest-csv`

Ingère des données depuis un fichier CSV uploadé.

**Form Data:**
- `file` (file): Fichier CSV Yahoo Finance
- `instrument_code` (str): Code de l'instrument
- `asset_class` (optional, str): Classe d'actif
- `weekend_tradable` (optional, bool): Trading weekend
- `provider_symbol` (optional, str): Symbole Yahoo (ex: "BTC-USD")

**Exemple:**
```bash
curl -X POST "http://localhost:8000/api/market-data/yahoo/ingest-csv" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@data.csv" \
  -F "instrument_code=BTCUSD" \
  -F "asset_class=CRYPTO"
```

---

### 6. POST `/api/market-data/yahoo/ingest-html-table`

Ingère des données depuis une table HTML collée (méthode principale).

**Body:**
```json
{
  "instrument_code": "BTCUSD",
  "asset_class": "CRYPTO",
  "weekend_tradable": true,
  "provider_symbol": "BTC-USD",
  "html": "<table>...</table>"
}
```

**Exemple:**
```bash
curl -X POST "http://localhost:8000/api/market-data/yahoo/ingest-html-table" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_code": "BTCUSD",
    "asset_class": "CRYPTO",
    "html": "<table>...</table>"
  }'
```

**Réponse:**
```json
{
  "instrument": {...},
  "rows_parsed": 365,
  "rows_upserted": 360,
  "rows_skipped": 5,
  "skipped": [...],
  "events_detected": [...],
  "date_range": {
    "start": "2025-01-01",
    "end": "2026-01-01"
  },
  "chart_series": [...]
}
```

---

### 7. GET `/api/market-data/performance`

Récupère les données de performance (base100) pour plusieurs instruments.

**Query Parameters:**
- `instrument_ids` (required, str): IDs séparés par virgule (ex: "1,2,3")
- `start` (required, str): Date de début (YYYY-MM-DD)
- `end` (required, str): Date de fin (YYYY-MM-DD)
- `base` (optional, int): Valeur de base (default: 100)

**Exemple:**
```bash
curl -X GET "http://localhost:8000/api/market-data/performance?instrument_ids=1,2,3&start=2025-01-01&end=2026-01-01&base=100" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Réponse:**
```json
{
  "start": "2025-01-01",
  "end": "2026-01-01",
  "base": 100,
  "instruments": [
    {
      "instrument_id": 1,
      "symbol": "BTCUSD",
      "series": [
        {
          "date": "2025-01-01",
          "value": 100.0
        }
      ],
      "stats": {
        "total_return": 0.5,
        "max_drawdown": -0.2,
        "vol_annual": 0.3
      },
      "error": null
    }
  ]
}
```

---

## Notes Importantes

1. **Authentification:** Tous les endpoints requièrent un JWT token dans le header `Authorization: Bearer <token>`.

2. **Provider Yahoo:** Par défaut, les endpoints filtrent sur `provider="yahoo"` pour garantir la cohérence des données.

3. **Module centralisé:** Les endpoints `candles` et `series` utilisent le module `bars_d1_repo` pour garantir la cohérence avec le preview et les backtests.

4. **Upsert:** Les endpoints d'ingestion utilisent un mécanisme d'upsert (insert ou update) basé sur `(instrument_id, date)` pour éviter les doublons.

5. **Source de données:** Toutes les données sont stockées dans `market_data_bars_d1` avec `source="yahoo"`.

---

## Smart Update Modes

L'endpoint `POST /api/market-data/yahoo/ingest-html-table` supporte maintenant un mode "smart update" avec détection de conflits.

### Flux UX

1. **Premier clic "Validate"** (dry_run=true par défaut):
   - Analyse les conflits sans écrire en DB
   - Si pas de conflit: retourne `status="ok"` avec `analysis` et `actions_available=["insert_delta_only"]`
   - Si conflit: retourne `status="conflict"` (HTTP 409) avec `analysis` et `actions_available=["insert_delta_only", "overwrite_overlap", "overwrite_all_range"]`

2. **Deuxième clic** (après analyse):
   - Si `status="ok"`: bouton "Apply Delta" → `dry_run=false, mode="insert_delta_only"`
   - Si `status="conflict"`: choix entre 3 modes:
     - **Add Delta Only**: Insère uniquement les dates manquantes (sûr)
     - **Overwrite Overlap + Add Delta**: Met à jour les dates de chevauchement + ajoute nouvelles dates
     - **Overwrite All Range**: Supprime toutes les dates dans la plage puis réinsère tout (destructif)

### Modes d'Application

#### `insert_delta_only`
- **Sécurité**: ⭐⭐⭐⭐⭐ (le plus sûr)
- **Comportement**: Insère uniquement les dates absentes de la DB
- **Cas d'usage**: Extension de série existante (ex: 5 ans → 10 ans)

#### `overwrite_overlap`
- **Sécurité**: ⭐⭐⭐ (modéré)
- **Comportement**: Met à jour les dates de chevauchement + insère nouvelles dates
- **Cas d'usage**: Correction de données existantes + ajout de nouvelles dates

#### `overwrite_all_range`
- **Sécurité**: ⭐ (destructif)
- **Comportement**: Supprime toutes les dates dans `[min_date..max_date]` puis réinsère toutes les données incoming
- **Cas d'usage**: Remplacement complet d'une plage de dates

### Analyse de Conflits

L'analyse compare les valeurs avec une précision de 6 décimales (`quantize`):
- **Prix** (open/high/low/close): Comparaison avec `Decimal.quantize(0.000001)`
- **Volume**: Comparaison exacte (int)

**Exemple de réponse conflict:**
```json
{
  "status": "conflict",
  "analysis": {
    "incoming_count": 365,
    "incoming_range": {"min": "2025-01-01", "max": "2025-12-31"},
    "existing_count": 180,
    "existing_range": {"min": "2025-07-01", "max": "2025-12-31"},
    "overlap_count": 180,
    "mismatch_count": 5,
    "mismatches": [
      {"date": "2025-07-15", "field": "close", "existing_value": 105.0, "incoming_value": 107.0}
    ],
    "delta_count": 185,
    "has_conflict": true
  },
  "actions_available": ["insert_delta_only", "overwrite_overlap", "overwrite_all_range"]
}
```

### Exemple d'Utilisation

```bash
# 1. Dry run (analyse)
curl -X POST "http://localhost:8000/api/market-data/yahoo/ingest-html-table" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_code": "BTCUSD",
    "asset_class": "CRYPTO",
    "html": "<table>...</table>",
    "dry_run": true
  }'

# 2. Appliquer delta seulement (si pas de conflit)
curl -X POST "http://localhost:8000/api/market-data/yahoo/ingest-html-table" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_code": "BTCUSD",
    "asset_class": "CRYPTO",
    "html": "<table>...</table>",
    "dry_run": false,
    "mode": "insert_delta_only"
  }'
```

---

**Dernière mise à jour:** 2026-01-09

