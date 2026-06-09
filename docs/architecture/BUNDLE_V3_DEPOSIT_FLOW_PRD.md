# PRD — Bundle V3 Deposit Flow (finalisation raccordement)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-09 |
| **Prérequis** | PR-1 Drift · PR-2 Planner · PR-3 Executor · PR-4 FinancialOperationGuard |
| **Flag** | `BUNDLE_V3_DEPOSIT_FLOW_ENABLED` — OFF par défaut |
| **Hors scope** | PR-5 Lifecycle UI · Global Lock |

---

## Objectif

Faire du moteur V3 le **chemin officiel** de dépôt Bundle WebApp :

```
Deposit Bundle → Queue → Worker → Funding USDC cash leg → Rebalance V3 → Terminal
```

Le portefeuille = source de vérité. Le batch = rapport d'exécution uniquement.

---

## Étape 1 — Audit chemins legacy actifs

| legacy_path | used_in_prod | used_in_ui | can_be_removed_after_v3 | risk |
| --- | --- | --- | --- | --- |
| `_invest_via_lifi` | **Oui** — `POST /bundle/invest` USDC | Oui — `useBundleLifiInvest`, `PortalBundleInvestFlow` | **Non** — remplacé par ce PR | **Critique** |
| `resume_lifi_invest_batch` | **Oui** — recovery stuck legs | Oui — « Reprendre l'investissement » | **Partiel** — recovery historique seulement | **Élevé** |
| `bundle_invest_lock` / `peek` / `active-lock` | **Oui** — 1 lock/portfolio | Oui — panels allocation | **Partiel** — remplacé par FinancialOperationGuard + états V3 | **Critique** |
| `reconciliation_required` / `partial_in_progress` | Oui — read model + audits | Partiel — variantes UI, endpoint mort | **Partiel** — read model conservé, statuts legacy supprimés pour nouveaux dépôts | **Moyen** |
| `expired_invest_legs` / `requote_expired_invest_legs` | Oui — recovery post-incident | Oui — « Relancer l'allocation » | **Oui** après fermeture batches legacy | **Moyen-élevé** |

### Infrastructure queue existante (flags OFF prod)

| Pattern | Flag | Statut |
| --- | --- | --- |
| `transaction_outbox` | `LIFI_OUTBOX_WORKER_ENABLED` | LI.FI swaps, pas bundle invest |
| `bundle_funding_handler` | `BUNDLE_FUNDING_HANDLER_ENABLED` | Préparé B3a |
| `bundle_leg_settlement_handler` | `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | Préparé B3c |
| `bundle_b4b_runtime_bridge` | `BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED` | Tests contrôlés |
| V3 executor | `BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED` | Parallèle legacy, mock ECS OK |

---

## Étape 2 — Workflow cible

```
POST /bundle/invest (flag V3 deposit ON)
  │
  ├─ FinancialOperationGuard.acquire(BUNDLE_INVEST)
  ├─ FundBundleCashLeg (fund_bundle_cash_leg_from_self_trading)
  ├─ Create parent intent bundle_deposit_v3
  ├─ Enqueue outbox: bundle.v3_rebalance_requested
  └─ Return { status: "queued", deposit_execution_id, ... }

Worker (bundle_v3_deposit_worker)
  │
  ├─ Idempotence: plan_hash / execution_id
  ├─ compute_bundle_drift_snapshot + plan_bundle_rebalance_from_drift
  ├─ execute_v3_bundle_rebalance(trigger=deposit)
  ├─ FinancialOperationGuard.release() si terminal
  └─ Audit terminal (COMPLETED | COMPLETED_WITH_RESIDUAL_CASH | FAILED)
```

**États terminaux uniquement** pour nouveaux dépôts V3 — pas de `partial_in_progress`, `awaiting_signature`, `resume_required`.

---

## Étape 3 — Interdictions (nouveaux dépôts, flag ON)

| Interdit | Alternative |
| --- | --- |
| `resume_lifi_invest_batch` | 409 `v3_deposit_flow_resume_disabled` |
| `requote_expired_invest_legs` (nouveau dépôt) | `trigger=recovery` rebalance V3 |
| `acquire_invest_lock` / allocation legs LI.FI | Rebalance V3 buy-only/sell-then-buy |
| `peek_bundle_invest_lock` actif | FinancialOperationGuard + drift |

Recovery historique : chemins legacy restent accessibles **flag OFF** ou allowlist recovery.

---

## Étape 4 — Worker transactionnel

| Garantie | Mécanisme |
| --- | --- |
| Funding réussi OU rollback | Transaction HTTP request ; outbox enqueue même txn |
| Rebalance lancé 1× | `uq_outbox_intent_event_type` + idempotence executor |
| Retry worker | `attempt_count` / `next_retry_at` outbox |
| Crash reprise | `ACTION_V3_PROGRESS` audit + `find_running_v3_rebalance_execution` |
| Audit complet | `pe_audit_events` V3 terminal + deposit ledger |

---

## Étape 5 — Tests obligatoires

| # | Scénario | Attendu |
| --- | --- | --- |
| 1 | 1 dépôt Kings | Terminal COMPLETED* |
| 2 | 2 dépôts Kings simultanés | Second = 409 |
| 3 | Kings + Majors simultanés | OK (portefeuilles différents) |
| 4 | Crash worker mid-flight | Reprise idempotente |
| 5 | Leg échoué | 2 retries → FAILED terminal |
| 6 | Cash insuffisant pour buy | sell puis buy (planner) |

---

## Déploiement

1. Migration outbox event type (si enum étendu)
2. Deploy flag OFF — comportement legacy inchangé
3. `BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED=true` + `PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED=true`
4. `BUNDLE_V3_DEPOSIT_FLOW_ENABLED=true` pilote Kings
5. Test +20 USDC Kings/Majors puis stress concurrent

---

## Après cette PR

Désactivation progressive pour **nouveaux** dépôts :

- `bundle_invest_lock`
- `active-lock` UI
- `resume_lifi_invest_batch`
- `requote_expired_invest_legs`

Puis test final : Kings +20 · Majors +20 · Swap classique (robustesse réelle).
