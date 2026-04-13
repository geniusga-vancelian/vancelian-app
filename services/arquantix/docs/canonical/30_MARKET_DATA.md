# Market Data — Instruments & Bars D1

**Fichiers clés**: `api/services/market_data/`, `api/database.py`, `api/scripts/load_market_data.py`

---

## 1. Asset Classes

### Liste exhaustive

Définie dans `api/services/market_data/routes.py:19-27`:

```python
CORE_V1_INSTRUMENTS = [
    {"symbol": "BTC", "name": "Bitcoin", "asset_class": "crypto", "weekend_tradable": "true"},
    {"symbol": "ETH", "name": "Ethereum", "asset_class": "crypto", "weekend_tradable": "true"},
    {"symbol": "SOL", "name": "Solana", "asset_class": "crypto", "weekend_tradable": "true"},
    {"symbol": "URTH", "name": "iShares MSCI World ETF", "asset_class": "etf", "weekend_tradable": "false"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_class": "etf", "weekend_tradable": "false"},
    {"symbol": "DIA", "name": "SPDR Dow Jones Industrial Average ETF", "asset_class": "etf", "weekend_tradable": "false"},
    {"symbol": "GLD", "name": "SPDR Gold Trust", "asset_class": "etf", "weekend_tradable": "false"},
]
```

**Asset classes supportées** (d'après `InstrumentCreate`):
- `crypto` - Cryptomonnaies (BTC, ETH, SOL, etc.)
- `etf` - ETFs (QQQ, URTH, DIA, GLD, etc.)
- `equity` - Actions (UNKNOWN si utilisé)
- `forex` - Devises (EURUSD, GBPUSD, etc.)
- `index` - Indices (S&P 500, NASDAQ, etc.)
- `commodities` - Matières premières (GOLD, SILVER, etc.)

**Référence**: `api/services/market_data/routes.py:37`

### Règles par classe

**Weekend Trading**:
- **Crypto**: `weekend_tradable = "true"` (trading 24/7)
- **ETF/Equity/Forex/Index/Commodities**: `weekend_tradable = "false"` (trading en semaine)

**Provider Symbol**:
- **Crypto**: `BTC-USD`, `ETH-USD`, `SOL-USD` (suffixe `-USD` pour Yahoo Finance)
- **Forex**: `EURUSD=X`, `GBPUSD=X` (suffixe `=X` pour Yahoo Finance)
- **Indices**: `^GSPC` (S&P 500), `^DJI` (Dow Jones), etc.

**Référence**: `api/services/market_data/yahoo_client.py:19-65`

---

## 2. Instruments

### Modèle (`api/database.py:117-132`)

```python
class MarketDataInstrument(Base):
    __tablename__ = "market_data_instruments"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)  # Instrument code interne
    name = Column(String(200), nullable=True)
    asset_class = Column(String(20), nullable=False)  # crypto, etf, etc.
    weekend_tradable = Column(String(10), nullable=False, server_default="false")  # "true" or "false" as string
    provider = Column(String(50), nullable=False, server_default="yahoo")
    provider_symbol = Column(String(50), nullable=True)  # Symbole pour Yahoo Finance
    is_active = Column(String(10), nullable=False, server_default="true")  # "true" or "false" as string
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
```

### Instrument Code vs Provider Symbol

**`symbol`** (instrument_code interne):
- Format: `BTC`, `ETH`, `QQQ`, `EURUSD`
- Unique, utilisé dans l'application

**`provider_symbol`** (symbole pour Yahoo Finance):
- Format: `BTC-USD`, `ETH-USD`, `QQQ`, `EURUSD=X`
- Optionnel (si `None`, conversion automatique via `YahooFinanceClient.get_symbol_for_yahoo()`)
- Utilisé pour fetch les données depuis Yahoo Finance

**Exemple**:
- `symbol = "BTC"`, `provider_symbol = "BTC-USD"` → Yahoo Finance cherche `BTC-USD`
- `symbol = "BTC"`, `provider_symbol = None` → Conversion auto: `BTC-USD`

**Référence**: `api/services/market_data/yahoo_client.py:19-65`

### Normalisation

**Fonction**: `YahooFinanceClient.get_symbol_for_yahoo()`

**Règles**:
1. Si `provider_symbol` fourni → utiliser tel quel
2. Si `asset_class == "crypto"` → ajouter `-USD` si absent
3. Si `asset_class == "forex"` → ajouter `=X` si absent
4. Si index → mapping (ex: `"S&P 500"` → `"^GSPC"`)
5. Sinon → utiliser `symbol` tel quel

**Référence**: `api/services/market_data/yahoo_client.py:19-65`

---

## 3. Provider Yahoo Finance

**Client**: `YahooFinanceClient` (`api/services/market_data/yahoo_client.py`)

**Library**: `yfinance` (version: UNKNOWN, vérifier `api/requirements.txt`)

**Méthode principale**: `get_historical_data()`

**Paramètres**:
- `symbol`: Instrument code interne (ex: `"BTC"`)
- `asset_class`: Classe d'actif (ex: `"crypto"`)
- `provider_symbol`: Symbole Yahoo Finance (optionnel)
- `start_date`: Date de début (optionnel)
- `end_date`: Date de fin (optionnel, défaut: aujourd'hui)
- `period`: Période (`"1d"`, `"5d"`, `"1mo"`, `"3mo"`, `"6mo"`, `"1y"`, `"2y"`, `"5y"`, `"10y"`, `"ytd"`, `"max"`)

**Retour**: Liste de bars `[{"date": date, "open": Decimal, "high": Decimal, "low": Decimal, "close": Decimal, "volume": int}, ...]`

**Référence**: `api/services/market_data/yahoo_client.py:67-175`

---

## 4. Table `market_data_bars_d1`

### Structure (`api/database.py:134-148`)

```python
class MarketDataBarD1(Base):
    __tablename__ = "market_data_bars_d1"
    
    instrument_id = Column(Integer, ForeignKey("public.market_data_instruments.id"), primary_key=True, nullable=False, index=True)
    date = Column(Date, primary_key=True, nullable=False, index=True)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    volume = Column(BigInteger, nullable=False)
    source = Column(String(50), nullable=False, server_default="yahoo")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
```

### Clé primaire

**PK**: `(instrument_id, date)` - Une seule barre par instrument et date.

**Contrainte unique**: `uq_market_data_bars_d1_instrument_date` (implicite via PK composite).

**Référence**: `api/alembic/versions/dd7124eabc4d_add_market_data_tables.py:40-57`

### Source de vérité

**Table unique**: `market_data_bars_d1` est la **source unique de vérité** pour toutes les données historiques D1.

**Utilisation**:
- **Charts**: `GET /api/market-data/instruments/{id}/bars` → Query `market_data_bars_d1`
- **Backtests**: `load_open_bars()` dans `api/services/backtest/repository.py` → Query `market_data_bars_d1`
- **Preview**: UNKNOWN (non vérifié)

**Pourquoi tout passe par cette table**:
- Cohérence des données (pas de duplication)
- Performance (index sur `instrument_id` et `date`)
- Historique traçable (`created_at`)

**Référence**: `api/services/backtest/repository.py:23-70`

---

## 5. Ingestion Yahoo Finance (HTML)

### Méthode canonique

**Script**: `api/scripts/load_market_data.py`

**Usage**:
```bash
python scripts/load_market_data.py [--all] [--update-recent] [--instrument-id ID] [--force-full]
```

**Référence**: `api/scripts/load_market_data.py:1-4`

### Parsing HTML

⚠️ **UNKNOWN (needs confirmation)**: Le parsing HTML Yahoo Finance n'est pas vérifié dans le code actuel.

**Fichier mentionné**: `web/src/app/admin/market-data/upload/page.tsx` (textarea pour HTML Yahoo Finance)

**Backend**: UNKNOWN si endpoint existe pour parser HTML.

### Validation colonnes

**Colonnes attendues** (OHLCV):
- `open` - Prix d'ouverture
- `high` - Prix le plus haut
- `low` - Prix le plus bas
- `close` - Prix de clôture
- `volume` - Volume

**Type**: `Numeric(20, 8)` pour OHLC, `BigInteger` pour volume.

**Référence**: `api/database.py:140-144`

### Gestion des conflits

**Insertion**: Si barre existe déjà (même `instrument_id` + `date`), comportement UNKNOWN (upsert ou erreur ?).

**Référence**: UNKNOWN (non vérifié dans `api/scripts/load_market_data.py`)

---

## 6. Smart Update (`load_market_data.py`)

### Dry Run

⚠️ **UNKNOWN (needs confirmation)**: Option `--check-only` mentionnée dans les commentaires mais UNKNOWN si implémentée.

**Référence**: `api/scripts/load_market_data.py:250` (argument `--check-only`)

### Delta (mise à jour récente)

**Option**: `--update-recent`

**Logique**:
- Vérifie la dernière barre (`max(date)`)
- Si `date_max < today - 7 jours` → fetch récent (derniers 120 jours)
- Sinon → skip

**Référence**: `api/scripts/load_market_data.py:113-118`

### Overwrite Overlap

⚠️ **UNKNOWN (needs confirmation)**: Logique de merge/overwrite des données existantes non vérifiée.

### Overwrite Full Range

**Option**: `--force-full`

**Logique**: Force fetch complet (période max) même si données existent.

**Référence**: `api/scripts/load_market_data.py:90` (paramètre `force_full`)

---

## 7. Fonctions `load_open_bars` (repository)

**Fichier**: `api/services/backtest/repository.py:23-70`

**Signature**:
```python
def load_open_bars(db: Session, instrument_ids: List[int], start_date: date, end_date: date) -> Dict[int, pd.DataFrame]:
```

**Retour**: Dict `{instrument_id: DataFrame}` où DataFrame index = date, colonnes = `['open', 'high', 'low', 'close', 'volume']`

**Logique**:
1. Query `market_data_bars_d1` avec filtres `instrument_id IN (...) AND date >= start_date AND date <= end_date`
2. Grouper par `instrument_id`
3. Convertir en DataFrame Pandas (index = date, colonnes = OHLCV)
4. Retourner dict

**Utilisation**: Backtest executor (`api/services/backtest/executor.py:39`)

**Référence**: `api/services/backtest/repository.py:23-70`

---

## 8. Bugs évités grâce à la centralisation

**Avant** (si chaque module fetchait directement Yahoo):
- Données inconsistantes (caches différents)
- Rate limiting multiple
- Historique non traçable

**Après** (centralisation via `market_data_bars_d1`):
- Source unique de vérité
- Cohérence garantie (même données pour charts et backtests)
- Historique traçable (`created_at`)
- Performance (index DB)

---

## 9. Migration vers Yahoo Finance

**Ancien provider**: Alpha Vantage (déprécié)

**Nouveau provider**: Yahoo Finance (via `yfinance`)

**Changements**:
- `api/services/market_data/client.py` → DEPRECATED
- `api/services/market_data/yahoo_client.py` → Nouveau client
- `provider` default: `"yahoo"` (au lieu de `"alphavantage"`)
- `source` default: `"yahoo"` dans `market_data_bars_d1`

**Référence**: `api/database.py:128,145`, `api/services/market_data/yahoo_client.py`

---

## 10. Limitations actuelles

- **Parsing HTML Yahoo Finance**: UNKNOWN si implémenté
- **Upsert intelligent**: UNKNOWN si implémenté (merge des données existantes)
- **Gestion des gaps**: Détection des jours manquants, mais UNKNOWN si automatique


