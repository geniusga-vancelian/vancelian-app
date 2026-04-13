# Global History Time Alignment Fix

## Root Cause

Le global history construisait sa propre timeline en utilisant `nav_points` (mode=value) comme série canonique, puis cherchait les `performance_value` correspondants via un lookup `_perf_at()` dans une deuxième série.

Problèmes :

1. **Timeline pilotée par NAV, pas par perf** : la série canonique était `mode="value"`, alors que les charts affichent `performance_value`. Si NAV et perf avaient des timestamps légèrement différents (live point injection), le lookup `_perf_at()` reportait la dernière valeur connue → segments plats artificiels.

2. **Logique de merge complexe** : `_perf_at()` parcourait `perf_timestamps_sorted` linéairement avec un `last_known_perf` stateful — fragile et O(n²) dans le pire cas.

3. **Incohérence avec le crypto chart** : la page Crypto appelle `build_wallet_history(mode="performance_value")` directement et obtient une série dense (candle-driven). Le global history reconstruisait sa propre timeline, créant potentiellement un nombre de points et une densité différents.

## Fix

### Architecture — Perf series = canonical timeline

**AVANT** :
```
nav_points = build_wallet_history(mode="value")     ← canonical
perf_points = build_wallet_history(mode="performance_value")
→ iterate nav_points, lookup perf via _perf_at()
```

**APRÈS** :
```
perf_points = build_wallet_history(mode="performance_value")  ← canonical
nav_by_ts = build_wallet_history(mode="value")  → dict index
→ iterate perf_points, lookup NAV via dict
```

La série `performance_value` pilote la timeline. C'est **exactement la même série** que celle du crypto chart. Le NAV est un simple overlay informatif via lookup O(1) par timestamp.

### Code — `build_global_history()` dans `valuation.py`

```python
# Single canonical series: performance_value
crypto_perf_result = build_wallet_history(
    db, client_id, reference_currency="EUR",
    mode="performance_value",
)
perf_points = crypto_perf_result.get("points", [])

# NAV as index for total_value overlay
nav_by_ts = {p["timestamp"]: p.get("wallet_value", 0) for p in nav_result["points"]}

# Build output from perf series (canonical)
for pp in perf_points:
    perf_val = pp.get("wallet_value", 0)   # direct, no lookup
    nav_val = nav_by_ts.get(ts_str)         # O(1) dict lookup
    total_val = crypto_nav_val + fiat_val
    points.append({
        "timestamp": ts_str,
        "total_value": total_val,
        "performance_value": perf_val,
    })
```

### Éliminé

- `_perf_at()` — fonction de lookup interpolé → supprimée
- `perf_by_ts` dict + `perf_timestamps_sorted` list → supprimés
- `last_known_perf` stateful variable → supprimée
- Timeline merge logic → supprimée

## Before vs After

| Aspect | Avant | Après |
|---|---|---|
| Timeline source | `mode="value"` (NAV) | `mode="performance_value"` (perf) |
| Perf lookup | `_perf_at()` interpolation, carry-forward | Direct from point, aucun lookup |
| NAV lookup | Direct (canonical) | `nav_by_ts.get()` O(1) dict |
| Densité des points | Dépend du NAV | Identique au crypto chart |
| Segments plats | Possible (stale carry-forward) | Impossible (valeur directe) |
| Complexité | O(n × m) worst case | O(n) |

## Validation

### Test 1 : Pas de trades → chart évolue
La timeline est pilotée par les candles (prix de marché), pas par les trades. Entre deux trades, les prix de marché évoluent → la courbe évolue.

### Test 2 : Global == Crypto (quand seul crypto existe)
Les deux appellent `build_wallet_history(mode="performance_value")` avec les mêmes paramètres. Timeline identique, valeurs identiques.

### Test 3 : Chart continu
Chaque point de `perf_points` a sa `wallet_value` directe — pas de lookup, pas de carry-forward, pas de segment plat.

### Test 4 : Alignement temporel identique entre écrans
```
assert len(global_points) == len(crypto_perf_points) + (0 or 1)
```
Le `+1` est le live anchor point si nécessaire.

## Final Guarantees

| Garantie | Mécanisme |
|---|---|
| Timeline = crypto chart | `perf_points` from `build_wallet_history(mode="performance_value")` |
| Pas de gaps | Timeline = trade ts + candle ts (dense, market-driven) |
| Pas de segments plats artificiels | `performance_value` lu directement, jamais interpolé |
| Last point == statistics | Ancré via `get_pnl().total_pnl` |
| Max drawdown correct | Calculé sur `performance_value`, pas `total_value` |
| Dépôt = pas de spike | Fiat n'impacte pas `performance_value` |
