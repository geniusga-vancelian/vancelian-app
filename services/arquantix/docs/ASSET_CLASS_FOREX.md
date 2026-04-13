# Asset Class FOREX

## Vue d'ensemble

La classe d'actif **FOREX** permet de gérer les paires de devises (EUR/USD, USD/JPY, GBP/USD, etc.) dans le système Arquantix.

## Conventions de nommage

### Format interne (instrument_code)

Les instruments FOREX sont stockés dans la base de données avec un code normalisé **sans séparateur** :

- **EURUSD** (et non EUR-USD ou EUR/USD)
- **USDJPY** (et non USD-JPY ou USD/JPY)
- **GBPUSD** (et non GBP-USD ou GBP/USD)

### Format Yahoo Finance (provider_symbol)

Le symbole Yahoo Finance peut contenir des séparateurs ou le suffixe `=X` :

- **EURUSD=X** (format standard Yahoo)
- **EUR-USD** (format alternatif Yahoo)
- **EURUSD** (format simple, sera normalisé)

Lors de l'ingestion, le système :
- Normalise automatiquement `instrument_code` en format sans séparateur
- Conserve le format Yahoo original dans `provider_symbol`
- Si `provider_symbol` n'est pas fourni, génère automatiquement `EURUSD=X`

## Détection automatique

Lors de l'ingestion depuis une URL Yahoo Finance, le système détecte automatiquement FOREX si :

1. Le ticker se termine par `=X` (ex: `EURUSD=X`)
2. Le ticker fait 7 caractères avec un tiret (ex: `EUR-USD`)

Exemple :
```
https://finance.yahoo.com/quote/EURUSD=X/history
→ Détection automatique : asset_class = "FOREX"
→ instrument_code = "EURUSD"
→ provider_symbol = "EURUSD=X"
```

## Weekend Trading

Par défaut, les instruments FOREX ont `weekend_tradable = false`.

**Note** : Le trading FOREX est techniquement ouvert 24/7, mais les données historiques Yahoo Finance sont généralement fermées le weekend. Le système suit la convention des données disponibles.

Pour forcer le weekend trading dans un backtest, utilisez le paramètre `allow_weekend_trading` au niveau du backtest.

## Ingestion

### Via HTML Table (Yahoo Finance)

1. Aller sur la page Yahoo Finance "Historical Data" pour une paire (ex: EURUSD=X)
2. Copier le HTML de la table
3. Coller dans l'admin Market Data
4. Sélectionner Asset Class: **FOREX**
5. Entrer Instrument Code: **EURUSD** (sans séparateur)
6. Provider Symbol (optionnel): **EURUSD=X** (sera généré automatiquement si non fourni)

### Via CSV Upload

1. Télécharger le CSV depuis Yahoo Finance
2. Utiliser le formulaire CSV Upload
3. Sélectionner Asset Class: **FOREX**
4. Entrer Instrument Code: **EURUSD** (sera normalisé automatiquement)

### Via URL (Automatique)

```
POST /api/market-data/yahoo/ingest-from-url
{
  "url": "https://finance.yahoo.com/quote/EURUSD=X/history",
  "instrument_code": "EURUSD"
}
```

Le système détectera automatiquement `asset_class = "FOREX"` grâce au suffixe `=X`.

## Bundles

### Bundle Fixed Instruments

Exemple : Bundle "FX Majors"

```json
{
  "name": "FX Majors",
  "asset_class": "forex",
  "type": "fixed_instruments",
  "components": [
    {
      "component_type": "instrument",
      "instrument_code": "EURUSD",
      "weight": 33.33
    },
    {
      "component_type": "instrument",
      "instrument_code": "USDJPY",
      "weight": 33.33
    },
    {
      "component_type": "instrument",
      "instrument_code": "GBPUSD",
      "weight": 33.34
    }
  ]
}
```

**Règles** :
- Tous les instruments doivent appartenir à la même asset class (`forex`)
- Les poids doivent sommer à 100%
- Les instruments doivent exister dans la DB avec `provider = "yahoo"` et `is_active = "true"`

### Bundle Composite

Un bundle FOREX peut contenir d'autres bundles FOREX :

```json
{
  "name": "FX Balanced",
  "asset_class": "forex",
  "type": "composite_fixed",
  "components": [
    {
      "component_type": "bundle",
      "child_bundle_id": 1,  // "FX Majors"
      "weight": 50.0
    },
    {
      "component_type": "bundle",
      "child_bundle_id": 2,  // "FX Exotics"
      "weight": 50.0
    }
  ]
}
```

### Bundle Dynamic

Les bundles dynamiques peuvent utiliser des règles DSL pour ajuster les poids FOREX en fonction de la volatilité, des corrélations, etc.

**Exemple** : Rééquilibrer en fonction de la volatilité inverse

```json
{
  "name": "FX Volatility Inverse",
  "asset_class": "forex",
  "type": "dynamic",
  "dynamic_rule": {
    "rule_type": "formula_dsl",
    "rule_json": {
      "type": "weights",
      "items": [
        {
          "instrument_code": "EURUSD",
          "op": {
            "type": "ratio",
            "numerator": {"type": "const", "value": 1},
            "denominator": {
              "type": "volatility",
              "instrument_code": "EURUSD",
              "lookback_days": 30
            }
          }
        },
        {
          "instrument_code": "USDJPY",
          "op": {
            "type": "ratio",
            "numerator": {"type": "const", "value": 1},
            "denominator": {
              "type": "volatility",
              "instrument_code": "USDJPY",
              "lookback_days": 30
            }
          }
        }
      ],
      "post": {
        "op": "normalize_to_one"
      }
    }
  }
}
```

## Backtests

### Backtest simple avec FOREX

```json
{
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "instrument_ids": [1, 2, 3],  // EURUSD, USDJPY, GBPUSD
  "strategy": {
    "type": "equal_weight"
  },
  "rebalance": "weekly",
  "allow_weekend_trading": false,  // FOREX par défaut
  "fees_bps": 5,
  "slippage_bps": 2
}
```

### Backtest avec Bundle FOREX

```json
{
  "start_date": "2023-01-01",
  "end_date": "2024-01-01",
  "bundle_id": 10,  // Bundle "FX Majors"
  "rebalance": "weekly",
  "allow_weekend_trading": false,
  "fees_bps": 5,
  "slippage_bps": 2
}
```

**Comportement** :
- Le bundle est résolu en poids fixes pour chaque instrument FOREX
- À chaque date de rééquilibrage, le portefeuille revient aux poids cibles du bundle
- `allow_weekend_trading` peut être `true` pour forcer le trading le weekend (si les données sont disponibles)

## Charts

Les charts FOREX supportent :

1. **Line Chart** : Prix de clôture (Close)
2. **Candlestick Chart** : OHLC (Open, High, Low, Close)

Les données proviennent de `market_data_bars_d1` avec `source = "yahoo"`.

**Endpoint** :
```
GET /api/market-data/candles?instrument_code=EURUSD&provider=yahoo&start=2023-01-01&end=2024-01-01&tf=1d
```

## Validation

### Schémas Pydantic

- `BundleBase.asset_class` : Accepte `"forex"` (lowercase)
- `YahooIngestHtmlRequest.asset_class` : Accepte `"FOREX"` (uppercase ou lowercase)
- `InstrumentBase.asset_class` : Pattern regex accepte `"forex"`

### Comparaisons case-insensitive

Les validations de correspondance d'asset class dans les bundles sont **case-insensitive** :

```python
if instrument.asset_class.lower() != bundle.asset_class.lower():
    raise HTTPException(...)
```

Cela garantit que `"forex"`, `"FOREX"`, et `"Forex"` sont tous acceptés.

## Exemples pratiques

### 1. Créer un instrument FOREX via HTML

1. Aller sur https://finance.yahoo.com/quote/EURUSD=X/history
2. Copier le HTML de la table historique
3. Dans `/admin/market-data` :
   - Coller le HTML
   - Instrument Code: `EURUSD`
   - Asset Class: `FOREX`
   - Cliquer "Validate"
   - Si OK, cliquer "Add Delta Only"

### 2. Créer un bundle FOREX "FX Majors"

1. Aller sur `/admin/bundles/new`
2. Asset Class: `forex`
3. Type: `Fixed Instruments`
4. Ajouter composants :
   - EURUSD: 33.33%
   - USDJPY: 33.33%
   - GBPUSD: 33.34%
5. Créer le bundle

### 3. Lancer un backtest avec le bundle

1. Aller sur `/admin/backtests`
2. Asset Class: `forex`
3. Bundle: Sélectionner "FX Majors"
4. Dates: 2023-01-01 à 2024-01-01
5. Rééquilibrage: `weekly`
6. Allow Weekend Trading: `false` (par défaut pour FOREX)
7. Lancer le backtest

## Limitations et notes

1. **Données Yahoo Finance** : Les données FOREX peuvent être incomplètes le weekend. Le système suit les données disponibles.

2. **Provider unique** : Actuellement, seul Yahoo Finance est supporté pour FOREX (`provider = "yahoo"`).

3. **Volume** : Le volume FOREX dans Yahoo Finance représente le volume de contrats, pas les montants notionnels.

4. **Weekend Trading** : Par défaut `false`, mais peut être overridé dans les backtests si nécessaire.

## Support

Pour toute question ou problème avec FOREX, vérifier :
1. Le format de `instrument_code` (doit être sans séparateur)
2. L'asset_class en DB (doit être `"forex"` en lowercase)
3. Le `provider_symbol` Yahoo (peut contenir `=X` ou tiret)
4. La correspondance asset_class dans les bundles (case-insensitive)

