# Runbook - Audit CORE_SATELLITE V2.1

Ce document contient les commandes pour vérifier la conformité de l'implémentation CORE_SATELLITE V2.1.

---

## Prérequis

- Python 3.9+ avec dépendances installées (`pip install -r api/requirements.txt`)
- Accès à la base de données (optionnel, pour tests end-to-end)
- Node.js 18+ et npm (pour vérifications frontend)

---

## Vérifications Statiques

### 1. Vérifier la présence de CORE_SATELLITE dans les dropdowns frontend

```bash
cd web/src/components/finance
grep -n "CORE_SATELLITE" BacktestsTab.tsx
```

**Expected output**:
```
35:  const [strategyType, setStrategyType] = useState<'equal_weight' | 'momentum' | 'bundle_strategy' | 'CPPI' | 'CORE_SATELLITE'>('equal_weight')
621:                        <SelectItem value="CORE_SATELLITE">Core-Satellite</SelectItem>
636:                        <SelectItem value="CORE_SATELLITE">Core-Satellite</SelectItem>
```

**Status**: ✅ OK si 3+ occurrences trouvées

---

### 2. Vérifier les paramètres V2.1 dans les schémas API

#### Backend (Pydantic)

```bash
cd api/services/backtest
grep -A 7 "V2.1 EDHEC-style allocation params" routes.py
```

**Expected output**:
```python
    # V2.1 EDHEC-style allocation params
    allocation_mode: Optional[str] = None
    lambda_risk: Optional[float] = None
    multiplier: Optional[float] = None
    floor_rel_ratio: Optional[float] = None
    floor_accrues_with_core: Optional[bool] = None
    sat_max: Optional[float] = None
```

**Status**: ✅ OK si tous les 6 paramètres sont présents

#### Frontend (Zod)

```bash
cd web/src/app/api/backtests/run
grep -A 7 "V2.1 EDHEC-style allocation params" route.ts
```

**Expected output**:
```typescript
      // V2.1 EDHEC-style allocation params
      allocation_mode: z.enum(['te_target', 'utility_lambda', 'dynamic_cushion']).optional(),
      lambda_risk: z.number().min(0).optional(),
      multiplier: z.number().min(0).optional(),
      floor_rel_ratio: z.number().min(0).max(1).optional(),
      floor_accrues_with_core: z.boolean().optional(),
      sat_max: z.number().min(0).max(1).optional(),
```

**Status**: ✅ OK si tous les 6 paramètres sont présents

---

### 3. Vérifier que les fonctions V2.1 sont définies

```bash
cd api/services/backtest/strategies
python3 -c "
import sys
sys.path.insert(0, '../../..')
from services.backtest.strategies.core_satellite import (
    compute_scalar_satellite_weight,
    build_unit_satellite_portfolio,
    compute_te_sat,
    compute_ir_sat
)
print('✅ Toutes les fonctions V2.1 sont importables')
"
```

**Expected output**:
```
✅ Toutes les fonctions V2.1 sont importables
```

**Status**: ✅ OK si pas d'erreur d'import

---

### 4. Vérifier que les champs V2.1 sont stockés dans weights_json

```bash
cd api/services/backtest/strategies
grep -n "_cs_alloc_mode\|_cs_sat_weight_scalar\|_cs_te_sat\|_cs_ir_sat" core_satellite.py
```

**Expected output**: ❌ **FAIL** (aucune occurrence trouvée actuellement)

**Status attendu après correctif**: ✅ OK si occurrences trouvées (ex: `weights_dict['_cs_alloc_mode']`)

---

## Vérifications Runtime (Tests)

### 5. Lancer les tests existants

```bash
cd api/tests
PYTHONPATH=.. python -m pytest test_core_satellite_v1.py -v
```

**Expected output**:
```
test_core_satellite_v1.py::test_te_below_target_on_low_risk PASSED
test_core_satellite_v1.py::test_skip_rebalance_on_missing_price PASSED
...
```

**Status**: ✅ OK si tous les tests passent

---

### 6. Test contractuel V2.1 (à créer)

```bash
cd api/tests
PYTHONPATH=.. python -m pytest test_core_satellite_v2_1_contract.py -v
```

**Expected output** (après création du test):
```
test_core_satellite_v2_1_contract.py::test_v2_1_weights_json_contains_fields PASSED
test_core_satellite_v2_1_contract.py::test_v2_1_te_target_mode PASSED
test_core_satellite_v2_1_contract.py::test_v2_1_utility_lambda_mode PASSED
test_core_satellite_v2_1_contract.py::test_v2_1_dynamic_cushion_mode PASSED
```

**Status**: ❌ **FAIL** (test n'existe pas encore)

---

### 7. Test manuel rapide (backtest synthétique)

```bash
cd api
python3 -c "
import sys
sys.path.insert(0, '.')
from services.backtest.strategies.core_satellite import run_core_satellite_backtest
import pandas as pd
from datetime import date

# Créer données synthétiques
dates = pd.date_range('2024-01-01', '2024-01-20', freq='D')
prices_df = pd.DataFrame({
    1: [100.0] * len(dates),
    2: [50.0] * len(dates),
}, index=dates)

# Lancer backtest V2.1
result = run_core_satellite_backtest(
    prices_df=prices_df,
    instrument_ids=[1, 2],
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 20),
    initial_capital=100.0,
    rebalance_frequency='daily',
    fees_bps=0.0,
    slippage_bps=0.0,
    allocation_mode='te_target',
    target_te=0.10,
    debug=True,
)

# Vérifier champs V2.1
if result['portfolio_series']:
    first_bar = result['portfolio_series'][0]
    weights = first_bar.get('weights_json', {})
    v2_1_keys = ['_cs_alloc_mode', '_cs_sat_weight_scalar', '_cs_te_sat', '_cs_ir_sat']
    found = [k for k in v2_1_keys if k in weights]
    missing = [k for k in v2_1_keys if k not in weights]
    
    if missing:
        print(f'❌ FAIL: Champs V2.1 manquants: {missing}')
        print(f'   Trouvés: {found}')
        sys.exit(1)
    else:
        print(f'✅ OK: Tous les champs V2.1 présents: {found}')
else:
    print('❌ FAIL: Pas de portfolio_series')
    sys.exit(1)
"
```

**Expected output** (après correctif):
```
✅ OK: Tous les champs V2.1 présents: ['_cs_alloc_mode', '_cs_sat_weight_scalar', '_cs_te_sat', '_cs_ir_sat']
```

**Status actuel**: ❌ **FAIL** (champs manquants)

---

## Vérifications Frontend

### 8. Vérifier que le build Next.js passe

```bash
cd web
npm run build 2>&1 | grep -E "(error|Error|FAIL)" | head -20
```

**Expected output**: Aucune erreur liée à CORE_SATELLITE

**Status**: ✅ OK si pas d'erreur

---

### 9. Vérifier les types TypeScript

```bash
cd web
npx tsc --noEmit 2>&1 | grep -i "CORE_SATELLITE\|core.satellite" | head -10
```

**Expected output**: Aucune erreur (ou warnings mineurs acceptables)

**Status**: ⚠️ WARNING (types incomplets, mais pas bloquant)

---

## Script d'Audit Automatisé

Le script `scripts/audit_core_satellite_v2_1.py` exécute toutes les vérifications ci-dessus.

### Utilisation

```bash
cd scripts
python3 audit_core_satellite_v2_1.py
```

**Exit code**:
- `0`: ✅ Tous les checks passent
- `1`: ❌ Au moins un check échoue

**Output**:
```
[OK] CORE_SATELLITE présent dans BacktestsTab.tsx (3 occurrences)
[OK] Paramètres V2.1 dans routes.py (6 paramètres)
[OK] Paramètres V2.1 dans route.ts (6 paramètres)
[OK] Fonctions V2.1 importables
[FAIL] Champs V2.1 dans weights_json: _cs_alloc_mode, _cs_sat_weight_scalar, _cs_te_sat, _cs_ir_sat manquants
[OK] Tests V1 passent
[FAIL] Tests V2.1 contractuels manquants
[OK] Build Next.js passe
[WARNING] Types TypeScript incomplets

Résultat: FAIL (2 erreurs critiques)
```

---

## Checklist de Conformité

- [ ] ✅ CORE_SATELLITE dans dropdowns frontend (BacktestsTab.tsx)
- [ ] ✅ Paramètres V2.1 dans Pydantic (routes.py)
- [ ] ✅ Paramètres V2.1 dans Zod (route.ts)
- [ ] ✅ Fonctions V2.1 définies (compute_scalar_satellite_weight, etc.)
- [ ] ❌ Champs V2.1 stockés dans weights_json (CRITIQUE)
- [ ] ✅ Parsing V2.1 dans executor.py
- [ ] ❌ Tests V2.1 contractuels (HAUTE priorité)
- [ ] ✅ Charts CoreSatelliteCharts.tsx créés
- [ ] ⚠️ Types TypeScript complets (optionnel)
- [ ] ❌ Documentation V2.1 (MOYENNE priorité)

---

## Commandes de Correctif Rapide

### Après application des correctifs

1. Vérifier que les champs V2.1 sont stockés:
```bash
cd api/services/backtest/strategies
grep -n "weights_dict\['_cs_" core_satellite.py
```

2. Lancer le test contractuel:
```bash
cd api/tests
PYTHONPATH=.. python -m pytest test_core_satellite_v2_1_contract.py::test_v2_1_weights_json_contains_fields -v
```

3. Test manuel rapide:
```bash
cd api
python3 scripts/quick_test_v2_1.py  # (à créer)
```

---

## Références

- Rapport d'audit complet: `docs/AUDIT_CORE_SATELLITE_V2_1.md`
- Documentation stratégie: `docs/STRATEGY_CORE_SATELLITE.md`
- Code backend: `api/services/backtest/strategies/core_satellite.py`
- Code frontend: `web/src/components/finance/BacktestsTab.tsx`
