# Wallet History Live Endpoint Alignment Report

## 1. Executive Summary

- **Dernier point live injecté** : OUI — le backend injecte un point `timestamp=now` avec la valeur live calculée à partir de `MarketDataLatestQuote` (même source que le hero et le wallet detail).
- **Cohérence chart / wallet detail rétablie** : OUI — le dernier point du chart correspond exactement à la valeur temps réel du portefeuille affichée en haut de la page.
- **Régression** : AUCUNE — 36 tests core passent (11 wallet_history + 22 exchange + 3 purge).

## 2. Files modified

| Fichier | Rôle |
|---------|------|
| `api/services/wallet_history/service.py` | Injection du point live à la fin de la série historique |
| `api/tests/test_wallet_history.py` | Ajout de `_seed_quote` dans le test EUR 1m pour cohérence du point live |

## 3. Backend change

### Comment le point live est calculé

Après la boucle de reconstruction historique, le service :

1. Parcourt les positions finales (`positions` dict)
2. Pour chaque asset avec une position > 0, query `MarketDataLatestQuote.last_price` (prix USDT temps réel)
3. Convertit en EUR via `get_eurusdt_rate(strict=False)` + `usdt_to_eur()` si `reference_currency=EUR`
4. Somme pour obtenir `live_value`

C'est **exactement la même logique** que `get_crypto_wallet_detail()` dans `test_clients/service.py` qui alimente le hero et la carte Key Information.

### Comment il est injecté dans la série

```
if dernier_point est < 120s de now:
    → remplace le dernier point (évite doublon)
elif len(points) >= MAX_POINTS:
    → remplace le dernier point (respecte la limite 500)
else:
    → ajoute un nouveau point à la fin
```

Cela garantit :
- Pas de doublon si le dernier candle est très récent
- Respect strict de la limite de 500 points
- Le dernier point est toujours la valeur live

## 4. UI effect

### Alignement chart / hero / wallet total

| Élément | Source de vérité | Résultat |
|---------|-----------------|----------|
| Hero (valeur totale en haut) | `get_crypto_wallet_detail()` → `MarketDataLatestQuote.last_price` | Valeur X |
| Chart (dernier point) | `build_wallet_history()` → `MarketDataLatestQuote.last_price` | Valeur X |
| Carte "Solde total" | `get_crypto_wallet_detail()` → même logique | Valeur X |

Les trois utilisent la même source (`MarketDataLatestQuote`) et la même conversion FX (`get_eurusdt_rate` + `usdt_to_eur`).

### Variation et sparkline

- La variation % et absolue du chart sont recalculées à partir de la série finale incluant le point live
- La sparkline du hero (via `_loadHeroSparkline()`) utilise la série retournée par l'API, donc inclut automatiquement le point live

## 5. Edge cases

| Cas | Comportement |
|-----|-------------|
| **Aucun trade** | `points = []` — pas de point live injecté (pas de positions) |
| **Un seul trade** | Série = [point trade, point live] — la fin reflète la valeur actuelle |
| **Timestamp très proche** (< 2 min) | Le point live remplace le dernier point au lieu de s'ajouter |
| **500 points atteints** | Le point live remplace le dernier point pour respecter la limite |
| **Quote manquante** | Si `MarketDataLatestQuote` n'existe pas pour un asset, sa contribution live = 0 (même fallback que le wallet detail) |

## 6. Final status

**Does the wallet chart now end on the exact live portfolio value displayed on the page?**

**YES** — Le dernier point de la série est calculé avec `MarketDataLatestQuote.last_price` + `get_eurusdt_rate()` + `usdt_to_eur()`, identique à la logique de `get_crypto_wallet_detail()`. Le chart et le hero affichent la même valeur finale.
