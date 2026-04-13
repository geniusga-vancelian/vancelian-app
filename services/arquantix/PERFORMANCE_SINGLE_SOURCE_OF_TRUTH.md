# Performance Value — Single Source of Truth

## Problem

`performance_value` dans le global history était calculé comme :

```
performance_value = total_value − net_deposits
```

Ce calcul est **fondamentalement incorrect** pour un système financier :

1. **Dépendance circulaire** : la performance dépend de `total_value` qui inclut le fiat, alors que le fiat n'a aucune performance de marché.

2. **Incohérence avec les sous-pages** : les pages Crypto / Bundle / Wallet utilisent `build_wallet_history(mode="performance_value")` qui calcule la performance via un moteur de cost-basis (WAC = Weighted Average Cost). Le résultat est `realized_pnl + unrealized_pnl` pour chaque timestamp, dérivé des prix d'exécution et des prix de marché.

3. **Spike sur dépôt** : un dépôt de 1000 € augmente `total_value` de 1000 € mais `net_deposits` aussi — la soustraction devrait être nulle. Mais les deux timelines (fiat vs deposits) n'avaient pas les mêmes timestamps, créant des fenêtres de décalage où `performance_value` sautait artificiellement.

4. **Max drawdown faux** : calculé sur `total_value` au lieu de la série de performance, il mélangeait les retraits (réduction du patrimoine) avec les pertes de marché.

## Fix

### Backend — `valuation.py` → `build_global_history()`

**AVANT** (1 appel + dérivation) :
```python
crypto_nav = build_wallet_history(mode="value")
performance_value = total_value - net_deposits  # DÉRIVÉ
```

**APRÈS** (2 appels directs, même moteur) :
```python
crypto_nav = build_wallet_history(mode="value")           # pour total_value
crypto_perf = build_wallet_history(mode="performance_value")  # DIRECT
```

`performance_value` provient maintenant directement du moteur cost-basis de `build_wallet_history`, le même moteur utilisé par toutes les autres pages. Fiat a une performance de zéro par définition (pas de risque de marché), donc :

```
global_performance = crypto_performance (direct + bundles)
```

### Ancrage du dernier point

**AVANT** :
```python
live_perf = live_total - current_net_deposits  # DÉRIVÉ
```

**APRÈS** :
```python
pnl = get_pnl(db, client_id)  # realized + unrealized via invariants
live_perf = pnl["total_pnl"]  # DIRECT
```

Le dernier point du chart est maintenant identique à `performance.total_pnl` dans l'endpoint `/global/statistics`.

### Max drawdown

Calculé sur la série `performance_value` (pas `total_value`), ce qui reflète le vrai risque de marché sans les mouvements de cash.

### Suppression complète de `total_value − net_deposits`

Recherche dans tout le backend :
```
grep -r "total.*-.*net_dep" api/
```
→ **0 résultats**. La formule dérivée a été entièrement éliminée.

### Frontend — Strict usage

| Surface | Champ chart | Source label perf % |
|---|---|---|
| Home dashboard | `p.performanceValue` | `stats.performancePct` |
| Global Statistics | `p.performanceValue` | `lastPerfVal` from points |
| Crypto Statistics | `mode="performance_value"` | from backend |
| Bundle Statistics | `mode="performance_value"` | from backend |
| Wallet Statistics | `mode="performance_value"` | from backend |

Aucun chart n'utilise `totalValue`. Aucun calcul local `(last - first)`.

## Invariants

### Invariant 1 : Origine unique
```
performance_value = build_wallet_history(mode="performance_value").wallet_value
```
Pas de dérivation, pas de recomposition.

### Invariant 2 : Cohérence chart ↔ statistiques
```
last_point(chart).performance_value == get_pnl(client).total_pnl
```
Garanti par l'ancrage du dernier point via `get_pnl()`.

### Invariant 3 : Fiat = zéro performance
Le fiat ne contribue pas à `performance_value`. Seule la performance crypto (direct + bundles) est comptabilisée.

### Invariant 4 : Même moteur partout
Toutes les pages utilisent `_build_performance_value()` du module `wallet_history/service.py` :
- Cost-basis WAC (Weighted Average Cost)
- Realized PnL = net_received − cost_basis_consumed
- Unrealized PnL = position × current_price − remaining_cost_basis
- Live point injecté depuis `MarketDataLatestQuote`

### Invariant 5 : Max drawdown sur performance
```
max_drawdown = max((peak − v) / peak) sur performance_value
```
Pas sur `total_value`.

## Guarantees

| Scénario | Comportement |
|---|---|
| Dépôt 1000 € | `performance_value` inchangé (fiat = 0 performance) |
| Perte -200 € sur BTC | `performance_value` descend de ~200 € |
| Achat 500 € de ETH | `performance_value` inchangé (cost = market value au moment de l'achat) |
| Vente avec gain | `realized_pnl` augmente, `performance_value` augmente |
| Dashboard == Crypto | Identique (même moteur, scope global = direct + bundles) |
| Chart last point == stats | Garanti par ancrage `get_pnl()` |
