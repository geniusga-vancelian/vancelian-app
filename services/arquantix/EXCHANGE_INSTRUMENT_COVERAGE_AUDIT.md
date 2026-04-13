# EXCHANGE_INSTRUMENT_COVERAGE_AUDIT

## Executive Summary

L'audit révèle un **désalignement structurel entre 4 couches** du système, qui fait que certains assets sont visibles dans l'app (catalogue, bundles, markets) mais **non échangeables** au runtime.

**Root cause principale** : `SUPPORTED_ASSETS` (Exchange Engine gate) ne contient que **7 assets** (BTC, ETH, SOL, XRP, ADA, USDC, EURC), alors que le PE (Portfolio Engine), les instruments Binance, et les bundles utilisent **11+ assets** (BTC, ETH, SOL, XRP, BNB, ADA, DOGE, USDC, AVAX, LINK, DOT).

Tout appel `buy()`, `sell()`, `swap()`, `preview_buy()`, `preview_swap()` passe par le guard :

```python
if asset not in SUPPORTED_ASSETS:
    raise UnsupportedAssetError(f"unsupported_asset: {asset}")
```

Les assets absents de `SUPPORTED_ASSETS` échouent immédiatement avec cette erreur, **avant même** de tenter de résoudre un prix.

---

## Asset Coverage Table

| Asset | `SUPPORTED_ASSETS` | `ASSET_PROVIDER_SYMBOL_MAP` | `ASSET_PRECISION` | `ensure_binance_instruments` | `seed_pe_crypto_assets` | PE Instrument | Binance pair exists | Quote live | BUY | SELL | SWAP | Bundle usable |
|-------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **BTC** | ✅ | ✅ BTCUSDT | ✅ 8 | ✅ | ✅ | ✅ BTC-SPOT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **ETH** | ✅ | ✅ ETHUSDT | ✅ 18 | ✅ | ✅ | ✅ ETH-SPOT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SOL** | ✅ | ✅ SOLUSDT | ✅ 9 | ✅ | ✅ | ✅ SOL-SPOT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **XRP** | ✅ | ✅ XRPUSDT | ✅ 6 | ✅ | ✅ | ✅ XRP-SPOT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **ADA** | ✅ | ✅ ADAUSDT | ✅ 6 | ✅ | ✅ | ✅ ADA-SPOT | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **USDC** | ✅ | ✅ USDCUSDT | ✅ 6 | ✅ | ✅ | ✅ USDC-SPOT | ✅ | ⚠️ stale fallback | ✅ | ✅ | ✅ | ✅ (entry asset) |
| **EURC** | ✅ | ❌ retiré | ✅ 6 | ❌ | ❌ | ❌ | ❌ EURCUSDT invalide | ❌ fallback 1.0 EUR | ✅* | ✅* | ✅* | ⚠️ non default |
| **BNB** | ❌ | ❌ | ❌ | ✅ BNBUSDT | ✅ BNB-SPOT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **DOGE** | ❌ | ❌ | ❌ | ✅ DOGEUSDT | ✅ DOGE-SPOT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **AVAX** | ❌ | ❌ | ❌ | ✅ AVAXUSDT | ✅ AVAX-SPOT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **LINK** | ❌ | ❌ | ❌ | ✅ LINKUSDT | ✅ LINK-SPOT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **DOT** | ❌ | ❌ | ❌ | ✅ DOTUSDT | ✅ DOT-SPOT | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

\* EURC : fonctionne via fallback EUR-pegged, mais aucun vrai feed marché.

---

## Broken Assets Analysis

### Catégorie 1 — Assets totalement OK (6)

**BTC, ETH, SOL, XRP, ADA, USDC**

Chaîne complète fonctionnelle :
- Déclarés dans `SUPPORTED_ASSETS`
- Mapping `ASSET_PROVIDER_SYMBOL_MAP` correct
- Precision définie dans `ASSET_PRECISION`
- Instrument Binance créé (`ensure_binance_instruments`)
- PE asset + instrument seedé (`seed_pe_crypto_assets`)
- Quote live alimentée (WebSocket / REST)
- `_resolve_price()` fonctionne
- `buy()` / `sell()` / `swap()` fonctionnent

### Catégorie 2 — Asset avec fallback seulement (1)

**EURC**

- Déclaré `SUPPORTED_ASSETS` : ✅
- Mapping : ❌ retiré (EURCUSDT n'existe pas chez Binance)
- Fallback : `_eur_pegged_fallback_price()` → `1.0 EUR`
- Fonctionnel via fallback synthétique
- Pas de vrai feed marché
- Non utilisé comme entry asset par défaut

### Catégorie 3 — Assets totalement non échangeables (5)

**BNB, DOGE, AVAX, LINK, DOT**

| Couche | Status |
|--------|--------|
| `SUPPORTED_ASSETS` | ❌ **ABSENT** — c'est le bloquant |
| `ASSET_PROVIDER_SYMBOL_MAP` | ❌ ABSENT |
| `ASSET_PRECISION` | ❌ ABSENT |
| `ensure_binance_instruments` | ✅ Instrument créé |
| `seed_pe_crypto_assets` | ✅ PE asset + instrument |
| Binance pair | ✅ Valide (BNBUSDT, etc.) |
| Quote live | ✅ Alimentée |
| `_resolve_price()` | ❌ `PriceUnavailableError: no_provider_symbol_for_BNB` |
| `preview_buy()` | ❌ `UnsupportedAssetError` (gate line 139) |
| `swap()` | ❌ `UnsupportedAssetError` (gate line 777) |
| Bundle allocation | ❌ Échec au swap (status "failed") |

**Ces 5 assets ont une infrastructure complète** (instruments Binance, PE instruments, quotes live), mais sont bloqués par 3 registres manquants dans `exchange/assets.py`.

---

## BNB Deep Dive

### Chaîne de résolution

```
Bundle invest → BundleOrchestrator.invest_into_bundle()
  → _execute_swap_from_entry(USDC, BNB, ...)
    → ExchangeService.swap(from_asset="USDC", to_asset="BNB", ...)
      → Line 777: if "BNB" not in SUPPORTED_ASSETS → ❌ UnsupportedAssetError
```

BNB est bloqué **immédiatement au gate d'entrée** du swap, avant toute tentative de pricing.

### Pourquoi BNB est dans les bundles

Le bundle "Crypto Bundle TOP 5" contient vraisemblablement BTC, ETH, SOL, XRP, BNB. BNB est déclaré comme `TargetAllocation` dans le PE avec un `pe_instrument` BNB-SPOT rattaché à un `pe_asset` BNB.

Le PE n'a aucune notion de `SUPPORTED_ASSETS` — il ne fait qu'orchestrer les allocations. C'est au moment du swap que l'Exchange Engine rejette l'asset.

### Résultat observé

Lors de l'investissement bundle, le `BundleOrchestrator` :
1. Itère sur chaque `TargetAllocation` (BTC, ETH, SOL, XRP, BNB)
2. Appelle `_execute_swap_from_entry()` pour chaque
3. BTC, ETH, SOL, XRP → ✅ swap réussi
4. BNB → ❌ `UnsupportedAssetError`, capturé dans le `except`, `status: "failed"`
5. Le reliquat d'allocation BNB reste dans le **cash leg USDC**

Le bundle passe en `status: "partial"` — c'est correct fonctionnellement, mais l'allocation BNB n'est jamais exécutée.

### Infrastructure BNB

| Composant | Status | Détail |
|-----------|--------|--------|
| Binance pair `BNBUSDT` | ✅ Existe | Symbole valide, volume élevé |
| `market_data_instruments` | ✅ | Créé par `ensure_binance_instruments` |
| `market_data_latest_quotes` | ✅ | Alimenté par WebSocket |
| `pe_assets` (BNB) | ✅ | Seedé par `seed_pe_crypto_assets` |
| `pe_instruments` (BNB-SPOT) | ✅ | Seedé, lié à l'asset BNB |
| `SUPPORTED_ASSETS` | ❌ | **ABSENT** |
| `ASSET_PROVIDER_SYMBOL_MAP` | ❌ | **ABSENT** |
| `ASSET_PRECISION` | ❌ | **ABSENT** |

**BNB a toute l'infrastructure nécessaire sauf 3 lignes dans `exchange/assets.py`.**

---

## Swap Routing Gaps

### Routing actuel

Le swap dans l'Exchange Engine est **abstrait** : il ne passe pas réellement par un intermédiaire USDT. Le routing est :

```
swap(USDC → BTC) :
  1. _resolve_price(USDC, side="sell") → prix EUR de USDC
  2. _resolve_price(BTC, side="buy")  → prix EUR de BTC
  3. gross_eur = amount_USDC × price_USDC_eur
  4. net_eur = gross_eur - fees
  5. amount_BTC = net_eur / price_BTC_eur
```

Il n'y a **pas de routing USDC → USDT → BNB** au niveau de l'Exchange Engine. Chaque asset est résolu indépendamment en EUR via sa quote USDT et le taux EURUSDT. Le swap est une opération comptable à deux prix, pas un routing on-chain.

### Implication

Si BNB est ajouté à `SUPPORTED_ASSETS` + `ASSET_PROVIDER_SYMBOL_MAP` + `ASSET_PRECISION`, le swap `USDC → BNB` fonctionnera automatiquement car :
- `_resolve_price("USDC")` → prix EUR (fallback stablecoin OK)
- `_resolve_price("BNB")` → prix EUR via `BNBUSDT` quote live + `EURUSDT` FX

Aucun routing intermédiaire n'est nécessaire.

### Assets qui nécessiteraient un routing spécial

Aucun. Tous les assets Binance sont cotés en USDT, et le système résout tout via `{ASSET}USDT + EURUSDT → EUR`. Pas de gap de routing.

---

## Root Causes

### Root Cause 1 — Registre Exchange incomplet (CRITIQUE)

`SUPPORTED_ASSETS`, `ASSET_PROVIDER_SYMBOL_MAP`, et `ASSET_PRECISION` dans `exchange/assets.py` ne couvrent que 7 assets sur les 11+ disponibles dans l'infrastructure.

**Assets manquants : BNB, DOGE, AVAX, LINK, DOT**

### Root Cause 2 — Pas de validation cross-couche

Il n'existe aucune vérification au moment de la création de bundle que les assets cibles (`TargetAllocation`) sont réellement échangeables. Le PE accepte n'importe quel `pe_instrument`, y compris ceux dont l'asset n'est pas dans `SUPPORTED_ASSETS`.

### Root Cause 3 — Couches indépendantes sans contrat partagé

| Couche | Source de vérité | Assets couverts |
|--------|-----------------|-----------------|
| Binance instruments | `ensure_binance_instruments.py` | 11 crypto |
| PE assets/instruments | `seed_pe_crypto_assets.py` | 11 crypto |
| Exchange Engine | `SUPPORTED_ASSETS` | **7 crypto** |
| Bundle allocations | PE instruments | 11 crypto |
| Flutter Markets | Binance instruments | 11 crypto |

Le bottleneck est clairement `SUPPORTED_ASSETS`.

---

## Risk Assessment

| Asset | Risque | Impact |
|-------|--------|--------|
| **BNB** | 🔴 CRITIQUE | Présent dans bundle TOP 5, allocation échoue systématiquement → cash leg non investi |
| **DOGE** | 🟡 MODÉRÉ | Visible dans Markets/catalogue mais non tradable. Pas dans un bundle actif (à vérifier) |
| **AVAX** | 🟡 MODÉRÉ | Idem DOGE |
| **LINK** | 🟡 MODÉRÉ | Idem DOGE |
| **DOT** | 🟡 MODÉRÉ | Idem DOGE |
| **EURC** | 🟢 FAIBLE | Fonctionne via fallback, pas d'impact produit immédiat |

### Impact bundle BNB

Chaque investissement dans un bundle contenant BNB :
- Laisse ~10-20% non investis dans le cash leg
- Le bundle passe en `status: "partial"`
- L'utilisateur voit BNB à 0 dans l'allocation réelle
- L'UX est dégradée mais pas bloquante

---

## Recommended Fix Strategy (high-level only)

### Option A — Ajouter les 5 assets manquants à `exchange/assets.py` (recommandé)

Ajouter BNB, DOGE, AVAX, LINK, DOT à :
1. `SUPPORTED_ASSETS`
2. `ASSET_PROVIDER_SYMBOL_MAP` (avec les paires USDT existantes)
3. `ASSET_PRECISION` (avec les précisions standard)

**Effort** : ~15 lignes dans un seul fichier.
**Risque** : minimal — toute l'infrastructure est déjà en place.

### Option B — Retirer les assets non supportés des bundles

Modifier les `TargetAllocation` pour exclure BNB (et autres) tant qu'ils ne sont pas dans `SUPPORTED_ASSETS`.

**Problème** : ne résout pas le problème de fond, et dégrade le produit.

### Option C — Ajouter une validation cross-couche

Lors de la création de bundle, vérifier que chaque asset cible est dans `SUPPORTED_ASSETS`. Rejeter la création sinon.

**À faire en complément de l'Option A**, pas en remplacement.

### Recommandation

**Option A + Option C** :
1. Ajouter immédiatement les 5 assets à `exchange/assets.py`
2. Ajouter une validation dans `BundleService.create_bundle()` pour garantir la cohérence future
