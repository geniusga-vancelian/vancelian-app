# Bundle Allocation Execution — Phase 5A

Optimisation P0 du moteur d'allocation bundle (fund-first inchangé).

**Audit source :** [BUNDLE_ALLOCATION_EXECUTION_ENGINE_AUDIT.md](./BUNDLE_ALLOCATION_EXECUTION_ENGINE_AUDIT.md)

---

## Résumé

| Feature | Statut | Default |
|---------|--------|---------|
| Execution buffer USDC | ✅ | `1.0` USDC |
| Execution buffer BPS (optionnel) | ✅ | désactivé |
| Quotes parallèles LI.FI | ✅ | **désactivé** |
| Settlement PE montants réels | ✅ | toujours actif |
| Planned amounts en metadata ledger | ✅ | — |

**Non modifié :** Mon Trading, fund-first, retrait, ledger history switch, recovery, legacy Exchange.

---

## Flags environnement

| Variable | Default | Description |
|----------|---------|-------------|
| `BUNDLE_ALLOC_EXECUTION_BUFFER_USDC` | `1.0` | USDC conservés en cash leg (non alloués) |
| `BUNDLE_ALLOC_EXECUTION_BUFFER_BPS` | *(vide)* | Si défini : `buffer = max(USDC, fund × bps/10000)` |
| `BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED` | `false` | Quotes LI.FI en parallèle (max 5 legs) |

---

## Comportement

### 1. Execution buffer

```
fund 1000 USDC → cash leg +1000
allocatable = 1000 − buffer (ex. 999)
legs planifiés sur allocatable × poids
reliquat = buffer + dust ROUND_DOWN → reste cash leg
```

Fichiers :
- `bundle_execution/allocation_config.py`
- `bundle_execution/allocation_planner.py`

Preview invest expose : `execution_buffer`, `allocatable_amount`.

### 2. Quotes parallèles (opt-in)

Activé uniquement si :
- `BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=true`
- Provider `lifi_base`
- Plus d'un leg planifié

Comportement :
- `commit` du fund avant quotes (sessions worker isolées)
- `ThreadPoolExecutor`, max **5** workers
- Fallback séquentiel si flag off

Fichier : `bundle_execution/allocation_parallel.py`

### 3. Settlement PE réel

À CONFIRMED, priorité :
- **Débit cash leg :** audit `actual_amount_in` → LI.FI `sending` → quote `amount_in`
- **Crédit spot :** audit `actual_receive_amount` → on-chain/status → quote

Ledger shadow : `planned_entry_consumed`, `planned_crypto_received` en metadata.

Fichiers :
- `bundle_execution/allocation_settlement.py`
- `bundle_lifi_leg_service._apply_pe_atoms_for_leg`
- `bundle_ledger/service.record_allocation_buy`

---

## Rollout recommandé

### Étape 1 — Buffer seul (prod)

```bash
BUNDLE_ALLOC_EXECUTION_BUFFER_USDC=1.0
BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=false
```

Vérifier : cash leg résiduel ≈ buffer + dust après invest Top 5.

### Étape 2 — Staging quotes parallèles

```bash
BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=true
```

Smoke :
```bash
cd services/arquantix/api
python3 -m pytest tests/test_bundle_allocation_phase5a.py -q
python3 -m scripts.smoke_bundle_ledger_history --person-id ... --portfolio-id ...
```

### Étape 3 — Prod limitée

Panel 1 → 3 portfolios avec parallel ON, monitor latence invest + EXPIRED quotes.

---

## Rollback

| Action | Effet |
|--------|-------|
| `BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED=false` | Retour quotes séquentielles immédiat |
| `BUNDLE_ALLOC_EXECUTION_BUFFER_USDC=0` | Plus de buffer (legs sur 100 % fund) |
| Redémarrer API | Prise en compte flags |

Aucune migration DB. Aucune suppression ledger/atoms.

---

## Tests

```bash
cd services/arquantix/api
python3 -m pytest tests/test_bundle_allocation_phase5a.py -q
```

Couverture :
- buffer réduit le plan
- parallel runner invoqué (flag ON)
- cash résiduel en cash leg
- settlement réel ≠ plan
- leg failed / autres OK
- finalize sans micro-retry
- bundle recoverable si tous legs failed

---

## Fichiers modifiés

| Fichier | Rôle |
|---------|------|
| `allocation_config.py` | Flags + buffer |
| `allocation_planner.py` | Plan legs post-buffer |
| `allocation_parallel.py` | Séquentiel / parallèle |
| `allocation_settlement.py` | Montants réels PE |
| `bundles/orchestrator.py` | Intégration invest + preview |
| `bundle_lifi_leg_service.py` | Settlement réel |
| `bundle_ledger/service.py` | Metadata planned |

---

## Phase 5A.5 — validation

- Smoke : `scripts/smoke_bundle_allocation_phase5a.py`
- Rollout : [BUNDLE_ALLOCATION_PHASE5A_ROLLOUT.md](./BUNDLE_ALLOCATION_PHASE5A_ROLLOUT.md)
- Logs : `bundle_allocation.*` (plan, quotes, settlement, residual)

---
