# Rapport d’exécution — Checklist staging LI.FI Orchestrator (Phase 2)

| Champ | Valeur |
| --- | --- |
| **Checklist** | [STAGING_ACTIVATION_CHECKLIST_LIFI_ORCHESTRATOR.md](STAGING_ACTIVATION_CHECKLIST_LIFI_ORCHESTRATOR.md) |
| **Feu vert** | Go checklist staging (pas Go S3 controller) |
| **Opérateur** | Cursor (agent) |
| **Date / heure** | 2026-06-07 (audit + gates automatisés) |
| **Commit cible checklist** | `5571955cc65a8ff80c822942cc154e1cc33d7aa5` (`main`) |
| **Décision** | **Checklist staging KO** — blocage environnement (voir § Décision) |
| **Suite** | [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) — pilot prod allowlist (pas staging fictif) |

---

## A. Diagnostic

| Zone | État constaté |
| --- | --- |
| Gates automatisés (pytest) | ✅ **30/30 passed** sur `5571955c` (machine locale, `services/arquantix/api/.venv-r2`) |
| Env staging Arquantix dédié | ❌ **Absent** — pas de cluster/service ECS Arquantix staging dans les workflows |
| `vancelian-staging-api` (me-central-1) | ⚠️ Service distinct, image `d56003e8` (déc. 2025), **~523 commits** derrière `main`, **sans code S3b** |
| `arquantix-cluster` (us-east-1) | ⚠️ **Production** Arquantix — image `004568c8` (S3b présent), flags orchestrateur **absents = OFF** ; **hors périmètre** checklist (interdit prod) |
| Stack locale `arquantixrecovery` | Baseline flags orchestrateur **OFF** (vars absentes) ; `LIFI_SWAPS_MOCK=1` — **non conforme** campagne staging réel (checklist § Flags hors périmètre) |
| Production flags ON | ✅ **Aucune activation** — pas de `LIFI_INTENT_ORCHESTRATOR_ENABLED` / `LIFI_OUTBOX_WORKER_ENABLED` / `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` sur ECS prod |
| Controller / COMPLETED | ✅ **Non démarré** |

---

## B. Cause probable du blocage

La checklist exige un **staging dédié** avec le commit S3b déployé, activation séquentielle des flags, et **10 swaps LI.FI réels** (`LIFI_SWAPS_MOCK=0`).

L’infra documentée ne fournit pas aujourd’hui cet environnement pour l’API Arquantix Phase 2 :

1. **`arquantix-api-deploy.yml`** pousse `main` vers **`arquantix-cluster` (prod)**, pas vers un staging Arquantix.
2. **`deploy-staging.yml`** cible **`vancelian-staging-api`** (autre codebase / image racine), pas `services/arquantix/api`.
3. L’image ECR `arquantix-api:5571955c` **n’existe pas** (commit doc-only post-S3b) ; la dernière image S3b en prod est `004568c8`.

Sans env staging Arquantix isolé, les étapes 1–3, la campagne 10 swaps et le rollback **ne peuvent pas être exécutés** en respectant l’interdiction prod.

---

## C. Résultats exécutés (périmètre réalisé)

### Smoke tests (§5 checklist)

Exécutés depuis `services/arquantix/api` sur commit `5571955c` :

```text
30 passed in 3.17s
```

| Fichier | Résultat |
| --- | --- |
| `tests/test_settlement_lifi_s3b.py` | ✅ |
| `tests/test_transaction_outbox_settlement_s3a.py` | ✅ |
| `tests/test_settlement_contract_s2_5.py` | ✅ |
| `tests/test_transaction_outbox_worker_s2b.py` | ✅ |
| `tests/test_lifi_orchestrator_quote_s2a.py` | ✅ |

### Étape 0 — Baseline flags OFF (lecture seule)

| Environnement | `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `LIFI_OUTBOX_WORKER_ENABLED` | `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` |
| --- | --- | --- | --- |
| ECS `arquantix-api` (prod, audit only) | absent → `false` | absent → `false` | absent → `false` |
| Docker local `arquantixrecovery-arquantix-api-1` | absent → `false` | absent → `false` | absent → `false` |

Smoke tests OFF : couverts par `test_s3b_flag_off_legacy_apply_swap_unchanged` + suite ci-dessus.

### Étapes 1–3 — Activation séquentielle

| Étape | Flags | Statut |
| --- | --- | --- |
| 0 | `false` / `false` / `false` | ✅ Vérifié (lecture seule) |
| 1 | `true` / `false` / `false` | ❌ Non exécuté (pas d’env staging cible) |
| 2 | `true` / `true` / `false` | ❌ Non exécuté |
| 3 | `true` / `true` / `true` | ❌ Non exécuté |

### Campagne 10 swaps manuels

| # | Quote | Intent | `intent.created` | CONFIRMED | `intent.settle` | 1D+1C | `LEDGER_SETTLED` | 2ᵉ NOOP | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1–10 | — | — | — | — | — | — | — | — | **Non exécuté** — env staging Arquantix requis |

### SQL checks (baseline locale `arquantix_fresh`, lecture seule)

| Requête | Résultat |
| --- | --- |
| Outbox `GROUP BY event_type, status` | 0 ligne (table vide ou aucun événement) |
| `pe_position_atoms` COUNT | 8 |
| `cost_basis_executions` COUNT | 7 |
| `person_wallet_deposits` `lifi-swap:%:debit` | 5 (données historiques locales — pas campagne checklist) |

Requêtes par `intent_id` / `swap_id` : **N/A** (aucun swap campagne).

### Incidents STOP

Aucun — campagne non démarrée.

### Rollback flags OFF

| Critère | Statut |
| --- | --- |
| 3 flags → `false` + restart API | ❌ Non testé (flags jamais activés sur staging) |
| 1 swap legacy end-to-end post-rollback | ❌ Non testé |
| Outbox pending sans effet | ❌ Non testé |

---

## D. Risques si contournement

| Action interdite / risquée | Risque |
| --- | --- |
| Activer flags sur **ECS prod** (`arquantix-cluster`) | Écriture ledger réelle sur prod sans dual-run S5 |
| Utiliser **local** avec `LIFI_SWAPS_MOCK=1` | Faux positif — ne valide pas LI.FI réel |
| Utiliser **vancelian-staging** sans merge S3b | Code Phase 2 absent — résultats non significatifs |
| Modifier `.env.arquantix` / Compose sans accord explicite | Violation charte environnement locale |

---

## Plan minimal pour débloquer (hors scope exécuté)

**Prérequis ops** (feu vert séparé recommandé) :

1. **Provisionner ou désigner** un env staging Arquantix dédié (ECS service + RDS isolé, ou runbook local staging avec `LIFI_SWAPS_MOCK=0` et validation explicite `.env.arquantix`).
2. **Déployer** image `arquantix-api` ≥ `004568c8` (S3b) sur cet env — **pas** sur prod flags ON.
3. **Exécuter** checklist § Étapes 0→3 séquentiellement ; documenter opérateur + horodatage par étape.
4. **Campagne 10 swaps** standalone Base (USDC→ETH ou équivalent) ; remplir tableau § Campagne.
5. **Rollback** : flags OFF → restart → 1 swap legacy → SQL outbox pending.
6. **Mettre à jour** ce rapport → décision OK / OK avec réserves / KO.

**Non démarré** (verrouillé) : S4 Product Locks, S5 dual-run, S3 Controller, flags prod ON.

---

## Décision

| Verdict | Justification |
| --- | --- |
| **Checklist staging KO** | Gates automatisés ✅ ; **étapes opérationnelles staging (flags séquentiels, 10 swaps, rollback) non réalisables** faute d’environnement staging Arquantix dédié avec S3b déployé. Prod et controller **non touchés** ✅. |

### Sign-off partiel

| Rôle | Nom | Date | Étape |
| --- | --- | --- | --- |
| Dev / Cursor | Cursor | 2026-06-07 | Smoke tests 30/30 ✅ |
| Ops staging | — | — | Étapes 0–3 + campagne + rollback ❌ en attente env |
| CTO | — | — | Go S5 — **non applicable** |

---

## Références audit infra (lecture seule)

```text
ECS arquantix prod:  arquantix-cluster / arquantix-api
  image: arquantix-api:004568c8be0294c8917900cd996c0e9780528eab
  LIFI orchestrateur flags: (non définis → OFF)

ECS vancelian staging: vancelian-staging-api-cluster / vancelian-staging-api-svc
  image: vancelian-api:d56003e8d2ca900b94d626523e9bb7d58f24eee8
  LIFI orchestrateur flags: (non définis)
```
