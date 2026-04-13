# SWAP_QUOTE_STALENESS_HARDENING_REPORT

## Executive Summary

Audit et hardening de la validation de fraîcheur / disponibilité des quotes pour le swap crypto ↔ crypto.
L'audit montre que le code de résolution de prix (`_resolve_price`) appliquait **déjà** les gardes nécessaires pour les deux jambes du swap (source et target).
13 tests ont été ajoutés pour couvrir exhaustivement les 7 scénarios de rejet demandés.
Aucune modification du service ou du modèle comptable n'a été nécessaire.

**Résultat final** : 13/13 tests staleness passent, 36/36 tests non-régression passent.

---

## Current Gap

Avant ce patch, le swap crypto ↔ crypto avait été validé fonctionnellement avec 6 tests couvrant :
- Swap simple BTC → ETH
- Swap with fees
- Invariants A/B/C
- Insufficient source balance
- Multiple sequential swaps
- Preview vs execution

Le scénario **quote stale / missing** était explicitement marqué comme "skipped" dans `test_swap_crypto.py` (ligne 345 : `# Test 5 — Quote stale: skipped (would require mocking quote_time)`).

Le gap n'était **pas** dans le code de service (qui gérait déjà correctement les rejets), mais dans la **couverture de tests** qui ne validait pas ces chemins d'erreur.

---

## Freshness Rule Enforcement

### Règle métier

Le swap est rejeté si :

| Condition | Erreur | HTTP |
|-----------|--------|------|
| Quote source > 60s | `MarketQuoteStaleError` | 503 |
| Quote target > 60s | `MarketQuoteStaleError` | 503 |
| Quote source absente | `PriceUnavailableError` | 503 |
| Quote target absente | `PriceUnavailableError` | 503 |
| Quote source sans timestamp | `MarketQuoteStaleError` | 503 |
| Quote target sans timestamp | `MarketQuoteStaleError` | 503 |

### Implémentation dans `_resolve_price()`

La méthode `_resolve_price()` (utilisée par `preview_swap` et `swap`) applique la chaîne de validation suivante :

1. **Provider symbol** : Si l'asset n'a pas de mapping, `PriceUnavailableError`
2. **Quote existence** : Si aucune quote ou `last_price` null, `PriceUnavailableError`
3. **Timestamp existence** : Si `quote_time` est null, `MarketQuoteStaleError`
4. **Freshness** : Si `age_seconds > MAX_QUOTE_AGE_SECONDS (60)`, `MarketQuoteStaleError`

Les deux appels dans `preview_swap` et `swap` passent `override_price=None`, ce qui garantit que le freshness guard est **toujours** actif. Aucun fallback silencieux n'est possible.

### Séquence dans preview_swap / swap

```
preview_swap():
  price_from = _resolve_price(db, from_asset, None, side="sell")  ← garde source
  price_to   = _resolve_price(db, to_asset, None, side="buy")    ← garde target
  ... calculs ...

swap():
  price_from = _resolve_price(db, from_asset, None, side="sell")  ← garde source
  price_to   = _resolve_price(db, to_asset, None, side="buy")    ← garde target
  ... idempotency check, création d'ordres, etc. ...
```

Les appels de prix se font **avant** toute création d'ordre ou modification de position. En cas de rejet, l'exception remonte via `error_mapper.py` en HTTP 503 avec `error_code` structuré.

### Cohérence BUY / SELL

Les endpoints BUY et SELL utilisent exactement la même méthode `_resolve_price()` avec les mêmes gardes. Le comportement est identique : quote stale ou absente → erreur 503, aucun side effect.

---

## Missing Quote Handling

| Cas | Détection | Erreur |
|-----|-----------|--------|
| Instrument non mappé dans `ASSET_PROVIDER_SYMBOL_MAP` | `provider_symbol is None` | `PriceUnavailableError` |
| Aucune ligne dans `market_data_latest_quotes` | `quote is None` | `PriceUnavailableError` |
| `last_price` null | `quote.last_price is None` | `PriceUnavailableError` |
| `quote_time` null | `quote.quote_time is None` | `MarketQuoteStaleError` |

Aucun de ces cas ne produit de fallback silencieux. Le message d'erreur est explicite et contient le nom de l'asset concerné.

---

## Tests Added

**Fichier** : `api/tests/test_swap_quote_staleness.py`

13 tests couvrant les 7 scénarios demandés :

| # | Test | Scénario | Vérifie |
|---|------|----------|---------|
| 1 | `test_swap_source_quote_stale_preview` | Source BTC quote 120s old | preview → 503 MARKET_QUOTE_STALE |
| 2 | `test_swap_source_quote_stale_exec` | Source BTC quote 120s old | swap → 503, aucun ordre créé |
| 3 | `test_swap_target_quote_stale_preview` | Target ETH quote 120s old | preview → 503 MARKET_QUOTE_STALE |
| 4 | `test_swap_target_quote_stale_exec` | Target ETH quote 120s old | swap → 503, aucun ordre créé |
| 5 | `test_swap_source_quote_missing_preview` | Source BTC quote supprimée | preview → 503 PRICE_UNAVAILABLE |
| 6 | `test_swap_source_quote_missing_exec` | Source BTC quote supprimée | swap → 503, aucun ordre créé |
| 7 | `test_swap_target_quote_missing_preview` | Target ETH quote supprimée | preview → 503 PRICE_UNAVAILABLE |
| 8 | `test_swap_target_quote_missing_exec` | Target ETH quote supprimée | swap → 503, aucun ordre créé |
| 9 | `test_swap_source_no_timestamp_preview` | Source BTC quote_time=NULL | preview → 503 MARKET_QUOTE_STALE |
| 10 | `test_swap_source_no_timestamp_exec` | Source BTC quote_time=NULL | swap → 503, aucun ordre créé |
| 11 | `test_swap_target_no_timestamp_preview` | Target ETH quote_time=NULL | preview → 503 MARKET_QUOTE_STALE |
| 12 | `test_swap_target_no_timestamp_exec` | Target ETH quote_time=NULL | swap → 503, aucun ordre créé |
| 13 | `test_swap_stale_no_side_effects` | Source stale, vérification complète | Positions BTC/ETH inchangées, aucun ordre, aucun swap_group_id |

### Technique de test

- Chaque test exécute un setup complet (client, dépôt EUR, achat BTC) pour avoir une position réelle
- Les quotes sont d'abord seedées fraîches, puis altérées (stale / supprimées / timestamp null) avant l'appel
- La vérification porte sur le code HTTP **et** le `error_code` structuré dans le body
- Les tests de side effects vérifient le count d'ordres avant/après

---

## No-Side-Effects Validation

Le test `test_swap_stale_no_side_effects` vérifie de manière exhaustive :

1. **Position BTC** : balance identique avant et après le rejet
2. **Position ETH** : balance identique (0) avant et après le rejet
3. **Ordres** : aucun `ExchangeOrder` créé
4. **swap_group_id** : aucun enregistrement avec `swap_group_id IS NOT NULL`

Cette validation confirme que le rejet est atomique : l'exception est levée dans `_resolve_price` avant tout effet de bord dans le service.

---

## Final Status

| Métrique | Valeur |
|----------|--------|
| Tests staleness ajoutés | 13 |
| Tests staleness passants | 13/13 |
| Tests non-régression (swap + exchange + PnL) | 36/36 |
| Fichiers de service modifiés | 0 |
| Modèle comptable modifié | non |
| swap_group_id modifié | non |
| BUY / SELL impactés | non |
| Invariants A/B/C impactés | non |

Le guard de fraîcheur était déjà en place dans `_resolve_price()` et couvrait correctement les deux jambes du swap. Ce patch ajoute uniquement la **couverture de tests** qui manquait pour valider ces chemins d'erreur de manière automatisée.
