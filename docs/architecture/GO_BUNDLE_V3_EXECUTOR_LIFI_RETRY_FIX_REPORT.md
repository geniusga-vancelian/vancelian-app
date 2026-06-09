# GO — Bundle V3 Executor LI.FI Retry Fix Report

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-09 |
| **Contexte** | Kings V3 — buy ETH `quote_ttl_expired` en ~3 s, `attempts=1` malgré `MAX_SWAP_ATTEMPTS=2` |
| **Sources** | `BUNDLE_FORENSIC_AUDIT_LAST_TWO_DEPOSITS.md`, `deposit_timeline.json` |
| **Verdict** | **CORRECTIF CODE + TESTS OK** — déploiement ECS requis avant preuve prod |

---

## 1. Cause racine

### 1.1 Comportement observé prod

| Dépôt | Swap ETH | TTL | Attempts | Terminal |
| --- | --- | --- | --- | --- |
| #1 `efa20c53` | `4d985286` | ~3 s | **1** | `COMPLETED_WITH_RESIDUAL_CASH` |
| #2 `40a300b1` | (analogue) | ~2 s | **1** | `COMPLETED_WITH_RESIDUAL_CASH` |

### 1.2 Analyse code (`rebalance_executor.py`)

Boucle `_execute_plan_legs` (avant correctif) :

```python
if leg_result.status == "pending":
    break  # ← sortie immédiate, pas de 2e tentative
```

En prod, LI.FI retourne `pending` + `requires_client_signature: true` (worker headless, pas de signature WebApp). Le leg restait `pending`, puis `_expire_pending_legs` le marquait `quote_ttl_expired` **sans re-quote**.

**Écart** : `MAX_SWAP_ATTEMPTS=2` configuré mais **jamais consommé** sur le chemin pending/LI.FI.

---

## 2. Correctif

### 2.1 Résolution pending → retryable

Nouvelle méthode `_resolve_pending_leg` :

| Cas swap DB / raw | Résolution | Action |
| --- | --- | --- |
| `requires_client_signature` | `expired` / `quote_ttl_expired` | **re-quote** (attempt 2) |
| Swap `QUOTE_RECEIVED` / `AWAITING_SIGNATURE` | `expired` / `quote_ttl_expired` | **re-quote** |
| Swap `EXPIRED` / `FAILED` | `expired` | **re-quote** si attempts < max |
| Swap confirmé | `completed` | terminal OK |
| Swap `SUBMITTED` | `pending` | attente confirmation |

### 2.2 Journalisation par tentative

`V3LegExecutionResult.attempt_details[]` :

```json
{
  "attempt_index": 1,
  "leg_id": "v3-rebal-...-a1",
  "swap_id": "...",
  "status": "expired",
  "error_code": "quote_ttl_expired"
}
```

Exposé dans `buy_results` / `sell_results` du terminal audit.

### 2.3 Terminal residual

`COMPLETED_WITH_RESIDUAL_CASH` n’est émis qu’après **épuisement** des `MAX_SWAP_ATTEMPTS` (défaut 2), pas après la 1re expiration.

---

## 3. Tests obligatoires

| Scénario | Test | Résultat |
| --- | --- | --- |
| attempt 1 expired → attempt 2 success → `COMPLETED` | `test_quote_ttl_expired_retry_success_on_attempt2` | **PASS** |
| attempt 1 + 2 expired → `COMPLETED_WITH_RESIDUAL_CASH` | `test_quote_ttl_expired_both_attempts_terminal_residual` | **PASS** |
| attempts never > 2 | assertions `attempts == 2` + `len(calls) == 2` | **PASS** |
| no duplicate PE/CB before confirmation | `test_quote_ttl_expired_both_attempts_terminal_residual` (counts) | **PASS** |
| pending ×2 → terminal sans resume | `test_timeout_pending_becomes_terminal_no_resume` (mis à jour) | **PASS** |
| leg fail puis success (gate) | `test_gate_05_leg_fail_then_success_terminal` | **PASS** (existant) |
| leg fail ×2 (gate) | `test_gate_06_leg_fail_twice_never_running_stuck` | **PASS** (existant) |

Commande :

```bash
cd services/arquantix/api
PYTHONPATH=. .venv/bin/pytest \
  tests/test_bundle_rebalance_executor.py \
  tests/test_bundle_v3_deposit_flow_pre_pr_gate.py::test_gate_05_leg_fail_then_success_terminal \
  tests/test_bundle_v3_deposit_flow_pre_pr_gate.py::test_gate_06_leg_fail_twice_never_running_stuck \
  -q
```

---

## 4. Comportement attendu post-déploiement

```
attempt 1: execute_leg → pending (requires_client_signature)
         → _resolve_pending_leg → expired (quote_ttl_expired)
         → continue (attempt < MAX_SWAP_ATTEMPTS)

attempt 2: execute_leg → re-quote immédiat
         → completed OU expired

si attempt 2 expired → COMPLETED_WITH_RESIDUAL_CASH (terminal, guard released)
si attempt 2 completed → COMPLETED
```

**Interdit** : `attempt 1 expired → COMPLETED_WITH_RESIDUAL_CASH` avec `attempts=1`.

---

## 5. Déploiement

| Étape | Statut |
| --- | --- |
| Code executor + tests | **OK** — 39 tests PASS |
| Deploy ECS `arquantix-api:169` | **OK** — commit `c0d1b224`, GHA success |
| Preuve prod code déployé | **OK** — `_resolve_pending_leg`, `attempt_details`, `MAX_SWAP_ATTEMPTS=2` |
| Preuve prod swap réel | **EN ATTENTE** — pas de dépôt (NO_GO jusqu'à GO final) |

---

## 6. Critère GO

| Condition | Statut |
| --- | --- |
| Retry 2 attempts prouvé en tests | **OK** |
| Retry 2 attempts code en prod (`:169`) | **OK** (vérif statique ECS) |
| Worker auto (Partie A) | **OK** — voir `GO_BUNDLE_V3_WORKER_CADENCE_FIX_REPORT.md` |
| Kings +20 unique | **CONDITIONNEL** — possible après 1 swap réel confirme attempt 2 si TTL expire |
