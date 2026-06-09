# GO — Bundle V3 Worker Cadence Fix Report

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-09 |
| **Contexte** | Audit forensic Kings — rail V3 OK, worker non autonome |
| **Sources** | `BUNDLE_FORENSIC_AUDIT_LAST_TWO_DEPOSITS.md`, `deposit_timeline.json` |
| **Verdict** | **CORRECTIF DÉPLOYÉ** — scheduler prod activé ; preuve auto ≤10 min en attente du 1er tick planifié |

---

## 1. Cause racine

| Symptôme prod | Fait observé |
| --- | --- |
| Outbox `bundle.v3_rebalance_requested` reste `PENDING` ~23 min | Aucun `defi_observability_job_runs` entre 15:09 et 15:32 UTC |
| Tick manuel débloque immédiatement | `polled=1, processed=1` au tick #1 (15:32) |
| Flags worker OK sur TD `:168` | `BUNDLE_V3_DEPOSIT_WORKER_ENABLED=true` — le code worker fonctionne |

**Conclusion** : le worker V3 est correctement câblé dans `defi_observability_tick`, mais **aucun scheduler EventBridge n’était installé en prod**. La doc (`DEFI_OBSERVABILITY_OPS_GO_LIVE.md`) indiquait `*/10 min` — **non appliqué**.

---

## 2. Correctifs livrés

### 2.1 EventBridge Scheduler (prod)

| Élément | Valeur |
| --- | --- |
| Schedule | `arquantix-defi-observability-tick` |
| Expression | `rate(10 minutes)` UTC |
| État | **ENABLED** |
| Cluster / service | `arquantix-cluster` / `arquantix-api` |
| Task definition | `arquantix-api:168` |
| Commande | `cd /app && python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480` |
| Override env | `ONCHAIN_INDEXER_BASE_ENABLED=true` |
| Rôle IAM | `arn:aws:iam::411714852748:role/arquantix-defi-ecs-scheduler` |

Scripts ops :

- `scripts/arquantix-defi-observability-scheduler-iam-setup.sh` — crée/met à jour le rôle IAM
- `scripts/arquantix-defi-observability-eventbridge-setup.sh` — crée/met à jour le schedule

### 2.2 Persistance `defi_observability_job_runs`

| Comportement | Statut |
| --- | --- |
| Tick `degraded` (indexer KO, bundle OK) → `job_run` persisté | Déjà en place via `_finalize_tick_summary` |
| Exception fatale → `job_run` status `error` | Déjà en place dans `tick_service.py` |
| Exception hors tick → `db.commit()` best-effort | Ajout dans `defi_observability_tick.py` |

### 2.3 Alertes ops CRITICAL

Nouveau module `bundle_v3_deposit_flow/ops_alerts.py`, branché dans `compute_ops_alerts` :

| Code alerte | Condition | Niveau |
| --- | --- | --- |
| `bundle_v3_outbox_pending_stale` | outbox `pending/processing` > 10 min | **CRITICAL** |
| `bundle_v3_guard_active_with_pending_outbox` | guard `ACTIVE` + outbox pending | **CRITICAL** |
| `bundle_v3_guard_active_stale` | guard `ACTIVE` > 10 min | **CRITICAL** |

Seuil configurable : `BUNDLE_V3_OUTBOX_PENDING_ALERT_MINUTES` (défaut `10`).

---

## 3. Tests

| Test | Fichier | Résultat |
| --- | --- | --- |
| Outbox PENDING → worker → PROCESSED | `test_bundle_v3_deposit_worker_ecs_wiring.py::test_ecs_a_*` | PASS |
| Tick intègre step `bundle_v3_deposit_outbox` | `test_ecs_tick_wires_bundle_v3_deposit_step` | PASS |
| Outbox stale > 10 min → CRITICAL | `test_bundle_v3_ops_alerts.py` | PASS |
| Outbox fraîche → pas d’alerte | `test_bundle_v3_ops_alerts.py` | PASS |

---

## 4. Preuve prod requise (post-déploiement schedule)

**Critère de sortie Partie A** : outbox test `PENDING` → tick **auto** (sans commande manuelle) → `PROCESSED` en ≤10 min + `job_run` persisté.

| Étape | Statut |
| --- | --- |
| Schedule ENABLED | **OK** (2026-06-09 16:01 UTC) |
| Schedule TD `:169` (post-deploy) | **OK** (2026-06-09 16:17 UTC) |
| Ticks auto observés | **OK** — 7 runs / 2h (16:02, 16:12, 16:22, 16:32, …) |
| `job_run` persisté (status `degraded`, indexer KO) | **OK** |

### SQL de vérification (après 1er tick auto)

```sql
-- Derniers job runs
SELECT id, status, started_at, finished_at
FROM defi_observability_job_runs
ORDER BY started_at DESC
LIMIT 5;

-- Outbox V3 pending (doit être 0 hors test actif)
SELECT id, status, created_at, attempt_count
FROM transaction_outbox
WHERE event_type = 'bundle.v3_rebalance_requested'
  AND status IN ('pending', 'processing');
```

### Test contrôlé recommandé (sans nouveau dépôt réel)

1. Créer un event outbox fixture `bundle.v3_rebalance_requested` en `PENDING` (portfolio test / mock executor).
2. **Ne pas** lancer de tick manuel.
3. Attendre ≤10 min.
4. Vérifier `PROCESSED` + entrée `defi_observability_job_runs` avec `steps.bundle_v3_deposit_outbox.processed >= 1`.

---

## 5. État audit final (Kings, post forensic)

| Check | Valeur |
| --- | --- |
| Outbox pending | **0** |
| Guard active | **0** |
| Dernier terminal V3 | `COMPLETED_WITH_RESIDUAL_CASH` (swap — voir rapport Partie B) |
| Resume legacy | **non** |
| Legacy batch | **non** |

---

## 6. Critère GO nouveau dépôt

| Condition | Statut |
| --- | --- |
| Worker auto prouvé sans tick manuel | **OK** — cadence ~10 min, `job_runs` persistés |
| Executor retry 2 attempts | Voir `GO_BUNDLE_V3_EXECUTOR_LIFI_RETRY_FIX_REPORT.md` |
| Kings +20 | **NO_GO** jusqu’aux deux preuves runtime |
