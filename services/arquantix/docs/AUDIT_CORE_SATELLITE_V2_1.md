# Audit de Conformité CORE_SATELLITE V2.1 (EDHEC-style)

**Date**: 2024-12-XX  
**Version**: V2.1  
**Objectif**: Vérifier la conformité de l'implémentation Core-Satellite V2.1 par rapport aux exigences EDHEC-style.

---

## Étape 1 — Inventaire des Fichiers

### Backend

| Fichier | Rôle | Statut | Notes |
|---------|------|--------|-------|
| `api/services/backtest/strategies/core_satellite.py` | Implémentation principale de la stratégie | ✅ OK | Fonctions V2.1 définies |
| `api/services/backtest/executor.py` | Dispatch des stratégies | ✅ OK | Paramètres V2.1 parsés |
| `api/services/backtest/routes.py` | Schémas Pydantic API | ✅ OK | Paramètres V2.1 dans `BacktestStrategyParams` |

### Frontend

| Fichier | Rôle | Statut | Notes |
|---------|------|--------|-------|
| `web/src/components/finance/BacktestsTab.tsx` | UI principale backtest | ✅ OK | CORE_SATELLITE dans dropdowns |
| `web/src/components/backtests/CoreSatelliteCharts.tsx` | Charts spécifiques | ✅ OK | Charts pour allocation, TE, cushion |
| `web/src/app/api/backtests/run/route.ts` | Proxy Next.js / Zod | ✅ OK | Validation Zod V2.1 |

### Tests

| Fichier | Rôle | Statut | Notes |
|---------|------|--------|-------|
| `api/tests/test_core_satellite_v1.py` | Tests V1 | ⚠️ PARTIEL | Tests V1 existants, pas de tests V2.1 contractuels |

### Documentation

| Fichier | Rôle | Statut | Notes |
|---------|------|--------|-------|
| `docs/STRATEGY_CORE_SATELLITE.md` | Documentation principale | ❌ INCOMPLET | Pas de section V2.1 EDHEC-style |
| `docs/CORE_SATELLITE_V1_TO_V2_DELTA.md` | Delta V1→V2 | ⚠️ PARTIEL | Pas de section V2→V2.1 |

---

## Étape 2 — Invariants Backend (weights_json / series)

### ❌ FAIL: Champs V2.1 manquants dans weights_json

**Problème identifié**: Les champs V2.1 EDHEC-style ne sont **PAS** stockés dans `weights_json`.

**Champs attendus (obligatoires)**:
- `_cs_alloc_mode` (string): Mode d'allocation utilisé ("te_target", "utility_lambda", "dynamic_cushion")
- `_cs_sat_weight_scalar` (float 0..1): Poids scalaire du satellite (w)
- `_cs_te_sat` (float): Tracking Error du satellite (annualisée)
- `_cs_ir_sat` (float ou null): Information Ratio du satellite

**Champs conditionnels (si `allocation_mode == "dynamic_cushion"`)**:
- `_cs_rel_index` (float): Index de performance relative
- `_cs_rel_floor` (float): Floor de performance relative
- `_cs_cushion` (float): Cushion dynamique

**Localisation du problème**:
- Fichier: `api/services/backtest/strategies/core_satellite.py`
- Ligne ~325-338: Construction de `weights_dict` avant création de `portfolio_bar`

**Code actuel** (lignes 325-338):
```python
weights_dict = {str(inst_id): float(satellite_weights.get(inst_id, 0.0)) for inst_id in instrument_ids}
weights_dict['_core_weight'] = float(core_weight)
# ... V2 fields (_te_pred, _satellite_turnover, etc.)
# ❌ PAS de champs V2.1 (_cs_alloc_mode, _cs_sat_weight_scalar, etc.)
```

**Cause racine**:
- La fonction `compute_scalar_satellite_weight()` est définie mais **jamais appelée** dans le code principal.
- L'ancienne logique V1/V2 (`_optimize_weights` avec grid search ou quadratic) est toujours utilisée.
- Les champs V2.1 ne sont pas calculés ni stockés.

### ✅ OK: Champs génériques V1/V2

- `_core_weight`: ✅ Stocké
- `_te_realized`: ✅ Stocké (si calculé)
- `_te_pred`: ✅ Stocké (si disponible)
- `_te_pred_shrunk`: ✅ Stocké (si shrinkage activé)
- `_satellite_turnover`: ✅ Stocké (si > 0)
- `_portfolio_turnover`: ✅ Stocké (si > 0)
- `_optimization_score`: ✅ Stocké (si disponible)

### ⚠️ WARNING: Logique V2.1 non intégrée

**Problème**: La refactorisation V2.1 (séparation `build_unit_satellite_portfolio` + `compute_scalar_satellite_weight`) n'est pas intégrée dans la boucle principale.

**Code manquant**:
- Appel à `compute_scalar_satellite_weight()` pour calculer `w_scalar`
- Stockage des résultats dans `weights_dict`
- Tracking de `rel_index`, `rel_floor`, `cushion` pour `dynamic_cushion`

---

## Étape 3 — Cohérence API (Pydantic vs Zod)

### ✅ OK: Paramètres V2.1 dans Pydantic

**Fichier**: `api/services/backtest/routes.py` (lignes 44-50)

```python
# V2.1 EDHEC-style allocation params
allocation_mode: Optional[str] = None
lambda_risk: Optional[float] = None
multiplier: Optional[float] = None
floor_rel_ratio: Optional[float] = None
floor_accrues_with_core: Optional[bool] = None
sat_max: Optional[float] = None
```

### ✅ OK: Paramètres V2.1 dans Zod

**Fichier**: `web/src/app/api/backtests/run/route.ts` (lignes 39-45)

```typescript
// V2.1 EDHEC-style allocation params
allocation_mode: z.enum(['te_target', 'utility_lambda', 'dynamic_cushion']).optional(),
lambda_risk: z.number().min(0).optional(),
multiplier: z.number().min(0).optional(),
floor_rel_ratio: z.number().min(0).max(1).optional(),
floor_accrues_with_core: z.boolean().optional(),
sat_max: z.number().min(0).max(1).optional(),
```

### ✅ OK: Parsing dans executor

**Fichier**: `api/services/backtest/executor.py` (lignes 222-228)

Les paramètres V2.1 sont parsés et passés à `run_core_satellite_backtest()`.

### ⚠️ WARNING: Pas de validation stricte

- `allocation_mode` accepte n'importe quelle string (devrait être enum)
- Pas de validation de cohérence (ex: `lambda_risk` requis si `allocation_mode == "utility_lambda"`)

---

## Étape 4 — Frontend (dropdowns, UI, params)

### ✅ OK: CORE_SATELLITE dans dropdowns

**Fichier**: `web/src/components/finance/BacktestsTab.tsx`

- Ligne 35: Type `strategyType` inclut `'CORE_SATELLITE'`
- Lignes 621, 636: `SelectItem value="CORE_SATELLITE"` dans les deux dropdowns (bundle et instruments)

### ✅ OK: JSON textarea pour params

- Lignes 52-74: `CORE_SATELLITE_DEFAULTS` défini avec tous les paramètres V2.1
- Lignes 733-765: UI avec textarea JSON, bouton "Use defaults", checkbox "Debug logs"

### ✅ OK: Validation Zod client-side

- Lignes 375-401: `coreSatelliteParamsSchema` avec validation complète
- Ligne 424: `parseCoreSatelliteParams` pour parsing et validation

### ⚠️ WARNING: Types TypeScript

**Fichier**: `web/src/components/backtests/types.ts`

- Ligne 54: `BacktestCreateRequest.strategy.type` ne inclut **PAS** `'CORE_SATELLITE'`
- Ligne 8: `PortfolioBar.weights_json` est `Record<string, number>` (pas de types spécifiques pour V2.1)

**Impact**: Pas de type-safety pour les champs V2.1 dans TypeScript.

---

## Étape 5 — Charts (vérification visuelle)

### ✅ OK: CoreSatelliteCharts component

**Fichier**: `web/src/components/backtests/CoreSatelliteCharts.tsx`

- Lignes 13-24: Extraction de `_core_weight` et `_cs_sat_weight_scalar` depuis `weights_json`
- Lignes 38-67: Chart "Core-Satellite Allocation" (full width)
- Lignes 69-116: Chart "Tracking Error (Realized vs Target)"
- Lignes 118-169: Chart "Dynamic Cushion" (si `_cs_cushion` présent)

### ❌ FAIL: Champs V2.1 manquants → Charts vides

**Problème**: Les charts attendent `_cs_sat_weight_scalar`, `_cs_cushion`, etc., mais ces champs ne sont **jamais** produits par le backend.

**Impact**: Les charts Core-Satellite affichent "No data available" même après un backtest.

### ✅ OK: Intégration dans BacktestsTab

- Lignes 1000-1003: `CoreSatelliteCharts` conditionnellement rendu si `strategy_type === 'CORE_SATELLITE'`

---

## Étape 6 — Tests automatiques

### ❌ FAIL: Pas de tests V2.1 contractuels

**Fichier existant**: `api/tests/test_core_satellite_v1.py`
- Tests V1 uniquement (grid search, basic TE targeting)
- Pas de tests pour V2.1:
  - `allocation_mode="te_target"`
  - `allocation_mode="utility_lambda"`
  - `allocation_mode="dynamic_cushion"`
  - Vérification des champs `weights_json` V2.1

**Tests manquants**:
1. `test_v2_1_te_target_alloc_changes_with_target_te`
2. `test_v2_1_utility_lambda_uses_lambda_risk`
3. `test_v2_1_dynamic_cushion_produces_rel_index_floor_cushion`
4. `test_v2_1_weights_json_contains_v2_1_fields` (test contractuel)

---

## Étape 7 — Documentation

### ❌ FAIL: Pas de documentation V2.1

**Fichier**: `docs/STRATEGY_CORE_SATELLITE.md`

- Section V2.1 EDHEC-style **absente**
- Pas de formules pour:
  - `w = clamp(target_te / TE_sat, sat_min, sat_max)` (te_target)
  - `w* = clamp(IR_sat / (2*lambda_risk*TE_sat), sat_min, sat_max)` (utility_lambda)
  - `w = clamp(multiplier * cushion, sat_min, sat_max)` (dynamic_cushion)
- Pas d'exemples JSON payloads pour les 3 modes

---

## Résumé des Findings

| Catégorie | Statut | Détails |
|-----------|--------|---------|
| **Backend - weights_json V2.1** | ❌ **FAIL** | Champs V2.1 jamais stockés, logique V2.1 non intégrée |
| **Backend - API schemas** | ✅ **OK** | Paramètres V2.1 dans Pydantic et Zod |
| **Frontend - UI** | ✅ **OK** | Dropdowns, JSON textarea, validation |
| **Frontend - Types** | ⚠️ **WARNING** | `BacktestCreateRequest` manque `CORE_SATELLITE` dans type union |
| **Charts** | ❌ **FAIL** | Charts attendent champs V2.1 qui ne sont pas produits |
| **Tests** | ❌ **FAIL** | Pas de tests V2.1 contractuels |
| **Documentation** | ❌ **FAIL** | Pas de section V2.1 EDHEC-style |

---

## Correctifs Proposés

### 1. Intégrer la logique V2.1 dans `core_satellite.py`

**Fichier**: `api/services/backtest/strategies/core_satellite.py`

**Changements nécessaires**:
1. Appeler `compute_scalar_satellite_weight()` dans la boucle principale (après `_optimize_weights`)
2. Stocker les champs V2.1 dans `weights_dict`:
   - `_cs_alloc_mode`
   - `_cs_sat_weight_scalar`
   - `_cs_te_sat`
   - `_cs_ir_sat`
   - `_cs_rel_index`, `_cs_rel_floor`, `_cs_cushion` (si `dynamic_cushion`)
3. Tracking de `rel_index`, `rel_floor`, `cushion` pour `dynamic_cushion`

**Patch estimé**: ~100 lignes modifiées/ajoutées

### 2. Mettre à jour les types TypeScript

**Fichier**: `web/src/components/backtests/types.ts`

**Changements**:
- Ajouter `'CORE_SATELLITE'` au type union de `BacktestCreateRequest.strategy.type`
- (Optionnel) Définir une interface pour `weights_json` V2.1

**Patch estimé**: ~5 lignes modifiées

### 3. Créer tests V2.1

**Fichier**: `api/tests/test_core_satellite_v2_1_contract.py` (nouveau)

**Tests**:
- Test contractuel: vérifier que `weights_json` contient les champs V2.1
- Tests fonctionnels pour les 3 modes d'allocation

**Patch estimé**: ~200 lignes

### 4. Mettre à jour la documentation

**Fichier**: `docs/STRATEGY_CORE_SATELLITE.md`

**Ajouts**:
- Section "V2.1 EDHEC-style Allocation Modes"
- Formules pour les 3 modes
- Exemples JSON payloads

**Patch estimé**: ~100 lignes

---

## Conclusion

**Statut global**: ❌ **FAIL** - Implémentation V2.1 incomplète

**Priorité**:
1. **CRITIQUE**: Intégrer la logique V2.1 dans `core_satellite.py` (les champs V2.1 doivent être produits)
2. **HAUTE**: Créer tests contractuels pour valider l'output
3. **MOYENNE**: Mettre à jour documentation et types TypeScript

**Estimation du travail**: ~400 lignes de code à modifier/ajouter

---

## Commandes de Vérification

Voir `docs/AUDIT_CORE_SATELLITE_V2_1_RUNBOOK.md` pour les commandes de vérification automatisées.
