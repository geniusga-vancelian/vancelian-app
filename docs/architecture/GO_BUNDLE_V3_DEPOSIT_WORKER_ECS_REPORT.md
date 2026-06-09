# GO — Bundle V3 Deposit Worker ECS

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-09 |
| **Branche** | `feat/bundle-v3-deposit-flow` (PR #67) |
| **Suite** | `pytest tests/test_bundle_v3_deposit_worker_ecs_wiring.py -v` |
| **Résultat global** | **7/7 PASS — GO ECS WIRING** |

---

## Verdict

Le worker `bundle.v3_rebalance_requested` est **branché** au runtime ECS production via le tick observabilité DeFi existant. Aucun nouveau cron, aucun ECS one-shot, aucune dépendance UI.

**Prérequis merge #67** : ce patch est inclus sur la même branche.

---

## Point d'injection ECS

| Couche | Fichier | Rôle |
| --- | --- | --- |
| **Orchestrateur** | `services/defi_observability/tick_service.py` | Step **2e** `bundle_v3_deposit_outbox` |
| **Handler** | `services/portfolio_engine/bundles/bundle_v3_deposit_flow/worker.py` | `process_bundle_v3_deposit_outbox()` |
| **Entrypoint prod** | `scripts/defi_observability_tick.py` | `python3 -m scripts.defi_observability_tick --no-dry-run` |
| **Wrapper ops** | `scripts/run_defi_observability_tick_prod.sh` | Cron / bastion |
| **ECS scheduled** | EventBridge → `arquantix-api` task | Même commande que les outbox workers LiFi |

### Cycle complet (flags ON)

```
POST /bundle/invest
  → status=queued
  → outbox PENDING (bundle.v3_rebalance_requested)
  → defi_observability_tick (cron */10 min)
  → process_bundle_v3_deposit_outbox()
  → execute_v3_bundle_rebalance(trigger=deposit)
  → terminal (COMPLETED | COMPLETED_WITH_RESIDUAL_CASH | FAILED)
  → outbox PROCESSED
  → guard RELEASED
```

### Flag requis

| Variable | Défaut | Prod pilote |
| --- | --- | --- |
| `BUNDLE_V3_DEPOSIT_WORKER_ENABLED` | `false` | `true` (avec les 3 autres flags V3) |

Le step est **skipped** si flag OFF ou `--dry-run`.

---

## Fréquence

| Mécanisme | Intervalle | Notes |
| --- | --- | --- |
| Cron externe (recommandé) | `*/10 * * * *` | Identique outbox LiFi + indexer |
| `--max-duration-seconds` | `480` | Marge si tick long |
| Batch worker | `limit=10` | Aligné outbox intent.created/settle |

Latence max attendue dépôt → rebalance : **~10 min** (intervalle cron), sauf retry immédiat si `next_retry_at` dépassé.

---

## Stratégie anti-double exécution

| Niveau | Mécanisme |
| --- | --- |
| **Tick global** | `pg_try_advisory_lock` — second tick → `skipped_locked`, exit 0 |
| **Poll outbox** | `FOR UPDATE SKIP LOCKED` sur `transaction_outbox` status=PENDING |
| **Lock row** | `status=PROCESSING`, `locked_by={host}:{pid}` |
| **RUNNING V3** | Lock outbox libéré, status repasse PENDING (pas de PROCESSED prématuré) |
| **Terminal V3** | Outbox PROCESSED + guard RELEASED |
| **Idempotence executor** | `execute_v3_bundle_rebalance` + plan_hash / execution_id |

Deux workers ECS simultanés sur le **même** événement : un seul acquiert la row (test D PASS).

---

## Tests obligatoires A–E

| ID | Scénario | Attendu | Résultat | Test |
| --- | --- | --- | --- | --- |
| **A** | outbox PENDING → worker → PROCESSED | 1 polled, 1 processed, guard released | **PASS** | `test_ecs_a_pending_to_processed` |
| **B** | worker crash | outbox PENDING, guard ACTIVE | **PASS** | `test_ecs_b_worker_crash_outbox_stays_pending` |
| **C** | worker restart | 1 funding, reprise idempotente, terminal | **PASS** | `test_ecs_c_worker_restart_idempotent` |
| **D** | 2 workers simultanés | SKIP LOCKED, 1 seul execute | **PASS** | `test_ecs_d_two_workers_no_double_process` |
| **E** | aucun événement V3 | polled=0, flag OFF → skipped | **PASS** | `test_ecs_e_no_v3_events_zero_cost` |

### Intégration tick

| Scénario | Résultat | Test |
| --- | --- | --- |
| Step présent dans `run_defi_observability_tick` (flag ON) | **PASS** | `test_ecs_tick_wires_bundle_v3_deposit_step` |
| Step skipped (flag OFF) | **PASS** | `test_ecs_tick_skips_when_worker_flag_off` |

---

## Vérification prod post-deploy

### 1. Tick manuel (ECS one-shot audit — pas le runtime)

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480'
```

### 2. JSON attendu dans stdout / CloudWatch

```json
"steps": {
  "bundle_v3_deposit_outbox": {
    "enabled": true,
    "polled": 0,
    "processed": 0,
    "failed": 0,
    "skipped": false
  }
}
```

Avec dépôt en file : `polled >= 1`, puis `processed >= 1` au tick suivant si terminal.

### 3. SQL diagnostic

```sql
SELECT id, status, event_type, locked_by, attempt_count, last_error
FROM transaction_outbox
WHERE event_type = 'bundle.v3_rebalance_requested'
ORDER BY created_at DESC
LIMIT 10;
```

---

## Procédure de rollback

### Rollback immédiat (sans revert code)

1. **Désactiver le flag** sur `arquantix-api` ECS task definition :
   - `BUNDLE_V3_DEPOSIT_WORKER_ENABLED=false`
2. **Optionnel** : `BUNDLE_V3_DEPOSIT_FLOW_ENABLED=false` — bloque nouveaux dépôts V3 via `/bundle/invest`
3. Redéployer le service ECS (rolling update)
4. Vérifier tick : `bundle_v3_deposit_outbox.skipped=true` ou `enabled=false`

Les événements PENDING restent en base — **pas de perte**. Réactivation flag → reprise au prochain tick.

### Rollback code (revert PR)

1. Revert merge #67 (ou cherry-pick inverse step 2e `tick_service.py`)
2. Deploy API
3. Flags OFF
4. Traiter manuellement les outbox PENDING restants (runbook incident) ou attendre réactivation

### Ordre recommandé (aligné pilote)

1. Patch worker ECS ← **fait**
2. Review rapide
3. Merge #67
4. Deploy migration 178 + flags OFF
5. Smoke legacy
6. Activer 4 flags Kings
7. Kings +20 réel → audit

---

## Commande tests locale

```bash
cd services/arquantix/api
PYTHONPATH=. .venv/bin/pytest tests/test_bundle_v3_deposit_worker_ecs_wiring.py -v
```

Suite complète pré-merge (gate + ECS + guard) :

```bash
PYTHONPATH=. .venv/bin/pytest \
  tests/test_bundle_v3_deposit_flow_pre_pr_gate.py \
  tests/test_bundle_v3_deposit_worker_ecs_wiring.py \
  tests/test_portfolio_financial_operation_guard.py -v
```
