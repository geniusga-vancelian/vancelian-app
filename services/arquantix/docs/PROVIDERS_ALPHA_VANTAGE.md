# Alpha Vantage Provider

## Pourquoi Alpha Vantage ?

**Raison** : Provider gratuit avec données historiques longues (20+ ans) pour crypto et ETFs.

**Limitations** :
- Free tier : 5 calls/minute (on utilise 4 pour sécurité)
- Premium tier : 75 calls/minute

**Alternatives possibles** : Polygon, Yahoo Finance, IEX Cloud (futur).

---

## Fonctions utilisées

### `DIGITAL_CURRENCY_DAILY`

**Usage** : Crypto (BTC, ETH, SOL)

**Paramètres** :
- `function=DIGITAL_CURRENCY_DAILY`
- `symbol=BTC` (ou ETH, SOL)
- `market=USD`
- `apikey=<key>`

**Réponse JSON** :
```json
{
  "Meta Data": {
    "1. Information": "Daily Prices and Volumes for Digital Currency",
    "2. Digital Currency Code": "BTC",
    "3. Digital Currency Name": "Bitcoin",
    "4. Market Code": "USD",
    "5. Market Name": "United States Dollar",
    "6. Last Refreshed": "2024-01-15",
    "7. Time Zone": "UTC"
  },
  "Time Series (Digital Currency Daily)": {
    "2024-01-15": {
      "1a. open (USD)": "42000.00",
      "2a. high (USD)": "42500.00",
      "3a. low (USD)": "41500.00",
      "4a. close (USD)": "42200.00",
      "5. volume": "1000000",
      "6. market cap (USD)": "830000000000"
    },
    "2024-01-14": { ... }
  }
}
```

**Champs utilisés** :
- `1a. open (USD)` → `open`
- `2a. high (USD)` → `high`
- `3a. low (USD)` → `low`
- `4a. close (USD)` → `close`
- `5. volume` → `volume`

**Fallback** : Si `"1a. open (USD)"` absent, essaie `"1. open"` puis `"open"` (robustesse).

---

### `TIME_SERIES_DAILY_ADJUSTED`

**Usage** : ETFs, equities (URTH, QQQ, DIA, GLD)

**Paramètres** :
- `function=TIME_SERIES_DAILY_ADJUSTED`
- `symbol=QQQ` (ou URTH, DIA, GLD)
- `outputsize=full` (20+ ans) ou `compact` (100 jours)
- `apikey=<key>`

**Réponse JSON** :
```json
{
  "Meta Data": {
    "1. Information": "Daily Time Series with Splits and Dividend Events",
    "2. Symbol": "QQQ",
    "3. Last Refreshed": "2024-01-15",
    "4. Output Size": "Full size",
    "5. Time Zone": "US/Eastern"
  },
  "Time Series (Daily)": {
    "2024-01-15": {
      "1. open": "380.00",
      "2. high": "385.00",
      "3. low": "378.00",
      "4. close": "382.00",
      "5. adjusted close": "382.00",
      "6. volume": "50000000",
      "7. dividend amount": "0.0000",
      "8. split coefficient": "1.0"
    },
    "2024-01-14": { ... }
  }
}
```

**Champs utilisés** :
- `1. open` → `open`
- `2. high` → `high`
- `3. low` → `low`
- `4. close` → `close`
- `5. volume` → `volume`

**Note** : On utilise `open` (pas `adjusted close`) pour convention open-to-open.

---

## Mapping symboles

### CORE_V1 Universe

| Symbole | Asset Class | Fonction Alpha Vantage | Provider Symbol |
|---------|-------------|------------------------|-----------------|
| BTC | crypto | `DIGITAL_CURRENCY_DAILY` | BTC |
| ETH | crypto | `DIGITAL_CURRENCY_DAILY` | ETH |
| SOL | crypto | `DIGITAL_CURRENCY_DAILY` | SOL |
| URTH | etf | `TIME_SERIES_DAILY_ADJUSTED` | URTH |
| QQQ | etf | `TIME_SERIES_DAILY_ADJUSTED` | QQQ |
| DIA | etf | `TIME_SERIES_DAILY_ADJUSTED` | DIA |
| GLD | etf | `TIME_SERIES_DAILY_ADJUSTED` | GLD |

**Logique** :
- `asset_class == "crypto"` → `DIGITAL_CURRENCY_DAILY`
- `asset_class == "etf"` ou `"equity"` → `TIME_SERIES_DAILY_ADJUSTED`

---

## Structure des réponses

### Réponse réussie

**Crypto** :
```json
{
  "Meta Data": { ... },
  "Time Series (Digital Currency Daily)": {
    "2024-01-15": {
      "1a. open (USD)": "42000.00",
      ...
    }
  }
}
```

**ETF** :
```json
{
  "Meta Data": { ... },
  "Time Series (Daily)": {
    "2024-01-15": {
      "1. open": "380.00",
      ...
    }
  }
}
```

---

### Erreurs fréquentes

#### Rate Limit

**Réponse** :
```json
{
  "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute and 500 calls per day. Please visit https://www.alphavantage.co/premium/ if you would like to target a higher API call frequency."
}
```

**Détection** : Clé `"Note"` présente.

**Action** : Retourne `status="error"` dans backfill, recommandation de relancer après délai.

---

#### Invalid API Call

**Réponse** :
```json
{
  "Error Message": "Invalid API call. Please retry or visit the documentation (https://www.alphavantage.co/documentation/) for TIME_SERIES_DAILY_ADJUSTED."
}
```

**Détection** : Clé `"Error Message"` présente.

**Action** : Retourne `status="error"` avec message.

**Causes possibles** :
- Symbole invalide
- Fonction incorrecte
- Paramètres manquants

---

#### Information (symbole non trouvé)

**Réponse** :
```json
{
  "Information": "The symbol you requested is not found. Please check the symbol and try again."
}
```

**Détection** : Clé `"Information"` présente.

**Action** : Retourne `status="error"` avec message.

---

#### Time Series manquant

**Réponse** :
```json
{
  "Meta Data": { ... },
  // Pas de "Time Series (Daily)" ou "Time Series (Digital Currency Daily)"
}
```

**Détection** : Clé time series absente.

**Action** : Retourne `status="error"` avec liste clés disponibles (pour debug).

---

## Parsing robuste

### Crypto

**Clés candidates** (ordre de préférence) :

**Open** :
1. `"1a. open (USD)"`
2. `"1. open"`
3. `"open"`

**High** :
1. `"2a. high (USD)"`
2. `"2. high"`
3. `"high"`

**Low** :
1. `"3a. low (USD)"`
2. `"3. low"`
3. `"low"`

**Close** :
1. `"4a. close (USD)"`
2. `"4. close"`
3. `"close"`

**Volume** :
1. `"5. volume"`
2. `"volume"`

**Fallback** : Si aucune clé trouvée, `ValueError` avec liste clés disponibles (sample).

---

### ETF/Equity

**Clés fixes** :
- `"1. open"` → `open`
- `"2. high"` → `high`
- `"3. low"` → `low`
- `"4. close"` → `close`
- `"5. volume"` → `volume`

**Pas de fallback** : Structure standardisée.

---

## Gestion erreurs dans le code

### Client (`client.py`)

**Méthode `_request()`** :
```python
def _request(self, params: Dict[str, str]) -> Dict[str, Any]:
    _rate_limit()  # Rate limiting
    
    response = client.get(self.base_url, params=params)
    data = response.json()
    
    # Check for API errors
    if "Error Message" in data:
        raise ValueError(f"Alpha Vantage API error: {data['Error Message']}")
    if "Note" in data:
        raise ValueError(f"Alpha Vantage rate limit: {data['Note']}")
    
    return data
```

---

### Routes (`routes.py`)

**Backfill** :
```python
try:
    data = client.get_daily_crypto(symbol, market="USD")
    bars = client.parse_daily_crypto(data)
    
    # Filter by date range
    bars = [b for b in bars if start_date <= b["date"] <= end_date]
    
    # Hard fail if no bars
    if not bars:
        raise ValueError(f"No bars found in date range")
    
    # Insert bars
    # ...
    
    # Hard fail if 0 inserted
    if inserted == 0:
        raise ValueError(f"No bars inserted")
        
except ValueError as e:
    # Return error status
    return BackfillMissingItem(status="error", error=str(e))
```

---

## Rate Limiting

**Limite free tier** : 5 calls/minute

**Implémentation** : 4 calls/minute (marge de sécurité)

**Code** (`client.py`) :
```python
RATE_LIMIT_CALLS = 4
RATE_LIMIT_WINDOW = 60  # seconds
_last_call_times: List[float] = []

def _rate_limit():
    now = time.time()
    # Remove calls older than window
    _last_call_times = [t for t in _last_call_times if now - t < RATE_LIMIT_WINDOW]
    
    if len(_last_call_times) >= RATE_LIMIT_CALLS:
        # Wait until oldest call is outside window
        wait_time = RATE_LIMIT_WINDOW - (now - _last_call_times[0]) + 1
        if wait_time > 0:
            time.sleep(wait_time)
            _last_call_times = []
    
    _last_call_times.append(time.time())
```

**Impact** : Backfill séquentiel lent (ex: 7 instruments × 15s = ~2 minutes minimum).

---

## Validation préalable

**Endpoint** : `POST /api/market-data/validate-provider`

**Usage** : Valider symboles AVANT backfill massif.

**Logique** :
1. Appelle Alpha Vantage pour chaque symbole
2. Vérifie erreurs (`Error Message`, `Note`, `Information`)
3. Vérifie time series présent
4. Parse un bar sample (derniers `years`)
5. Retourne `ValidateProviderResult(ok, sample_date, sample_open, sample_close, error)`

**Exemple réponse** :
```json
{
  "total": 7,
  "passed": 6,
  "failed": 1,
  "results": [
    {
      "symbol": "BTC",
      "asset_class": "crypto",
      "function_used": "DIGITAL_CURRENCY_DAILY",
      "ok": true,
      "sample_date": "2024-01-15",
      "sample_open": 42000.00,
      "sample_close": 42200.00,
      "error": null
    },
    {
      "symbol": "INVALID",
      "asset_class": "etf",
      "function_used": "TIME_SERIES_DAILY_ADJUSTED",
      "ok": false,
      "sample_date": null,
      "sample_open": null,
      "sample_close": null,
      "error": "Invalid API call. Please retry..."
    }
  ]
}
```

---

## Exemples de parsing

### Crypto (BTC)

**Réponse brute** :
```json
{
  "Time Series (Digital Currency Daily)": {
    "2024-01-15": {
      "1a. open (USD)": "42000.00",
      "2a. high (USD)": "42500.00",
      "3a. low (USD)": "41500.00",
      "4a. close (USD)": "42200.00",
      "5. volume": "1000000"
    }
  }
}
```

**Parsé** :
```python
{
    "date": date(2024, 1, 15),
    "open": Decimal("42000.00"),
    "high": Decimal("42500.00"),
    "low": Decimal("41500.00"),
    "close": Decimal("42200.00"),
    "volume": 1000000
}
```

---

### ETF (QQQ)

**Réponse brute** :
```json
{
  "Time Series (Daily)": {
    "2024-01-15": {
      "1. open": "380.00",
      "2. high": "385.00",
      "3. low": "378.00",
      "4. close": "382.00",
      "5. volume": "50000000"
    }
  }
}
```

**Parsé** :
```python
{
    "date": date(2024, 1, 15),
    "open": Decimal("380.00"),
    "high": Decimal("385.00"),
    "low": Decimal("378.00"),
    "close": Decimal("382.00"),
    "volume": 50000000
}
```

---

## Limitations connues

1. **Rate limit** : 4 calls/minute (free tier)
2. **Pas de données futures** : Historique uniquement
3. **Délai données** : 15-20 minutes pour données intraday (non utilisé ici)
4. **Symboles limités** : Certains symboles non supportés (validation préalable recommandée)

---

## Documents associés

- [Market Data Architecture](./MARKET_DATA_ARCHITECTURE.md)
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)






