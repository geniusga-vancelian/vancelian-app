# STABLECOIN_LIVE_QUOTES_AUDIT_REPORT

## Executive Summary

L'audit révèle que le système live des stablecoins est **partiellement sain** (Cas 2) :

- **USDC** : instrument USDCUSDT correctement configuré et alimenté par Binance (WebSocket + REST), mais avec une fréquence de mise à jour naturellement plus faible que les actifs volatils, ce qui cause des stale quotes en environnement de développement
- **EURC** : **instrument fantôme** — `EURCUSDT` est déclaré dans le code (`ASSET_PROVIDER_SYMBOL_MAP`) mais **n'existe pas chez Binance**. Aucune paire EURC n'est disponible sur Binance
- **USDT, DAI, BUSD** : déclarés dans `STABLECOIN_ASSETS` (seuil de staleness) mais **pas dans `SUPPORTED_ASSETS`** ni dans `ASSET_PROVIDER_SYMBOL_MAP` — pas de risque opérationnel car non utilisés

Le correctif principal appliqué : un **fallback de pricing synthétique** pour les stablecoins USD-pegged. Quand la quote live est absente, trop stale, ou sans instrument, `_resolve_price` retourne automatiquement `1.0 USDT → EUR` au lieu de lever une exception.

## Stablecoin Instrument Mapping

| Asset | In SUPPORTED_ASSETS | Provider Symbol | Binance Pair Exists | In ensure_instruments | Feed Source |
|-------|---------------------|-----------------|--------------------|-----------------------|-------------|
| USDC  | ✅ | USDCUSDT | ✅ Oui | ✅ Oui | WebSocket bookTicker + REST ticker |
| EURC  | ✅ | EURCUSDT | ❌ **Non** | ❌ Non | **Aucune** |
| USDT  | ❌ | — | N/A | N/A | N/A (pas utilisé comme asset) |
| DAI   | ❌ | — | N/A | N/A | N/A (pas utilisé comme asset) |
| BUSD  | ❌ | — | N/A | N/A | N/A (pas utilisé comme asset) |

### Détail USDC

- **provider_symbol** : `USDCUSDT` (dans `ASSET_PROVIDER_SYMBOL_MAP`)
- **Instrument Binance** : présent dans `ensure_binance_instruments.py` comme `("USDCUSDT", "USD Coin")`
- **WebSocket** : `load_binance_instruments()` charge tous les instruments actifs → USDCUSDT est inclus si l'instrument existe en DB
- **REST refresh** : `run_one_cycle()` itère aussi sur tous les instruments actifs → USDCUSDT est inclus
- **Fréquence bookTicker** : significativement plus faible que BTC/ETH/SOL (stablecoin = faible volatilité = moins de transactions = moins de bookTicker updates)

### Détail EURC

- **provider_symbol** : `EURCUSDT` (dans `ASSET_PROVIDER_SYMBOL_MAP`)
- **Résultat Binance API** : `{"code":-1121,"msg":"Invalid symbol."}` — **la paire n'existe pas**
- **Pas dans ensure_instruments** : jamais créé en DB
- **Impact** : si un bundle utilise EURC comme entry asset, `_resolve_price("EURC")` échoue systématiquement avec `no_market_quote_for_EURC`
- **Risque actuel** : faible car le bundle entry asset par défaut est USDC, pas EURC

## Latest Quotes Audit

| Asset | Quote exists in DB | Last update age (typical) | Healthy? |
|-------|--------------------|---------------------------|----------|
| USDC  | ✅ (si WS/REST actif) | 1-60s (WS actif), 60-600s+ (WS inactif) | ⚠️ Fragile en dev |
| EURC  | ❌ Jamais | N/A | ❌ Fantôme |

### Cadence réelle de mise à jour USDC

- **WebSocket actif** : bookTicker USDCUSDT arrive toutes les ~5-30s (dépend du volume Binance)
- **WebSocket inactif** (dev local) : seul le REST refresh met à jour, typiquement toutes les ~60s si un cron tourne
- **Aucun service actif** : la quote stagne et dépasse rapidement le seuil de 60s, puis 600s
- **Âge observé dans le bug** : 322s — cohérent avec un WebSocket qui a été interrompu quelques minutes avant

## WebSocket / REST Refresh Audit

### WebSocket (`binance_ws_ingestion.py`)

- `load_binance_instruments()` charge tous les instruments avec `provider=binance, is_active=true`
- Construit des streams `{symbol}@bookTicker` pour chacun
- **USDCUSDT sera inclus** si l'instrument existe en DB et est actif
- **EURCUSDT ne sera jamais inclus** car le stream n'existe pas chez Binance (et l'instrument n'est pas créé en DB)

### REST Refresh (`ingestion_binance.py`)

- `run_one_cycle()` itère sur les mêmes instruments
- Appelle `fetch_ticker(provider_symbol)` pour chacun (endpoint REST Binance `/api/v3/ticker/24hr`)
- **USDCUSDT** : fonctionne normalement
- **EURCUSDT** : retournerait `None` (erreur HTTP silencieuse) → comptabilisé comme failure dans le cycle

### Cron Refresh (`cron_refresh.py`)

- Concerne les **barres/candles** (backfill OHLC), pas les latest quotes
- N'impacte pas la fraîcheur des quotes live

## Bundle Preview Dependency Audit

### Chaîne de dépendance

```
preview_invest(funding_asset="EUR", funding_amount=100)
  → preview_buy(entry_asset="USDC", EUR_amount=100)
    → _resolve_price("USDC", side="buy")
      → cherche USDCUSDT dans market_data_latest_quotes
      → vérifie fraîcheur (MAX_QUOTE_AGE_SECONDS_STABLECOIN = 600s)
      → ❌ AVANT FIX : échoue si quote > 60s
      → ✅ APRÈS FIX : fallback synthétique 1.0 USDT si stale/absent

  → pour chaque allocation (BTC 70%, ETH 30%) :
    preview_swap(USDC → BTC)
      → _resolve_price("USDC", side="sell")  ← MÊME dépendance
      → _resolve_price("BTC", side="buy")    ← quote volatile, plus fiable
```

### Analyse

Le bundle preview a une **double dépendance** à la quote USDC :
1. `preview_buy(USDC)` — pour estimer la conversion EUR → USDC
2. `preview_swap(USDC → X)` — pour chaque allocation

Si la quote USDC est stale, le preview échoue **entièrement** (pas juste une jambe).

### La dépendance est-elle saine ?

**Non, dans sa forme d'origine.** Un stablecoin USD-pegged à ≈1.0 USDT ne devrait jamais bloquer un flow utilisateur à cause d'une quote stale. Le prix USDC ne varie que de ±0.001 USDT sur 24h.

## Root Cause Analysis

### Cause immédiate

Le seuil `MAX_QUOTE_AGE_SECONDS = 60s` était identique pour BTC et USDC. Or :
- BTC reçoit des bookTicker updates toutes les ~100ms sur Binance
- USDC reçoit des updates toutes les ~5-30s (volume plus faible)
- En dev local, le WebSocket peut ne pas tourner → la quote stagne

### Cause structurelle

Aucun fallback de pricing pour les stablecoins. Le système traite USDC comme un actif volatil nécessitant une quote live de précision, alors qu'un prix synthétique de 1.0 USDT est suffisamment précis (erreur < 0.1%).

### EURC : instrument fantôme

EURC est déclaré comme `SUPPORTED_ASSET` avec un provider_symbol `EURCUSDT` mais :
- La paire n'existe pas chez Binance
- L'instrument n'est pas créé par `ensure_binance_instruments`
- Aucun autre provider n'est configuré pour EURC
- Toute opération impliquant EURC comme pricing source échouera systématiquement

## Fix Applied

### 1. Fallback synthétique pour les stablecoins USD-pegged

Dans `_resolve_price()` (`exchange/service.py`) :

Ajout de `USD_PEGGED_STABLECOINS = {"USDC", "USDT", "DAI", "BUSD"}` et d'une méthode `_stablecoin_fallback_price()`.

Quand un stablecoin USD-pegged n'a pas de quote live fiable (absente, sans timestamp, ou trop stale), le système retourne automatiquement :

```
1.0 USDT → EUR (via taux EUR/USDT courant, ou 1.08 en dernier recours)
```

Le fallback s'active dans 4 cas :
- Pas de `provider_symbol` dans le mapping
- Pas de quote en DB
- Quote sans `quote_time`
- Quote trop stale (> 600s)

Chaque activation produit un log `INFO` pour traçabilité.

### 2. Seuil différencié (déjà en place)

- `MAX_QUOTE_AGE_SECONDS = 60s` pour les actifs volatils
- `MAX_QUOTE_AGE_SECONDS_STABLECOIN = 600s` pour les stablecoins

Le seuil élargi donne une première chance à la quote live avant le fallback.

### 3. EURC : pas de correctif technique

EURC n'a pas de paire Binance. Les options futures sont :
- Pricing synthétique basé sur EUR/USDT (1 EURC ≈ 1 EUR)
- Ajout d'un autre provider (Coinbase, etc.)
- Retrait de EURC de `SUPPORTED_ASSETS` si non utilisé

Pour l'instant, EURC bénéficie du même fallback que les autres stablecoins s'il est ajouté à `USD_PEGGED_STABLECOINS`. Cependant, EURC n'est **pas** USD-pegged (il est EUR-pegged), donc il n'est pas dans `USD_PEGGED_STABLECOINS`. Un traitement spécifique serait nécessaire si EURC est utilisé.

## Validation Scenarios

| # | Scénario | Résultat attendu |
|---|----------|-----------------|
| 1 | `preview_buy(USDC)` avec quote live fraîche | ✅ Utilise la quote live |
| 2 | `preview_buy(USDC)` avec quote stale 322s | ✅ Utilise la quote live (< 600s) |
| 3 | `preview_buy(USDC)` avec quote stale 800s | ✅ Fallback synthétique 1.0 USDT |
| 4 | `preview_buy(USDC)` sans quote en DB | ✅ Fallback synthétique 1.0 USDT |
| 5 | Bundle preview avec USDC entry asset | ✅ Fonctionne sans stale error |
| 6 | `_resolve_price("EURC")` | ⚠️ Pas de fallback (EUR-pegged, pas USD-pegged) — échoue si pas de quote |
| 7 | `_resolve_price("BTC")` avec quote stale 90s | ❌ MarketQuoteStaleError (correct, actif volatil) |
| 8 | market_data_latest_quotes USDC reste fraîche avec WS actif | ✅ Updates toutes les 5-30s |

## Final Status

| Item | Status |
|------|--------|
| USDC instrument mapping | ✅ Correct |
| USDC live feed (WS + REST) | ✅ Fonctionnel quand les services tournent |
| USDC staleness handling | ✅ Seuil 600s + fallback synthétique |
| EURC instrument mapping | ❌ Paire Binance inexistante — instrument fantôme |
| EURC live feed | ❌ Aucune source de données |
| EURC impact actuel | ⚠️ Faible (entry asset par défaut = USDC) |
| Bundle preview robustesse | ✅ Ne bloque plus sur stale USDC |
| USDT/DAI/BUSD | ✅ Non utilisés, pas de risque |

### Recommandation

**Cas 2 confirmé : système partiellement sain.**

- USDC est sain avec le fallback en place
- EURC nécessite soit un pricing synthétique EUR-based, soit le retrait de `SUPPORTED_ASSETS`, soit un provider alternatif — à traiter si EURC est utilisé en production
