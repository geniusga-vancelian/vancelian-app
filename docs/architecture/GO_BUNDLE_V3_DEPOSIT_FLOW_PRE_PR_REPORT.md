# GATE PRE-PR — Bundle V3 Deposit Flow

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-09 |
| **Branche** | `feat/bundle-v3-deposit-flow` |
| **Suite** | `pytest tests/test_bundle_v3_deposit_flow_pre_pr_gate.py -v` |
| **Résultat global** | **11/11 PASS — GO PRE-PR** |

---

## Verdict CTO

| Dimension | Estimation |
| --- | --- |
| Architecture V3 | ~95 % |
| Executor | ~90–95 % |
| Deposit Flow (code + tests unitaires gate) | ~85–88 % |
| Prêt stress test réel prod (Swap + 2 bundles) | **Non** — après deploy flags + test ECS |

**PR GitHub** : ouverture autorisée après revue de ce rapport. Stress test réel (Swap + Kings + Majors) reste **bloqué** jusqu’à validation ECS pilote.

---

## Correctif découvert pendant les tests

**Worker `tick_bundle_v3_deposit_worker`** : marquait l’outbox `PROCESSED` même quand `v3_status=RUNNING`. Corrigé — seuls les statuts terminaux clôturent l’outbox ; `RUNNING` libère le lock et remet `PENDING`.

---

## Résultats par scénario

| # | Scénario | Attendu | Résultat | Test |
| --- | --- | --- | --- | --- |
| **1** | Kings +20 USDC lifecycle | QUEUED → FUNDED → REBALANCE_REQUESTED → COMPLETED · guard ACTIVE→RELEASED | **PASS** | `test_gate_01_kings_deposit_full_lifecycle` |
| **2** | Kings +20 puis +20 immédiat | 1er queued · 2e `409 portfolio_financial_operation_in_progress` · 0 swap 2e | **PASS** | `test_gate_02_double_kings_deposit_second_409` |
| **3** | Kings +20 + Majors +20 | 2 opérations parallèles · 2 execution_id · 2 terminaux | **PASS** | `test_gate_03_kings_and_majors_parallel` |
| **4** | Crash worker après funding | Même intent/execution_id · 1 funding · reprise idempotente | **PASS** | `test_gate_04_worker_crash_after_funding_idempotent_resume` |
| **5** | Leg fail → retry → success | `MAX_SWAP_ATTEMPTS=2` · attempts=2 · terminal · pas resume | **PASS** | `test_gate_05_leg_fail_then_success_terminal` |
| **6** | Leg fail ×2 | `COMPLETED_WITH_RESIDUAL_CASH` ou `FAILED` · jamais `RUNNING` stuck | **PASS** | `test_gate_06_leg_fail_twice_never_running_stuck` |
| **7** | Swap classique + Kings + Majors | Pas de contamination guard inter-portfolios | **PASS** | `test_gate_07_classic_swap_and_bundle_deposits_isolated` |
| **8a** | Release guard `COMPLETED` | 0 ACTIVE orphan | **PASS** | `test_gate_08_guard_released_on_all_terminal_statuses[COMPLETED]` |
| **8b** | Release guard `COMPLETED_WITH_RESIDUAL_CASH` | 0 ACTIVE orphan | **PASS** | `test_gate_08_guard_released_on_all_terminal_statuses[COMPLETED_WITH_RESIDUAL_CASH]` |
| **8c** | Release guard `FAILED` | status FAILED · 0 ACTIVE orphan | **PASS** | `test_gate_08_guard_released_on_all_terminal_statuses[FAILED]` |
| **8d** | Batch 3 dépôts | 0 ACTIVE orphan global | **PASS** | `test_gate_08_no_active_orphans_after_batch` |

---

## Détail TEST 1 — Lifecycle

```
POST request_v3_bundle_deposit
  status: queued
  guard: ACTIVE
  outbox: PENDING (bundle.v3_rebalance_requested)

Worker tick
  v3_status: COMPLETED
  guard: RELEASED
  outbox: PROCESSED
```

---

## Détail TEST 2 — Double dépôt

```
Dépôt 1 → queued (guard ACTIVE)
Dépôt 2 → PortfolioFinancialOperationInProgress409
  error_code: portfolio_financial_operation_in_progress
Swaps créés pour dépôt 2 : 0
```

---

## Détail TEST 4 — Crash worker

```
fund_bundle_cash_leg calls : 1
execute_v3_bundle_rebalance calls : 2 (1 crash + 1 succès)
Outbox après crash : PENDING (retry)
Outbox après reprise : PROCESSED
```

---

## Limites connues (hors scope gate unitaire)

| Item | Statut |
| --- | --- |
| Test HTTP 202 réel WebApp | Non couvert — mocks funding/execute |
| Worker ECS cron prod | Non déployé |
| `INTERNAL_SWAP` câblé au guard | Non — TEST 7 valide l’isolation portfolio |
| Sell-then-buy cash insuffisant (TEST 6 planner) | Couvert indirectement via executor existant PR-3 |
| Désactivation `_invest_via_lifi` flag ON | Câblé route · pas testé ECS |

---

## Commande reproductible

```bash
cd services/arquantix/api
PYTHONPATH=. .venv/bin/pytest tests/test_bundle_v3_deposit_flow_pre_pr_gate.py -v
```

---

## Prochaines étapes (post-merge)

1. Merger PR-4 + PR V3 Deposit Flow
2. Deploy migration 178 + flags OFF
3. Activer pilote : `BUNDLE_V3_DEPOSIT_FLOW_ENABLED` + worker + executor + guard sur Kings
4. Test ECS réel +20 USDC
5. **Ensuite seulement** : stress Swap + Kings + Majors
