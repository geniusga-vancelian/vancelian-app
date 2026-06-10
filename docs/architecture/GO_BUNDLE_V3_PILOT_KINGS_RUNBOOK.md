# Runbook pilote — Kings +20 USDC (V3 Deposit Flow)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-09 |
| **PR mergée** | [#67](https://github.com/geniusga-vancelian/vancelian-app/pull/67) · `6d5ecedc` |
| **Compte** | gaelitier@gmail.com |
| **Portfolio** | Two Crypto Kings · `daea3720-e58e-410f-a796-3bbd541ac608` |
| **Majors** | `ab4ae920-f3e8-481b-8f82-a41a81d5779d` — **hors périmètre** jusqu’à validation Kings |

---

## Prérequis (post-merge)

| # | Action | Gate |
| --- | --- | --- |
| 0 | **Clôturer batch legacy `d1cbf600`** | [`GO_BUNDLE_LEGACY_BATCH_D1CBF600_CLOSE_RUNBOOK.md`](GO_BUNDLE_LEGACY_BATCH_D1CBF600_CLOSE_RUNBOOK.md) · `peek=none` |
| 1 | Merge PR #67 | Fait |
| 2 | Deploy migration **178** | `portfolio_financial_operations` existe |
| 3 | Deploy API avec **tous flags OFF** | Legacy inchangé |
| 4 | Activer **4 flags ensemble** | `./scripts/arquantix-ecs-pilot-v3-bundle-flags-activate.sh` |
| 5 | Re-audit flags | `all_required_flags_on=true` |

**Ne pas lancer** le stress Swap + Kings + Majors avant les 3 cycles nominaux (Kings×2 + Majors×1).

---

## Flags pilote (Kings uniquement)

```bash
PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED=true
BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED=true
BUNDLE_V3_DEPOSIT_FLOW_ENABLED=true
BUNDLE_V3_DEPOSIT_WORKER_ENABLED=true
```

Pas sur Majors. Pas globalement.

---

## Audit minimal — avant dépôt

### 1. Financial guard

```sql
SELECT id, portfolio_id, status, operation_type, batch_id, created_at, released_at
FROM portfolio_financial_operations
WHERE portfolio_id = 'daea3720-e58e-410f-a796-3bbd541ac608'
ORDER BY created_at DESC
LIMIT 10;
```

**Attendu :** `0` ligne `status = 'ACTIVE'`.

### 2. Cash leg Kings

Vérifier UI ou audit bundle : cash leg USDC ≈ **45.69 USDC** (valeur indicative pré-dépôt).

### 3. V3 running

Script ECS (read-only) :

```bash
./scripts/arquantix-ecs-bundle-v3-batch-lifecycle-audit.sh
```

**Attendu :** `find_running_v3_rebalance_execution` = **null**.

---

## Dépôt +20 USDC (cycle 1)

### Action utilisateur

Deposit **20 USDC** sur Two Crypto Kings via `/bundle/invest`.

### Attendu immédiatement

| Artefact | État |
| --- | --- |
| `portfolio_financial_operations` | `ACTIVE`, `operation_type = BUNDLE_INVEST` |
| `transaction_outbox` | `bundle.v3_rebalance_requested`, `PENDING` |
| Réponse API | `status=queued`, `flow=bundle_v3_deposit` |

```sql
SELECT id, status, event_type, locked_by, attempt_count, created_at
FROM transaction_outbox
WHERE event_type = 'bundle.v3_rebalance_requested'
ORDER BY created_at DESC
LIMIT 5;
```

---

## Tick ECS suivant (≤ 10 min)

Le worker tourne dans `defi_observability_tick` (step `bundle_v3_deposit_outbox`).

Tick manuel si besoin :

```bash
./scripts/arquantix-ecs-run-job.sh arquantix-api arquantix-api \
  'cd /app && python3 -m scripts.defi_observability_tick --no-dry-run --max-duration-seconds 480'
```

### Séquence attendue

| Étape | Signal |
| --- | --- |
| Outbox consommée | `PROCESSED` |
| Executor démarre | `ACTION_V3_RUNNING` (`v3_execution_running`) |
| Legs en cours | `ACTION_V3_PROGRESS` (`v3_execution_progress`) |
| Fin | `ACTION_V3_TERMINAL` — `COMPLETED` ou `COMPLETED_WITH_RESIDUAL_CASH` |

**Jamais** `RUNNING` > **30 min**.

Comportement nominal attendu (drift faible, cash suffisant) :

```
USDC cash → funding cash leg → drift → plan buy ETH → swap LI.FI → terminal → guard release
```

Aucun : resume · lock orphelin · batch historique · requote · expired legs · ambiguous.

---

## Vérifications finales (cycle 1)

Toutes **vraies simultanément** :

| Check | Attendu |
| --- | --- |
| `resume_required` | `false` |
| `find_running_v3_rebalance_execution` | `null` |
| `portfolio_financial_operations` ACTIVE | `0` |
| outbox `PENDING` (V3 deposit) | `0` |
| ghost legs | `0` |
| active invest lock | `none` |

Audit ghost legs (read-only) :

```bash
./scripts/arquantix-ecs-bundle-ghost-legs-classification-audit.sh
```

---

## Cycle 2 — deuxième +20 USDC (sans intervention)

**Sans** nettoyage · **sans** script · **sans** intervention humaine.

Refaire Deposit +20 sur Kings.

| Cycle | Attendu |
| --- | --- |
| 1er dépôt | `COMPLETED` ou `COMPLETED_WITH_RESIDUAL_CASH` |
| 2e dépôt | idem, sans intervention |

Si le 2e cycle termine aussi en terminal → **cœur V3 pratiquement validé**.

---

## STOP immédiat (avant Majors)

Arrêter et corriger si :

| Symptôme | Action |
| --- | --- |
| `RUNNING` > 30 min | STOP — investiguer executor / swaps |
| Guard `ACTIVE` + exécution terminale | STOP — release guard manquant |
| Outbox bloquée `PENDING` | STOP — worker ECS / flag `BUNDLE_V3_DEPOSIT_WORKER_ENABLED` |
| Delta PE/CB incohérent | STOP — audit reconciliation |

Rollback rapide worker :

```bash
BUNDLE_V3_DEPOSIT_WORKER_ENABLED=false
BUNDLE_V3_DEPOSIT_FLOW_ENABLED=false
```

---

## Rééquilibrage Kings — drift NAV `portfolio_value`

Deploy : drift sur **NAV totale** (spot + cash leg) + **chaîne LI.FI** + **reprise worker UI** au chargement page bundle.

| Action | Route |
| --- | --- |
| Worker en cours (read-only) | `GET /bundle/daea3720-…/active-operation` |
| Preview | `POST /bundle/daea3720-…/rebalancing/preview` |
| Démarrer | `POST /bundle/daea3720-…/rebalancing` → `v3_status=RUNNING` |
| Après chaque signature | `POST /bundle/daea3720-…/rebalancing/resume` |

**Attendu Kings — cash dominant** (cash ~125 USDC, investi ~35 USDC) :

- Preview : `planning_mode=portfolio_drift` · `weight_basis=portfolio_value` · achats **BTC ~86 USDC** + **ETH ~39 USDC**.

**Attendu Kings — cash résiduel** (cash ~6,4 USDC, investi ~12 USDC, NAV ~18,4 USDC) :

- Preview : achat **ETH ~5,5 USDC** (pas ~3,6 sur base investie seule).

Architecture : **[`BUNDLE_V3_PORTFOLIO_VALUE_DRIFT_AND_ACTIVE_OPERATION_ARCHITECTURE.md`](BUNDLE_V3_PORTFOLIO_VALUE_DRIFT_AND_ACTIVE_OPERATION_ARCHITECTURE.md)** · **[`BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md`](BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md)**.

Validation ECS :

```bash
./scripts/arquantix-ecs-bundle-drift-engine-audit.sh
./scripts/arquantix-ecs-bundle-v3-deposit-prod-audit.sh
```

---

## Après Kings (étape suivante)

| # | Action | Gate |
| --- | --- | --- |
| 1 | Kings +20 × 2 terminaux | Ce runbook |
| 2 | Activer flags **Majors** | Même 4 flags, portfolio `ab4ae920-…` |
| 3 | Majors +20 | Terminal |
| 4 | Stress T0/T+3s/T+6s | **Seulement après** les 3 cycles ci-dessus |

Stress test cible :

```
T0     Swap utilisateur
T0+3s  Kings +20
T0+6s  Majors +20
```

Chercher : swap normal · Kings OK · Majors OK · 0×500 · 0 deadletter · 0 double funding · 0 lock orphelin.

---

## Rééquilibrage portefeuille — pilote Majors

Portfolio **Crypto Majors** (`ab4ae920-f3e8-481b-8f82-a41a81d5779d`) : hors V3 deposit flow tant que Kings n’est pas validé, mais le **rééquilibrage manuel** est déjà câblé (remplace « Reprendre l’investissement »).

| Action | Route / entrée |
| --- | --- |
| Preview (read-only) | `POST /bundle/{portfolio_id}/rebalancing/preview` |
| Exécution | `POST /bundle/{portfolio_id}/rebalancing` · bouton portail **Rééquilibrage** |
| Reprise post-signature | `POST /bundle/{portfolio_id}/rebalancing/resume` |

**Comportement nominal Majors** : `planning_mode=portfolio_drift` · drift sur NAV (cash dilue les surpondérations spot) · achats depuis cash leg · `executeBundleTrade` + `resume` entre legs.

Workflow logique, formules de drift/plan et comptabilité PE : **[`BUNDLE_PORTFOLIO_REBALANCING_ARCHITECTURE.md`](BUNDLE_PORTFOLIO_REBALANCING_ARCHITECTURE.md)**.

**Gate** : ne pas lancer un rééquilibrage Majors en prod tant que Kings n’a pas produit **2 cycles dépôt terminaux** (section « Cycle 2 » ci-dessus), sauf preview read-only pour diagnostic.

---

## Confiance actuelle

| Couche | Niveau |
| --- | --- |
| Architecture | ~97 % |
| Code | ~92–95 % |
| Pilote réel Kings | **non validé** |
| Stress concurrentiel | **non validé** |

Le prochain dépôt Kings +20 est le **test le plus important** du chantier Bundle depuis l’incident des 4 batches.

---

## Docs liées

- [BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md](BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md) — chaîne de trades LI.FI · cash dominant · resume
- [BUNDLE_PORTFOLIO_REBALANCING_ARCHITECTURE.md](BUNDLE_PORTFOLIO_REBALANCING_ARCHITECTURE.md) — rééquilibrage (drift, plan, executor)
- [GO_BUNDLE_V3_DEPOSIT_WORKER_ECS_REPORT.md](GO_BUNDLE_V3_DEPOSIT_WORKER_ECS_REPORT.md)
- [GO_BUNDLE_V3_DEPOSIT_FLOW_PRE_PR_REPORT.md](GO_BUNDLE_V3_DEPOSIT_FLOW_PRE_PR_REPORT.md)
- [BUNDLE_V3_DEPOSIT_FLOW_PRD.md](BUNDLE_V3_DEPOSIT_FLOW_PRD.md)
