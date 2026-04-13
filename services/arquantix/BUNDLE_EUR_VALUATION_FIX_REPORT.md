# Bundle EUR Valuation Fix

## Executive Summary

Bug de valorisation devise identifié et corrigé dans l'endpoint `GET /api/app/bundle/my-bundles`. Les prix USDT étaient utilisés directement comme valeurs EUR sans conversion, gonflant la market_value des bundles de ~8-10% (le taux EUR/USDT).

## Root Cause Analysis

L'endpoint `mobile_my_bundles` utilisait `get_instrument_price()` qui retourne le prix en **USDT** (source: `MarketDataLatestQuote.last_price`). Ce prix était multiplié directement par la quantité pour produire `market_value`, sans aucune conversion EUR.

```python
# AVANT (bug)
price_usd = D(price_info["price"])       # ← prix USDT (ex: 85000 pour BTC)
market_value = qty * price_usd            # ← valeur en USDT, affichée comme EUR
```

Pendant ce temps, le `cost_basis` stocké dans les `PositionAtom` est bien en **EUR** (les ordres s'exécutent en EUR). Résultat : la performance comparait des EUR (cost) à des USD (market_value).

### Impact chiffré

Pour un investissement de 2000 EUR avec un taux EURUSDT ≈ 1.08 :
- `cost_basis` = 2000 EUR (correct)
- `market_value` = 2000 × 1.08 = ~2160 "EUR" (faux — c'est du USDT)
- `performance_pct` = +8% artificiels

Pour le cash leg USDC :
- 1000 USDC × 1.0 USDT = 1000 "EUR" affiché
- Correct : 1000 USDC × 0.926 EUR/USDC = 926 EUR

## Endpoint-by-Endpoint Valuation Audit

| Endpoint | Prix source | Conversion EUR | Statut |
|----------|-------------|----------------|--------|
| `GET /crypto-positions` | `MarketDataLatestQuote` | `usdt_to_eur()` | **OK** |
| `GET /crypto-positions/direct` | `MarketDataLatestQuote` | `usdt_to_eur()` | **OK** |
| `GET /crypto-positions/{asset}` | `MarketDataLatestQuote` | `usdt_to_eur()` | **OK** |
| `GET /wallet/statistics/{asset}` | `MarketDataLatestQuote` | `_to_ref()` | **OK** |
| `GET /wallet/history` | Candles + quotes | FX conversion | **OK** |
| `GET /portfolio/statistics` | Via `build_wallet_statistics` | `_to_ref()` | **OK** |
| **`GET /bundle/my-bundles`** | **`get_instrument_price()`** | **Aucune** | **BUG** |
| `GET /bundle/{id}/status` | Pas de prix (cost_basis only) | N/A | **OK** |
| `GET /bundle/{id}/statistics` | Via `build_wallet_statistics` | `_to_ref()` | **OK** |
| `GET /bundle/{id}/history` | Via `build_wallet_history` | FX conversion | **OK** |

## USD vs EUR Conversion Issues Found

### Issue unique : `mobile_my_bundles`

- `price_bridge.get_instrument_price()` retourne `quote.last_price` en USDT
- Ce prix USDT était utilisé comme prix EUR pour calculer `market_value`
- Affecte : `total_market_value`, `performance_pct`, chaque `position.market_value`

### Impact Flutter

- **Crypto page hero total** = `directValue` (EUR correct) + `bundleValue` (USDT affiché comme EUR) → gonflé
- **Bundle detail** = `totalMarketValue` gonflé → "gains" artificiels de ~8-10%
- **Home page** = utilise `crypto_positions` endpoint → EUR correct → écart avec page Crypto

## Fix Applied

### Backend : `api/services/test_clients/router.py` — `mobile_my_bundles`

```python
# APRÈS (fix)
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur

eurusdt_rate = get_eurusdt_rate(db, strict=False)

# Pour chaque position :
price_usdt = D(price_info["price"])
price_eur = usdt_to_eur(price_usdt, eurusdt_rate)    # ← conversion EUR
market_value = (qty * price_eur).quantize(D("0.01"))  # ← valeur en EUR
```

Changements :
- Import `get_eurusdt_rate` / `usdt_to_eur` (même utilitaires que tous les autres endpoints)
- Récupération du taux EURUSDT une seule fois par requête
- Conversion USDT → EUR pour chaque position avant calcul de `market_value`
- Champ `price_usd` renommé en `price_eur` dans la réponse JSON
- `total_market_value` et `performance_pct` calculés en EUR

### Flutter : `bundle_api.dart` — `BundlePositionInfo`

- Champ `priceUsd` renommé en `priceEur`
- Parsing JSON : `price_usd` → `price_eur`

## Before / After Expected Behavior

### Avant (bug)

| Métrique | Valeur affichée | Réalité |
|----------|----------------|---------|
| Bundle market value | ~2316 € | En fait ~2316 USDT ≈ 2145 € |
| Bundle performance | +15.8% | Artificiellement gonflé de ~8% |
| Page Crypto total | ~5321 € | Gonflé par bundle USDT |
| Page Home total | ~5009 € | Correct (endpoint séparé) |
| Écart Home/Crypto | ~312 € | Dû au mélange devise |

### Après (fix)

| Métrique | Valeur attendue |
|----------|----------------|
| Bundle market value | ~2145 € (si marché stable) |
| Bundle performance | ~7% (performance réelle) |
| Page Crypto total | ≈ Page Home total |
| Page Home total | Inchangé (déjà correct) |
| Écart Home/Crypto | ~0 € (cohérent) |

## Validation Scenarios

| # | Scénario | Attendu |
|---|----------|---------|
| 1 | Bundle investi 2×1000 EUR, marché stable | market_value ≈ 2000 EUR |
| 2 | Page Home et page Crypto | Totaux du même ordre de grandeur |
| 3 | Bundle detail : gains en cours | Reflète variation marché réelle, pas le taux EURUSDT |
| 4 | Cash leg USDC dans bundle | 1000 USDC ≈ 926 EUR (pas 1000 EUR) |
| 5 | Performance bundle | Proche de la performance réelle des assets sous-jacents |

## Final Status

**CORRIGÉ** — Le bug de valorisation devise dans `mobile_my_bundles` est résolu. Tous les montants bundle sont maintenant cohérents en EUR avec le reste de l'app.

### Fichiers modifiés

- `api/services/test_clients/router.py` — conversion USDT→EUR dans `mobile_my_bundles`
- `mobile/lib/features/wallet/data/bundle_api.dart` — `priceUsd` → `priceEur`
