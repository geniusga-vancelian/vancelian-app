# Market Data Architecture

## Structure du module

```
api/services/market_data/
├── __init__.py
├── config.py          # Configuration (env vars)
├── schemas.py         # Pydantic models (API)
├── client.py          # Alpha Vantage client
└── routes.py          # FastAPI endpoints
```

---

## Fichiers détaillés

### `config.py`

**Rôle** : Chargement des variables d'environnement.

**Variables** :
- `ALPHAVANTAGE_API_KEY` : Clé API Alpha Vantage (requis)
- `MARKET_DATA_PROVIDER` : Provider par défaut (`"alphavantage"`)

**Pattern** : Utilise `os.getenv()` (pas Pydantic Settings), aligné avec l'audit Arquantix.

```python
import os

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "alphavantage")
```

---

### `schemas.py`

**Rôle** : Définition des modèles Pydantic pour validation API.

**Modèles principaux** :

#### `InstrumentResponse`
```python
class InstrumentResponse(BaseModel):
    id: int
    symbol: str
    name: Optional[str]
    asset_class: str  # "equity", "etf", "crypto"
    weekend_tradable: bool
    provider: str
    provider_symbol: Optional[str]
    is_active: bool
    created_at: datetime
```

#### `BackfillMissingRequest`
```python
class BackfillMissingRequest(BaseModel):
    days: int = 365  # Nombre de jours à backfiller
    symbols: Optional[List[str]] = None  # Sous-ensemble optionnel
    force: bool = False  # Si True, backfill même si bars existent
```

#### `BackfillMissingResponse`
```python
class BackfillMissingResponse(BaseModel):
    db_name: str
    start: str  # YYYY-MM-DD
    end: str
    days: int
    total_instruments: int
    missing_before: int
    processed: List[BackfillMissingItem]  # Résultat par instrument
    missing_after: int
    total_bars_added: int
    duration_ms: int
```

#### `ValidateProviderRequest` / `ValidateProviderResponse`
Validation Alpha Vantage avant insertion DB.

#### `PerformanceResponse`
Réponse pour l'endpoint `/api/market-data/performance` (historique base100).

---

### `client.py`

**Rôle** : Client HTTP pour Alpha Vantage API avec rate limiting.

**Classe** : `AlphaVantageClient`

#### Rate Limiting

**Limite** : 4 calls/minute (free tier), 75 calls/minute (premium)

**Implémentation** :
```python
RATE_LIMIT_CALLS = 4
RATE_LIMIT_WINDOW = 60  # seconds
_last_call_times: List[float] = []

def _rate_limit():
    """Attend si trop d'appels récents"""
    # Supprime appels > 60s
    # Si >= 4 appels, attend jusqu'à ce que le plus ancien sorte de la fenêtre
```

#### Méthodes principales

##### `get_daily_equity_adjusted(symbol, outputsize="full")`
- **Fonction Alpha Vantage** : `TIME_SERIES_DAILY_ADJUSTED`
- **Usage** : ETFs, equities
- **Retour** : `{"Time Series (Daily)": {...}}`

##### `get_daily_crypto(symbol, market="USD")`
- **Fonction Alpha Vantage** : `DIGITAL_CURRENCY_DAILY`
- **Usage** : Crypto (BTC, ETH, SOL)
- **Retour** : `{"Time Series (Digital Currency Daily)": {...}}`

##### `parse_daily_equity(data)`
- **Parse** : `TIME_SERIES_DAILY` ou `TIME_SERIES_DAILY_ADJUSTED`
- **Champs** : `1. open`, `2. high`, `3. low`, `4. close`, `5. volume`
- **Retour** : `List[Dict[str, Any]]` avec `date`, `open`, `high`, `low`, `close`, `volume`

##### `parse_daily_crypto(data)`
- **Parse** : `DIGITAL_CURRENCY_DAILY`
- **Champs robustes** : Fallback sur plusieurs clés possibles
  - `open` : `"1a. open (USD)"` → `"1. open"` → `"open"`
  - `high` : `"2a. high (USD)"` → `"2. high"` → `"high"`
  - `low` : `"3a. low (USD)"` → `"3. low"` → `"low"`
  - `close` : `"4a. close (USD)"` → `"4. close"` → `"close"`
- **Gestion erreurs** : Si aucune clé trouvée, `ValueError` avec liste des clés disponibles

#### Gestion d'erreurs

**Erreurs détectées** :
- `"Error Message"` dans réponse → `ValueError("Alpha Vantage API error: ...")`
- `"Note"` dans réponse → `ValueError("Alpha Vantage rate limit: ...")`
- HTTP status != 200 → `ValueError("Alpha Vantage HTTP error: ...")`

---

### `routes.py`

**Rôle** : Endpoints FastAPI pour Market Data.

**Router** : `APIRouter(prefix="/api/market-data", tags=["market-data"])`

**Protection** : Tous les endpoints protégés par `Depends(get_current_user)`

#### Endpoints

##### `GET /api/market-data/instruments`

**Rôle** : Liste des instruments.

**Query params** :
- `is_active` : `Optional[bool]` (filtre)
- `asset_class` : `Optional[str]` ("equity", "etf", "crypto")

**Retour** : `List[InstrumentResponse]`

**Logique** :
1. Query `MarketDataInstrument`
2. Filtre `is_active` si fourni
3. Filtre `asset_class` si fourni
4. Retourne liste triée par `symbol`

---

##### `POST /api/market-data/instruments/seed`

**Rôle** : Seed CORE_V1 universe (7 instruments).

**Body** : `SeedRequest(universe="CORE_V1")`

**CORE_V1_INSTRUMENTS** :
```python
[
    {"symbol": "BTC", "name": "Bitcoin", "asset_class": "crypto", "weekend_tradable": True},
    {"symbol": "ETH", "name": "Ethereum", "asset_class": "crypto", "weekend_tradable": True},
    {"symbol": "SOL", "name": "Solana", "asset_class": "crypto", "weekend_tradable": True},
    {"symbol": "URTH", "name": "iShares MSCI World ETF", "asset_class": "etf", "weekend_tradable": False},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_class": "etf", "weekend_tradable": False},
    {"symbol": "DIA", "name": "SPDR Dow Jones Industrial Average ETF", "asset_class": "etf", "weekend_tradable": False},
    {"symbol": "GLD", "name": "SPDR Gold Trust", "asset_class": "etf", "weekend_tradable": False},
]
```

**Logique** :
1. Désactive instruments existants non dans CORE_V1 (`is_active=false`)
2. Pour chaque CORE_V1 :
   - Si existe : réactive et met à jour champs
   - Si n'existe pas : crée nouvel instrument
3. Commit DB
4. Retourne liste instruments actifs

---

##### `POST /api/market-data/instruments/{instrument_id}/backfill`

**Rôle** : Backfill historique pour un instrument spécifique.

**Body** : `BackfillRequest(start_date="YYYY-MM-DD", end_date="YYYY-MM-DD")`

**Logique** :
1. Charge instrument depuis DB
2. Détermine fonction Alpha Vantage :
   - `crypto` → `get_daily_crypto(provider_symbol, market="USD")`
   - `etf`/`equity` → `get_daily_equity_adjusted(provider_symbol, outputsize="full")`
3. Parse réponse → liste bars
4. Filtre par date range
5. Insert/update bars dans DB (commit)
6. Retourne `HistoryResponse`

**Gestion erreurs** :
- Si 0 bars après filtrage → `HTTPException(400, "No bars found in date range")`
- Si erreur Alpha Vantage → `HTTPException(500, error_message)`

---

##### `POST /api/market-data/update-daily`

**Rôle** : Mise à jour incrémentale (derniers jours) pour tous instruments actifs.

**Logique** :
1. Query instruments actifs
2. Pour chaque instrument :
   - Détermine dernière date dans DB
   - Appelle Alpha Vantage (derniers jours)
   - Insert nouvelles bars uniquement
3. Retourne résumé (instruments mis à jour, bars ajoutés)

**Note** : MVP synchrone (pas de background job).

---

##### `GET /api/market-data/instruments/{instrument_id}/bars`

**Rôle** : Récupère bars historiques pour un instrument.

**Query params** :
- `start` : `Optional[str]` (YYYY-MM-DD)
- `end` : `Optional[str]` (YYYY-MM-DD)

**Retour** : `HistoryResponse(symbol, bars, start_date, end_date, count)`

---

##### `GET /api/market-data/missing`

**Rôle** : Liste instruments sans bars.

**Retour** : `List[MissingInstrumentResponse]`

**Logique** :
```sql
SELECT instrument.*, COUNT(bars.instrument_id) as bars_count
FROM market_data_instruments instrument
LEFT JOIN market_data_bars_d1 bars ON instrument.id = bars.instrument_id
WHERE instrument.is_active = 'true'
GROUP BY instrument.id
HAVING COUNT(bars.instrument_id) = 0
```

---

##### `POST /api/market-data/backfill-missing`

**Rôle** : Backfill tous instruments manquants.

**Body** : `BackfillMissingRequest(days, symbols, force)`

**Logique** :
1. Calcule date range : `end = today`, `start = today - days`
2. Query instruments manquants (même query que `GET /missing`)
3. Filtre par `symbols` si fourni
4. Pour chaque instrument (séquentiel, rate-limited) :
   - Appelle Alpha Vantage (crypto ou equity selon `asset_class`)
   - Parse bars
   - Filtre par date range
   - **Hard fail si 0 bars après filtrage** → `status="error"`
   - Insert/update bars (commit par instrument)
   - **Hard fail si 0 bars insérés** → `status="error"`
   - Retourne `BackfillMissingItem(status, bars_added, error)`
5. Retourne `BackfillMissingResponse` avec résumé

**Points critiques** :
- Commit par instrument (pas de rollback global)
- Hard fail si 0 bars (pas de "OK avec 0 bars")
- Rate limiting automatique (client Alpha Vantage)

---

##### `POST /api/market-data/validate-provider`

**Rôle** : Valide Alpha Vantage pour symboles AVANT insertion DB.

**Body** : `ValidateProviderRequest(symbols, years)`

**Logique** :
1. Pour chaque symbole :
   - Détermine `asset_class` (depuis DB si existe, sinon `"etf"` par défaut)
   - Appelle Alpha Vantage :
     - `crypto` → `DIGITAL_CURRENCY_DAILY`
     - `etf`/`equity` → `TIME_SERIES_DAILY_ADJUSTED`
   - Vérifie erreurs :
     - `"Error Message"` → FAIL
     - `"Note"` → FAIL (rate limit)
     - `"Information"` → FAIL
     - Time series manquant → FAIL (liste clés disponibles)
   - Parse un bar sample (derniers `years`)
   - Retourne `ValidateProviderResult(ok, sample_date, sample_open, sample_close, error)`
2. Retourne `ValidateProviderResponse(total, passed, failed, results)`

**Usage** : Validation avant backfill massif.

---

##### `GET /api/market-data/performance`

**Rôle** : Historique performance (base100) pour instruments sélectionnés.

**Query params** :
- `instrument_ids` : `str` (comma-separated, ex: "1,2,3")
- `start` : `str` (YYYY-MM-DD)
- `end` : `str` (YYYY-MM-DD)
- `base` : `int` (default: 100)

**Retour** : `PerformanceResponse(start, end, base, instruments)`

**Logique** :
1. Parse `instrument_ids` → liste entiers
2. Charge instruments metadata
3. Charge bars D1 (via `load_open_bars` du backtest repository)
4. Pour chaque instrument :
   - Aligne prix au calendrier (forward-fill)
   - Calcule base100 : `(price / first_price) * base`
   - Calcule stats :
     - `total_return` : `(last / first) - 1`
     - `max_drawdown` : `min((base100 / peak) - 1)`
     - `vol_annual` : `std(daily_returns) * sqrt(365)`
5. Retourne séries + stats par instrument

**Usage** : "Voir historiques" dans UI (sans backtest).

---

## Détection "Missing" instruments

**Critère** : Instrument actif (`is_active="true"`) avec `COUNT(bars) = 0`

**Query SQL** :
```sql
SELECT instrument.*, COUNT(bars.instrument_id) as bars_count
FROM market_data_instruments instrument
LEFT JOIN market_data_bars_d1 bars ON instrument.id = bars.instrument_id
WHERE instrument.is_active = 'true'
GROUP BY instrument.id
HAVING COUNT(bars.instrument_id) = 0
```

**Endpoints** :
- `GET /api/market-data/missing` : Liste instruments manquants
- `POST /api/market-data/backfill-missing` : Backfill automatique

---

## Gestion erreurs Provider

### Cas d'erreur

1. **Rate limit** : `"Note"` dans réponse Alpha Vantage
   - **Action** : Retourne `status="error"` dans backfill
   - **Recommandation** : Relancer après délai

2. **Invalid API call** : `"Error Message"` dans réponse
   - **Action** : Retourne `status="error"` avec message
   - **Exemple** : `"Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED."`

3. **Time series manquant** : Clé attendue absente
   - **Action** : Retourne `status="error"` avec liste clés disponibles
   - **Exemple** : `"Missing required price key. Available keys: ['Meta Data', 'Error Message']"`

4. **0 bars après filtrage** : Date range ne contient pas de données
   - **Action** : Hard fail (`status="error"`)
   - **Raison** : Évite "OK avec 0 bars"

5. **0 bars insérés** : Tous bars déjà existants ou erreur insert
   - **Action** : Hard fail (`status="error"`)
   - **Raison** : Évite "OK avec 0 bars"

### Validation préalable

**Endpoint** : `POST /api/market-data/validate-provider`

**Usage** : Valider symboles AVANT backfill massif.

**Retour** : `ValidateProviderResponse` avec `ok`/`failed` par symbole.

---

## Commit DB

**Stratégie** : Commit par instrument (pas de transaction globale)

**Raison** :
- Si un instrument échoue, les autres continuent
- Évite rollback massif en cas d'erreur

**Code** :
```python
for instrument in instruments:
    try:
        # Fetch + parse + insert bars
        db.commit()  # Commit par instrument
    except Exception as e:
        db.rollback()  # Rollback uniquement cet instrument
        # Continue avec suivant
```

---

## Rate Limiting

**Limite** : 4 calls/minute (free tier Alpha Vantage)

**Implémentation** : Dans `client.py`, fonction `_rate_limit()`

**Comportement** :
- Si >= 4 appels dans les 60 dernières secondes → attend
- Attente = `60 - (now - oldest_call) + 1` secondes

**Impact** : Backfill séquentiel lent (ex: 7 instruments × 15s = ~2 minutes minimum)

---

## Documents associés

- [Overview](./MARKET_DATA_AND_BACKTEST_OVERVIEW.md)
- [Database Schema](./DATABASE_SCHEMA_MARKET_BACKTEST.md)
- [Alpha Vantage Provider](./PROVIDERS_ALPHA_VANTAGE.md)
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)






