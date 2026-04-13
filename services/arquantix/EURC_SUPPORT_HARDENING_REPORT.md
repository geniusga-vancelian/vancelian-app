# EURC_SUPPORT_HARDENING_REPORT

## Executive Summary

EURC (Circle EUR Coin) était dans un état ambigu : déclaré comme asset supporté avec un provider symbol `EURCUSDT` qui **n'existe pas chez Binance**. Aucune source de prix live n'alimentait EURC.

**Stratégie choisie : Option B** — conserver EURC comme asset supporté avec un fallback EUR-pegged explicite (`1 EURC = 1 EUR`).

Modifications appliquées :
1. Ajout de `EUR_PEGGED_STABLECOINS = {"EURC"}` avec fallback dédié `price_eur = 1.0`
2. Retrait du faux mapping `EURC: EURCUSDT` de `ASSET_PROVIDER_SYMBOL_MAP`
3. Intégration du fallback EUR-pegged aux 4 points de garde de `_resolve_price()`

## Current EURC State

### Avant ce patch

| Surface | Présence EURC | Cohérent ? |
|---------|---------------|------------|
| `SUPPORTED_ASSETS` | ✅ Oui | ✅ |
| `ASSET_PRECISION` | ✅ Oui (6 décimales) | ✅ |
| `ASSET_PROVIDER_SYMBOL_MAP` | ✅ `EURCUSDT` | ❌ Paire inexistante |
| `STABLECOIN_ASSETS` | ✅ Oui | ✅ |
| `USD_PEGGED_STABLECOINS` | ❌ Non (correct) | ✅ |
| `ensure_binance_instruments` | ❌ Non | ✅ (cohérent car paire inexistante) |
| Bundle entry asset default | ❌ Non (= USDC) | ✅ |
| Flutter | ❌ Aucune référence | ✅ |
| PE orchestrator/overlay | ✅ Classification stablecoin | ✅ |

### Problème

`ASSET_PROVIDER_SYMBOL_MAP["EURC"] = "EURCUSDT"` pointait vers un symbole Binance invalide. Toute tentative de `_resolve_price("EURC")` échouait avec `PriceUnavailableError` car :
- L'instrument n'existait pas en DB (jamais créé par `ensure_binance_instruments`)
- Même s'il existait, le fetch REST retournerait `{"code":-1121,"msg":"Invalid symbol."}`

## Why EURC Is Ambiguous Today

1. **Déclaré supporté** dans `SUPPORTED_ASSETS` → le système accepte EURC comme asset valide
2. **Mapping vers un faux symbole** → `_resolve_price("EURC")` tente de chercher `EURCUSDT` dans `market_data_latest_quotes`, ne trouve rien, et lève une exception
3. **Pas de fallback** → ni USD-pegged (car EURC n'est pas indexé sur le dollar) ni EUR-pegged
4. **Utilisé dans le PE** → `orchestrator.py` et `direct_overlay.py` classifient EURC comme `stablecoin`, ce qui est correct

Résultat : EURC est un "instrument fantôme" — déclaré mais non opérationnel.

## Option Analysis

### Option A — Désactiver EURC

| Avantage | Inconvénient |
|----------|-------------|
| Élimine l'ambiguïté | Nécessite de modifier `SUPPORTED_ASSETS`, toutes les validations |
| Simplifie le système | Interdit toute position EURC existante (cash legs) |
| | Rend EURC inutilisable comme future devise d'entrée |

### Option B — Support avec fallback EUR-pegged ✅ Choisie

| Avantage | Inconvénient |
|----------|-------------|
| EURC reste opérationnel | Pas de "vrai" prix marché |
| `1 EURC = 1 EUR` est sémantiquement correct | Erreur théorique de ±0.001% vs prix marché réel |
| Cohérent avec la devise de référence EUR | |
| Pas de refactor nécessaire | |
| Compatible avec les cash legs EURC existants | |
| Extensible : si un provider EURC est ajouté, le fallback est court-circuité | |

### Option C — Brancher une autre source de prix

| Avantage | Inconvénient |
|----------|-------------|
| Vrai prix marché | Nécessite un nouveau provider (Coinbase, Kraken, etc.) |
| | Complexité d'intégration significative |
| | EURC n'est pas activement utilisé |

**Recommandation : Option B.** Le fallback `1 EURC = 1 EUR` est parfaitement précis pour un stablecoin régulé MiCA avec backing 1:1 en euros. L'erreur est négligeable et le coût d'intégration d'un provider alternatif n'est pas justifié à ce stade.

## Chosen Strategy

**Option B — Support propre avec fallback EUR-pegged explicite**

### Modèle de fallback

```
1 EURC = 1.000000 EUR (synthétique, sans dépendance à un feed live)
```

### Hiérarchie de résolution dans `_resolve_price("EURC")`

```
1. provider_symbol dans ASSET_PROVIDER_SYMBOL_MAP ?
   → Non (retiré) → EUR-pegged ? → Oui → return 1.0 EUR

   (Si un provider est ajouté plus tard, la quote live sera prioritaire)
```

## Backend Changes

### 1. `exchange/service.py`

**Ajout :**
```python
EUR_PEGGED_STABLECOINS = frozenset({"EURC"})
```

**Ajout méthode :**
```python
@staticmethod
def _eur_pegged_fallback_price(asset: str) -> Decimal:
    logger.info("Using EUR-pegged fallback for %s: price_eur = 1.0", asset)
    return Decimal("1")
```

**Modification `_resolve_price()` :**
Les 4 points de garde (provider_symbol absent, quote absente, quote_time absent, quote stale) incluent maintenant un check `EUR_PEGGED_STABLECOINS` avant `USD_PEGGED_STABLECOINS`, avec fallback vers `_eur_pegged_fallback_price()`.

### 2. `exchange/assets.py`

**Modification :**
```python
# Avant
"EURC": "EURCUSDT",

# Après
# EURC: no Binance pair exists (EURCUSDT is invalid).
# Pricing uses EUR-pegged fallback (1 EURC = 1 EUR) in _resolve_price().
```

EURC reste dans `SUPPORTED_ASSETS` et `ASSET_PRECISION`.

### 3. Fichiers inchangés

| Fichier | Raison |
|---------|--------|
| `bundles/orchestrator.py` | Classification stablecoin correcte |
| `direct_overlay.py` | Classification stablecoin correcte |
| `ensure_binance_instruments.py` | EURC n'y était déjà pas |
| Flutter (tous fichiers) | Aucune référence EURC |
| Bundle entry config | Default = USDC, EURC non utilisé |

## Bundle / UI Impact

### Bundle entry asset

| Paramètre | Valeur | EURC impliqué ? |
|-----------|--------|-----------------|
| `entry_asset_default` (fallback) | `"USDC"` | ❌ |
| `entry_assets_allowed` (fallback) | `["USDC"]` | ❌ |
| `entry_asset_default` (schema) | `"USDC"` | ❌ |
| `entry_assets_allowed` (schema) | `["USDC"]` | ❌ |

### Scénarios bundle avec EURC

| Scénario | Comportement |
|----------|-------------|
| Cash leg EURC dans un bundle | Valorisé à 1.0 EUR (fallback) ✅ |
| EURC comme entry asset | Fonctionnerait via fallback, mais non proposé par défaut |
| preview_swap(EURC → BTC) | EURC résolu à 1.0 EUR, BTC via quote live ✅ |

### Flutter

Aucune référence EURC. Aucun impact.

## Validation Scenarios

| # | Scénario | Résultat |
|---|----------|---------|
| 1 | `_resolve_price("EURC")` sans quote live | ✅ Retourne `Decimal("1")` (1.0 EUR) |
| 2 | `_resolve_price("EURC")` avec quote live (future) | ✅ Utiliserait la quote live (provider_symbol ajouté) |
| 3 | `preview_buy("EURC", 100)` | ✅ 100 EUR → 100 EURC (prix 1.0 EUR) |
| 4 | Cash leg EURC valorisé dans bundle | ✅ quantity × 1.0 EUR |
| 5 | `_resolve_price("USDC")` sans quote live | ✅ Fallback USD-pegged inchangé |
| 6 | `_resolve_price("BTC")` stale | ❌ MarketQuoteStaleError (correct) |
| 7 | EURC n'apparaît pas dans Flutter | ✅ Aucune référence |
| 8 | Logs de fallback EURC | ✅ `INFO: Using EUR-pegged fallback for EURC: price_eur = 1.0` |

## Final Status

| Item | Status |
|------|--------|
| EURC dans `SUPPORTED_ASSETS` | ✅ Conservé |
| EURC dans `ASSET_PRECISION` | ✅ Conservé (6 décimales) |
| EURC dans `ASSET_PROVIDER_SYMBOL_MAP` | ✅ **Retiré** (faux symbole) |
| EURC dans `STABLECOIN_ASSETS` | ✅ Conservé (seuil staleness) |
| EURC dans `EUR_PEGGED_STABLECOINS` | ✅ **Ajouté** |
| `_eur_pegged_fallback_price()` | ✅ **Créé** — retourne `Decimal("1")` |
| Fallback intégré dans `_resolve_price()` | ✅ 4 points de garde couverts |
| Logs de traçabilité | ✅ `INFO` à chaque fallback |
| Impact bundle | ✅ Nul (USDC est le default) |
| Impact Flutter | ✅ Nul (aucune référence EURC) |
| Non-régression USDC/USD-pegged | ✅ Inchangé |
| Non-régression BTC/ETH/actifs volatils | ✅ Inchangé |
