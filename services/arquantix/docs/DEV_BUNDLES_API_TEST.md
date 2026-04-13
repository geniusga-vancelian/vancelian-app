# Tests API Bundles - Guide de développement

## Architecture

- **Table prix D1**: `market_data_bars_d1` (modèle: `MarketDataBarD1`)
- **Module centralisé**: `api/services/market_data/bars_d1_repo.py`
  - Utilisé par preview ET backtests (DRY)
  - Fonctions: `get_bars_d1()`, `get_price_dataframe()`, `get_available_date_range()`
- **Exceptions dédiées**: `api/services/bundles/exceptions.py`
  - `BundleValidationError` (400)
  - `BundleCycleError` (400)
  - `DynamicRuleInvalid` (400)
  - `InsufficientMarketData` (422)

## Prérequis

1. **Migration de base de données**
   ```bash
   cd api
   alembic upgrade head
   ```

2. **Vérifier que les services sont démarrés**
   - FastAPI backend sur le port configuré
   - PostgreSQL accessible
   - Données de prix disponibles dans `market_data_bars_d1`

## Tests avec curl

### 1. Créer un bundle fixed_instruments

```bash
curl -X POST "http://localhost:8000/api/bundles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Crypto Top 3",
    "asset_class": "crypto",
    "type": "fixed_instruments",
    "description": "Top 3 cryptos equal weight",
    "is_active": true,
    "components": [
      {
        "component_type": "instrument",
        "instrument_code": "BTCUSD",
        "weight": 33.3333
      },
      {
        "component_type": "instrument",
        "instrument_code": "ETHUSD",
        "weight": 33.3333
      },
      {
        "component_type": "instrument",
        "instrument_code": "SOLUSD",
        "weight": 33.3334
      }
    ]
  }'
```

### 2. Créer un bundle composite_fixed

```bash
# D'abord créer un bundle enfant
curl -X POST "http://localhost:8000/api/bundles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Crypto Core",
    "asset_class": "crypto",
    "type": "fixed_instruments",
    "components": [
      {"component_type": "instrument", "instrument_code": "BTCUSD", "weight": 50.0},
      {"component_type": "instrument", "instrument_code": "ETHUSD", "weight": 50.0}
    ]
  }'

# Notez l'ID du bundle créé (ex: 1), puis créez le bundle composite
curl -X POST "http://localhost:8000/api/bundles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Crypto Portfolio",
    "asset_class": "crypto",
    "type": "composite_fixed",
    "components": [
      {
        "component_type": "bundle",
        "child_bundle_id": 1,
        "weight": 60.0
      },
      {
        "component_type": "instrument",
        "instrument_code": "SOLUSD",
        "weight": 40.0
      }
    ]
  }'
```

### 3. Créer un bundle dynamic

```bash
curl -X POST "http://localhost:8000/api/bundles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Dynamic Crypto",
    "asset_class": "crypto",
    "type": "dynamic",
    "components": [
      {
        "component_type": "instrument",
        "instrument_code": "BTCUSD",
        "weight": 50.0
      },
      {
        "component_type": "instrument",
        "instrument_code": "ETHUSD",
        "weight": 50.0
    ],
    "dynamic_rule": {
      "rule_type": "formula_dsl",
      "rule_json": {
        "type": "weights",
        "items": [
          {
            "instrument": "BTCUSD",
            "expr": {
              "op": "clip",
              "min": 0.3,
              "max": 0.7,
              "value": {
                "op": "ratio",
                "a": {
                  "op": "sma",
                  "instrument": "BTCUSD",
                  "window": 50,
                  "field": "close"
                },
                "b": {
                  "op": "sma",
                  "instrument": "BTCUSD",
                  "window": 200,
                  "field": "close"
                }
              }
            }
          },
          {
            "instrument": "ETHUSD",
            "expr": {
              "op": "const",
              "value": 0.2
            }
          }
        ],
        "post": {
          "op": "normalize_to_one"
        }
      }
    }
  }'
```

### 4. Lister les bundles

```bash
curl -X GET "http://localhost:8000/api/bundles?asset_class=crypto" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Obtenir les détails d'un bundle

```bash
curl -X GET "http://localhost:8000/api/bundles/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 6. Preview d'un bundle (fixed/composite)

```bash
curl -X POST "http://localhost:8000/api/bundles/1/preview?date=2025-01-09" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 7. Preview d'un bundle dynamic

```bash
curl -X POST "http://localhost:8000/api/bundles/3/preview?date=2025-01-09" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 8. Mettre à jour un bundle

```bash
curl -X PUT "http://localhost:8000/api/bundles/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Crypto Top 3 Updated",
    "components": [
      {"component_type": "instrument", "instrument_code": "BTCUSD", "weight": 40.0},
      {"component_type": "instrument", "instrument_code": "ETHUSD", "weight": 30.0},
      {"component_type": "instrument", "instrument_code": "SOLUSD", "weight": 30.0}
    ]
  }'
```

### 9. Supprimer un bundle

```bash
curl -X DELETE "http://localhost:8000/api/bundles/1" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Codes de réponse attendus

- **201**: Bundle créé avec succès
- **200**: Bundle récupéré/mis à jour avec succès
- **204**: Bundle supprimé avec succès
- **400**: Erreur de validation (weights sum != 100, cycle détecté, etc.)
- **404**: Bundle non trouvé
- **422**: Données de marché insuffisantes pour preview (dynamic bundles)

## Validation des erreurs

### Test: weights ne somment pas à 100%

```bash
curl -X POST "http://localhost:8000/api/bundles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Invalid Bundle",
    "asset_class": "crypto",
    "type": "fixed_instruments",
    "components": [
      {"component_type": "instrument", "instrument_code": "BTCUSD", "weight": 50.0},
      {"component_type": "instrument", "instrument_code": "ETHUSD", "weight": 30.0}
    ]
  }'
```

**Attendu**: 400 Bad Request avec message "Component weights must sum to 100.0"

### Test: Cycle détecté

```bash
# Créer bundle A qui référence bundle B
# Puis créer bundle B qui référence bundle A
# Attendu: 400 Bad Request avec message "Cycle detected"
```

### Test: Dynamic rule sans normalize_to_one

```bash
curl -X POST "http://localhost:8000/api/bundles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "Invalid Dynamic",
    "asset_class": "crypto",
    "type": "dynamic",
    "components": [
      {"component_type": "instrument", "instrument_code": "BTCUSD", "weight": 100.0}
    ],
    "dynamic_rule": {
      "rule_json": {
        "type": "weights",
        "items": [
          {"instrument": "BTCUSD", "expr": {"op": "const", "value": 1.0}}
        ]
      }
    }
  }'
```

**Attendu**: 400 Bad Request avec message "rule_json.post.op must be 'normalize_to_one'"

## Notes

- Les tokens JWT doivent être obtenus via l'endpoint d'authentification
- Les dates doivent être au format YYYY-MM-DD
- Les weights sont en pourcentage (0-100), pas en fraction (0-1)
- Pour les dynamic bundles, assurez-vous d'avoir suffisamment de données historiques (250 jours minimum pour SMA)

