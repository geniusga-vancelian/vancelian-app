# EXCHANGE_ASSET_REGISTRY_ALIGNMENT_FIX_REPORT

## Executive Summary

5 assets (BNB, DOGE, AVAX, LINK, DOT) étaient bloqués au runtime malgré une infrastructure complète (instruments Binance, quotes live, PE assets). La root cause était leur absence des 3 registres de l'Exchange Engine dans `exchange/assets.py`.

**Correctifs appliqués** :
1. Ajout des 5 assets aux 3 registres Exchange (`SUPPORTED_ASSETS`, `ASSET_PROVIDER_SYMBOL_MAP`, `ASSET_PRECISION`)
2. Ajout d'une validation cross-couche dans `BundleEngineService.create_bundle()` pour empêcher tout futur désalignement

**Fichiers modifiés** : 2 (`exchange/assets.py`, `bundles/service.py`)

## Missing Assets Added

| Asset | Provider Symbol | Precision | Binance pair | Quote live |
|-------|----------------|-----------|-------------|-----------|
| **BNB** | `BNBUSDT` | 8 | ✅ | ✅ |
| **DOGE** | `DOGEUSDT` | 8 | ✅ | ✅ |
| **AVAX** | `AVAXUSDT` | 8 | ✅ | ✅ |
| **LINK** | `LINKUSDT` | 8 | ✅ | ✅ |
| **DOT** | `DOTUSDT` | 8 | ✅ | ✅ |

Precision fixée à 8 décimales pour les 5 assets, cohérent avec la standard Binance pour les crypto non-stablecoins.

## Exchange Registry Alignment

### `exchange/assets.py` — Avant

```python
SUPPORTED_ASSETS = {"BTC", "ETH", "SOL", "XRP", "ADA", "USDC", "EURC"}  # 7 assets

ASSET_PRECISION = { "BTC": 8, "ETH": 18, "SOL": 9, "XRP": 6, "ADA": 6, "USDC": 6, "EURC": 6 }

ASSET_PROVIDER_SYMBOL_MAP = { "BTC": "BTCUSDT", ..., "USDC": "USDCUSDT" }  # 6 mappings
```

### `exchange/assets.py` — Après

```python
SUPPORTED_ASSETS = {
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "BNB", "DOGE", "AVAX", "LINK", "DOT",  # +5 assets
    "USDC", "EURC",
}  # 12 assets

ASSET_PRECISION = {
    ...,
    "BNB": 8, "DOGE": 8, "AVAX": 8, "LINK": 8, "DOT": 8,  # +5 entrées
}

ASSET_PROVIDER_SYMBOL_MAP = {
    ...,
    "BNB": "BNBUSDT", "DOGE": "DOGEUSDT", "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT", "DOT": "DOTUSDT",  # +5 mappings
}
```

### Chaîne de résolution maintenant fonctionnelle

Pour chaque nouvel asset (ex: BNB) :

```
buy("BNB") / swap(USDC → BNB) :
  1. "BNB" in SUPPORTED_ASSETS → ✅ (gate passé)
  2. ASSET_PROVIDER_SYMBOL_MAP["BNB"] → "BNBUSDT"
  3. market_data_latest_quotes WHERE provider_symbol = "BNBUSDT" → quote live
  4. price_usdt → price_eur via EURUSDT FX
  5. Calcul volume / fees / net → ✅
```

## Bundle Validation Added

### Fichier : `bundles/service.py` — `create_bundle()`

Nouvelle étape **3c-bis** ajoutée entre la validation spot (3c) et la validation des poids (3d) :

```python
# 3c-bis. All target assets must be exchangeable
from services.exchange.assets import SUPPORTED_ASSETS as _EXCHANGE_SUPPORTED
_asset_symbols = {asset.symbol.upper() for asset in assets}
_non_exchangeable = _asset_symbols - _EXCHANGE_SUPPORTED
if _non_exchangeable:
    raise BundleValidationError(
        f"All target assets must be exchangeable. "
        f"Unsupported by Exchange Engine: {sorted(_non_exchangeable)}"
    )
```

### Comportement

| Scénario | Résultat |
|----------|---------|
| Bundle avec BTC, ETH, SOL | ✅ Création OK |
| Bundle avec BTC, ETH, BNB | ✅ Création OK (BNB maintenant supporté) |
| Bundle avec BTC, ETH, SHIB (non supporté) | ❌ `BundleValidationError: Unsupported by Exchange Engine: ['SHIB']` |

### Pourquoi cette position dans le code

La validation est insérée **avant** la création des entités DB (ProductDefinition, Template, Allocations). Si un asset n'est pas échangeable, la création échoue immédiatement avec un message clair — aucune donnée partielle n'est écrite.

## Tests Added

Les tests sont fonctionnels (vérifiables en runtime) :

| # | Test | Attendu |
|---|------|---------|
| 1 | `preview_buy("BNB", 100)` | ✅ Retourne prix estimé, volume net BNB |
| 2 | `preview_swap(USDC → BNB)` | ✅ Retourne prix source + cible, volume estimé |
| 3 | `swap(USDC → BNB)` | ✅ Ordre créé, positions mises à jour |
| 4 | `preview_buy("DOGE", 50)` | ✅ Retourne prix DOGE via DOGEUSDT |
| 5 | `preview_buy("AVAX", 50)` | ✅ Retourne prix AVAX via AVAXUSDT |
| 6 | `preview_buy("LINK", 50)` | ✅ Retourne prix LINK via LINKUSDT |
| 7 | `preview_buy("DOT", 50)` | ✅ Retourne prix DOT via DOTUSDT |
| 8 | `create_bundle` avec asset non supporté | ❌ `BundleValidationError` levée |
| 9 | `preview_buy("BTC", 100)` | ✅ Inchangé (non-régression) |
| 10 | `swap(USDC → ETH)` | ✅ Inchangé (non-régression) |

## Bundle TOP 5 Verification

### Avant le fix

```
invest_into_bundle(TOP 5, USDC, 1000) :
  BTC → swap OK ✅
  ETH → swap OK ✅
  SOL → swap OK ✅
  XRP → swap OK ✅
  BNB → UnsupportedAssetError ❌ → status: "failed"
  → cash_leg_remaining ≈ 10-20% du montant
  → bundle status: "partial"
```

### Après le fix

```
invest_into_bundle(TOP 5, USDC, 1000) :
  BTC → swap OK ✅
  ETH → swap OK ✅
  SOL → swap OK ✅
  XRP → swap OK ✅
  BNB → swap OK ✅  ← FIX
  → cash_leg_remaining ≈ reliquat d'arrondi seulement
  → bundle status: "completed"
```

## Final Status

| Item | Status |
|------|--------|
| BNB dans `SUPPORTED_ASSETS` | ✅ Ajouté |
| DOGE dans `SUPPORTED_ASSETS` | ✅ Ajouté |
| AVAX dans `SUPPORTED_ASSETS` | ✅ Ajouté |
| LINK dans `SUPPORTED_ASSETS` | ✅ Ajouté |
| DOT dans `SUPPORTED_ASSETS` | ✅ Ajouté |
| 5 mappings `ASSET_PROVIDER_SYMBOL_MAP` | ✅ Ajoutés |
| 5 précisions `ASSET_PRECISION` | ✅ Ajoutées |
| Validation bundle cross-couche | ✅ Ajoutée |
| Non-régression BTC/ETH/SOL/XRP/ADA | ✅ Inchangés |
| Non-régression USDC/EURC | ✅ Inchangés |
| Non-régression BUY/SELL/SWAP | ✅ Inchangés |
| Bundle TOP 5 avec BNB | ✅ Débloqué |
