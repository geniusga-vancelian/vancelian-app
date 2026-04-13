# Wallet History Normalization Fix

## Executive Summary

Le chart "Historical Performance" de la page Wallet Statistics affichait des valeurs incorrectes :
- **Value ~1970€** alors que Current Value ≈ 983€
- **Performance +97%** alors que le P&L réel est négatif
- **Spike vertical** au dernier point du chart
- **Dernier point ≠ Current Value** affiché au-dessus

Cinq bugs identifiés et corrigés dans le backend (`build_wallet_history`) et le frontend Flutter (`WalletStatisticsScreen`).

---

## Root Cause

### Bug 1 — Points à position zéro émis dans la série

**Fichier** : `api/services/wallet_history/service.py`

Le code n'avait aucun filtre pour exclure les timestamps où la position totale est nulle. Des candle timestamps pouvaient produire des points `wallet_value = 0` qui polluaient la série et perturbaient la normalisation de base.

### Bug 2 — `now` injecté dans la timeline candle-based

```python
# AVANT — ligne 220
all_timestamps.add(now)
```

Le timestamp `now` était ajouté à la timeline et valorisé via interpolation de candles + FX candles. Puis la live injection remplaçait ce point. Si la conversion FX candle ≠ FX live (sources différentes), cela créait un **spike vertical** au dernier point.

### Bug 3 — Variable shadowing `asset`

Le paramètre `asset` de la fonction était systématiquement écrasé par les boucles internes :
- `for asset in traded_assets:` (ligne 143)
- `t_ts, side, asset, amount, price = trade_events[trade_idx]` (ligne 244)
- `for asset, position in positions.items():` (ligne 255)

### Bug 4 — Performance % formule incorrecte (Flutter)

```dart
// AVANT
return relevant.map((p) => (p.walletValue / base) * 100).toList();
```

Cette formule donne **100%** au premier point (pas 0%). Avec `base = 983` et `current = 983` : affichage `100.0` interprété comme +100% de "performance".

La formule correcte est `((value/base) - 1) * 100` → 0% au premier point, -1.7% si le prix baisse.

### Bug 5 — `is_trade_ts` en O(n²)

```python
# AVANT
is_trade_ts = any(
    t_ts == ts and t_asset == asset
    for t_ts, _, t_asset, _, _ in trade_events
)
```

Scan linéaire de tous les trade_events à chaque (timestamp × asset). Remplacé par un set lookup O(1).

---

## Fix Applied

### Backend — `api/services/wallet_history/service.py`

#### 1. Variable shadowing corrigé

```python
# AVANT
for asset in traded_assets:
    ps = ASSET_PROVIDER_SYMBOL_MAP.get(asset, f"{asset}USDT")

# APRÈS
for ta in traded_assets:
    ps = ASSET_PROVIDER_SYMBOL_MAP.get(ta, f"{ta}USDT")
```

Toutes les boucles internes utilisent désormais des variables distinctes (`ta`, `t_asset`, `a`, `pos`).

#### 2. Timeline sans `now`

```python
# AVANT
all_timestamps.add(now)  # ← créait un point candle-based à now

# APRÈS
# now n'est PAS ajouté — la live injection gère le dernier point
```

Les candle timestamps sont filtrés : `if ts >= first_trade_ts`.

#### 3. Filtre zero-position

```python
total_pos = sum(p for p in positions.values() if p > 0)
if total_pos <= 0:
    continue
```

Les timestamps où aucune position n'est détenue sont exclus de la série.

#### 4. Filtre zero-value

```python
if wallet_value > 0:
    rounded = wallet_value.quantize(...)
    points.append({...})
```

Seuls les points avec une valeur positive sont émis.

#### 5. `is_trade_ts` → set lookup O(1)

```python
trade_ts_pairs: set[tuple[datetime, str]] = set()
for te in trade_events:
    trade_ts_pairs.add((te[0], te[2]))

# Dans la boucle :
is_trade = (ts, a) in trade_ts_pairs
```

---

## First Point Correction

### AVANT

Le premier point pouvait être :
- Un candle timestamp AVANT le premier trade (position = 0, value = 0)
- Le timestamp `now` sans trade (si un seul trade et `now` est ajouté)

### APRÈS

Le premier point est **toujours** le premier trade. Raisons :
1. La timeline ne contient que des trade timestamps + candle timestamps ≥ `first_trade_ts`
2. Le filtre `total_pos <= 0` exclut tout timestamp avant que la première position soit établie
3. Au timestamp du premier trade, la position est immédiatement non-nulle (le `while` loop process le trade avant de calculer la valeur)

**Résultat** : `first_point.wallet_value = amount_crypto × execution_price_eur`

---

## Last Point Correction

### AVANT

```python
all_timestamps.add(now)  # ← point candle-based
# ... main loop crée un point à now avec candle pricing ...
# ... live injection remplace ce point si < 120s ...
```

Problème : le point candle-based utilisait `_interpolate_price()` + FX candles pour la conversion EUR, tandis que la live injection utilisait `MarketDataLatestQuote` + `usdt_to_eur()`. Sources différentes → prix différent → spike.

### APRÈS

```python
# now n'est PAS dans la timeline
# Le dernier point candle-based est le dernier candle avant now
# La live injection AJOUTE ou REMPLACE le dernier point
```

Le dernier point du chart est **toujours** calculé depuis `MarketDataLatestQuote` via `usdt_to_eur()` — la même source que "Current Value" dans le hero UI.

**Résultat** : `chart_end == Current Value == position × live_price_eur`

---

## Performance Formula Fix

### AVANT (Flutter)

```dart
// Formule
return relevant.map((p) => (p.walletValue / base) * 100).toList();

// Résultat : base=983, current=983 → [100.0, 99.8, 100.2, ...]
// Affiché comme "+97%" ou "+100%"
```

### APRÈS (Flutter)

```dart
// Formule
return relevant.map((p) => ((p.walletValue / base) - 1) * 100).toList();

// Résultat : base=983, current=966 → [0.0, -0.2, -1.7, ...]
// Affiché comme "-1.70%"
```

### Labels UI adaptés

| Élément | AVANT | APRÈS |
|---------|-------|-------|
| `headerValue` (% mode) | `"98,30"` | `"-1,70 %"` |
| `pctLabel` (% mode) | `"+0.00 %"` (div/0) | `"-1.70 %"` |
| `isPositive` (% mode) | basé sur `periodChange` | basé sur `lastVal` (perf directe) |
| `startLabel` (% mode) | `"100"` | `"0.0 %"` |

---

## Before vs After Comparison

### Cas : Buy 1000€ BTC, prix actuel ≈ 983€

| Métrique | AVANT | APRÈS |
|----------|-------|-------|
| First point value | 0€ ou 983€ | 983€ (= amount × exec_price) |
| Last point value | ~1970€ (spike FX) | 983€ (= position × live_price) |
| Chart max | ~1970€ | ~1000€ (near purchase) |
| Performance % | +97% | -1.7% |
| Chart end == Current Value | Non | Oui |
| Points à position 0 | Inclus | Exclus |

---

## Validation Results

### Scénario 1 : Buy 1000€, Current Value ≈ 983€

| Vérification | Attendu | Statut |
|-------------|---------|--------|
| Value chart autour de 1000€ | ~983-1000€ | ✅ |
| Last point ≈ 983€ | = Current Value | ✅ |
| Performance ≈ -1.7% | Négatif | ✅ |
| Pas de spike au dernier point | Courbe lisse | ✅ |

### Scénario 2 : Buy puis Sell partiel

| Vérification | Attendu | Statut |
|-------------|---------|--------|
| Chart reflète la position réduite | Value diminue au sell | ✅ |
| Pas de saut/spike | Transition lisse | ✅ |

### Scénario 3 : Aucun trade

| Vérification | Attendu | Statut |
|-------------|---------|--------|
| Chart vide | `[]` retourné | ✅ |

### Scénario 4 : Single trade très récent (M1 candles)

| Vérification | Attendu | Statut |
|-------------|---------|--------|
| First point = trade value | amount × exec_price | ✅ |
| Last point = live value | position × live_price | ✅ |
| Performance calculable | 0% si même prix | ✅ |

### Scénario 5 : Trade sur un autre asset

| Vérification | Attendu | Statut |
|-------------|---------|--------|
| Chart BTC inchangé après trade ETH | Oui (asset-scoped) | ✅ |

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/wallet_history/service.py` | Zero-position filter, remove `now` from timeline, fix variable shadowing, O(1) trade lookup, zero-value filter |
| `mobile/lib/features/wallet/presentation/screens/wallet_statistics_screen.dart` | Performance formula `((v/base)-1)*100`, headerValue avec %, pctLabel direct, isPositive basé sur lastVal, startLabel avec % |

---

## Final Status

| Critère | Statut |
|---------|--------|
| Value chart = position × price | ✅ |
| First point = first trade value | ✅ |
| Last point = Current Value (live) | ✅ |
| Performance % = (value/base - 1) × 100 | ✅ |
| Pas de spike au dernier point | ✅ |
| Points à position 0 exclus | ✅ |
| Currency consistency (EUR via usdt_to_eur) | ✅ |
| Exchange engine non modifié | ✅ |
| Order schema non modifié | ✅ |
| Fee logic non modifiée | ✅ |
| Wallet statistics service non modifié | ✅ |
| API contract structure préservé | ✅ |
