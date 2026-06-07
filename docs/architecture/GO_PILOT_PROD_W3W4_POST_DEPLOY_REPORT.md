# Rapport post-deploy — W3/W4 auto-enqueue `intent.settle`

| Champ | Valeur |
| --- | --- |
| **PR** | [#38](https://github.com/geniusga-vancelian/vancelian-app/pull/38) — mergée |
| **Merge commit** | **`a13de0be331972ae083025db3722707e36761f0e`** |
| **Migration** | **174** — `uq_outbox_intent_event_type` UNIQUE `(intent_id, event_type)` |
| **Feu vert merge** | CTO — 2026-06-07 |
| **Opérateur deploy** | Cursor (agent) + GHA `arquantix-api-deploy.yml` |
| **Date deploy** | 2026-06-07 |
| **Décision** | **Post-deploy OK** |

---

## Objectif

Déployer W3/W4 en prod **sans** activer worker/ledger ni lancer Étape 3.

Pipeline désormais **live** (dormant : worker OFF, ledger OFF) :

```
CONFIRMED + tx_hash → auto enqueue intent.settle → (worker) → settlement → ledger
```

---

## Interdictions respectées

| Action | Statut |
| --- | --- |
| `LIFI_OUTBOX_WORKER_ENABLED=true` | ❌ Non (`false`) |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=true` | ❌ Non (`false`) |
| Swap signé / submit on-chain | ❌ Non |
| Étape 3 | ❌ Non |
| Controller | ❌ Non |
| Élargissement allowlist | ❌ Non |
| Suppression artefacts pilot | ❌ Non |

---

## 1. Deploy ECS prod (us-east-1)

| Champ | Valeur |
| --- | --- |
| Workflow GHA | `27088171488` — **success** |
| Cluster | `arquantix-cluster` |
| Service | `arquantix-api` |
| Task definition **avant** | `arquantix-api:119` (post-Étape 2 rollback) |
| Task definition **après** | **`arquantix-api:120`** |
| Rollout | `COMPLETED` · running **1/1** |
| Image | `411714852748.dkr.ecr.us-east-1.amazonaws.com/arquantix-api:a13de0be331972ae083025db3722707e36761f0e` |

---

## 2. Flags runtime (TD `:120`)

| Variable | Valeur prod | Attendu | OK |
| --- | --- | --- | --- |
| `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` | `gaelitier@gmail.com` | idem | ✅ |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `true` | `true` | ✅ |
| `LIFI_OUTBOX_WORKER_ENABLED` | `false` | `false` | ✅ |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | `false` | `false` | ✅ |

Source : `aws ecs describe-task-definition --task-definition arquantix-api:120`

---

## 3. Migration 174 + index unique (DB prod)

ECS one-shot (TD `:120`) — script `_w3w4-post-deploy-verify-inline.py` · task `9d26faa597fe48d49e65053b5f097bd1` · exit **0**

| Check | Résultat |
| --- | --- |
| `alembic_version` | **`174`** |
| Migration ≥ 174 | ✅ |
| Index `uq_outbox_intent_event_type` | ✅ présent |
| Définition index | `CREATE UNIQUE INDEX uq_outbox_intent_event_type ON public.transaction_outbox USING btree (intent_id, event_type)` |
| Colonne `status` dans l'index | ❌ absente (correct) |

---

## 4. Baseline outbox (prod)

| Métrique | Valeur | Attendu | OK |
| --- | --- | --- | --- |
| Outbox `pending` (tous types) | **0** | 0 | ✅ |
| Outbox `intent.settle` (total) | **0** | 0 | ✅ |
| Outbox `intent.settle` pending | **0** | 0 | ✅ |
| Outbox `dead_letter` | **0** | 0 | ✅ |

Compte pilot : `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492`

| Métrique | Valeur |
| --- | --- |
| Intents orchestrateur Phase 2 (pilot) | **8** |
| Autres users orchestrateur | **0** |

---

## 5. Baseline économique (prod)

| Métrique | Valeur | Attendu | OK |
| --- | --- | --- | --- |
| PE atoms | **19** | 19 | ✅ |
| Cost basis executions | **66** | 66 | ✅ |
| `person_wallet_deposits` `lifi-swap:%` | **116** | 116 | ✅ |
| `economic_baseline_match` | **true** | true | ✅ |

Aucune dérive économique détectée au deploy W3/W4.

---

## 6. Smoke

| Check | Résultat |
| --- | --- |
| Service ECS stable | ✅ `:120` PRIMARY COMPLETED |
| Image SHA ≥ `a13de0be` | ✅ tag exact merge commit |
| Job vérification DB | ✅ exit 0 |
| ALB health (logs service) | ✅ `GET /` 200 OK |

---

## 7. Décision

| Critère | OK |
| --- | --- |
| Image ≥ `a13de0be` | ✅ |
| Migration 174 appliquée | ✅ |
| Index unique `(intent_id, event_type)` | ✅ |
| Flags worker/ledger OFF | ✅ |
| Baseline outbox | ✅ |
| Baseline économique | ✅ |
| Aucun autre user orchestrateur | ✅ |

**Décision : post-deploy OK.**

W3/W4 est **déployé et vérifié** en prod. Le code auto-enqueue est live ; il ne s'exercera end-to-end que lorsque worker + ledger seront activés (Étape 3).

**Go Pilot Prod Étape 3** : décision **séparée**, feu vert explicite requis — voir [GO_PILOT_PROD_STEP3_EXECUTION_PLAN.md](GO_PILOT_PROD_STEP3_EXECUTION_PLAN.md).

---

## 8. Preuve JSON (extrait CloudWatch `/ecs/arquantix-api`)

```json
{
  "alembic_version": "174",
  "migration_174_ok": true,
  "unique_index": {
    "present": true,
    "indexname": "uq_outbox_intent_event_type",
    "indexdef": "CREATE UNIQUE INDEX uq_outbox_intent_event_type ON public.transaction_outbox USING btree (intent_id, event_type)"
  },
  "outbox": {
    "pending_total": 0,
    "intent_settle_total": 0,
    "intent_settle_pending": 0,
    "dead_letter": 0
  },
  "economic": { "pe": 19, "cb": 66, "legs": 116 },
  "economic_baseline_match": true,
  "orchestrator_intents_pilot": 8,
  "other_users_orchestrator": 0
}
```

---

## Références

| Doc | Rôle |
| --- | --- |
| [PHASE2_POC_LIFI_STANDALONE_SWAP.md](PHASE2_POC_LIFI_STANDALONE_SWAP.md) | Spec W3/W4 |
| [GO_PILOT_PROD_STEP3_EXECUTION_PLAN.md](GO_PILOT_PROD_STEP3_EXECUTION_PLAN.md) | Étape 3 (prochain feu vert) |
| [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) | Runbook pilot |
| `scripts/arquantix-ecs-w3w4-post-deploy-verify.sh` | Re-vérification ops |
