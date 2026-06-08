# Rapport post-deploy — Global User Transaction Lock V1 (PR #59)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 (verify ECS · TD :156) |
| **PR** | [#59](https://github.com/geniusga-vancelian/vancelian-app/pull/59) · merge `9087eb41` |
| **Décision** | **Deploy neutre OK — gate Global Lock V1 validé** |
| **Prérequis** | [GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md) ✅ |

---

## Résumé exécutif

Deploy neutre validé : module `global_user_transaction_lock` présent, message 409 user-safe, flag **OFF**, aucun wiring runtime, 0 lock `financial_transaction` actif, comptabilité inchangée (PE 19 · CB 67 · legs 131). **`all_checks_pass=true`**.

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | [run 27135981953](https://github.com/geniusga-vancelian/vancelian-app/actions/runs/27135981953) | success ✅ |
| Task definition | **TD :156** | ≥ post-#59 ✅ |
| Image SHA | `9087eb41` | contient merge global lock ✅ |
| Rollout ECS | **COMPLETED** | ✅ |
| Health | `https://arquantix.com/health` → **200** | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` | **absent** | ✅ |
| `global_user_transaction_lock_enabled()` | **false** | ✅ |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | absent | ✅ |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | absent | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-global-lock-post-deploy-verify.sh`  
**Inline** : `scripts/_global-lock-post-deploy-verify-inline.py`  
**Log stream** : `/ecs/arquantix-api` · task `f8c296901d3747029a868a6adb42367c` · exit **0**

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | **true** | ✅ |
| Alembic | **176** | ✅ |
| Flag global lock | absent / false | ✅ |
| `active_financial_transaction_locks` | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| Message user-safe 409 | **true** | ✅ |
| Orchestrator/worker wiring | **false** | ✅ |
| **`all_checks_pass`** | **true** | ✅ |

### Message 409 (user-safe)

```
A transaction is already in progress. Please wait until it is completed.
```

Détails techniques (`existing_intent_id`, `lock_key`, `reasons`) : champs internes uniquement — pas dans le message public.

---

## Test contrôlé lock

**✅ GO** — [GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md](GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md)  
`test_run_id=2c1c0a513603427a9c72335d031b3857` · `all_checks_pass=true`

---

## Gate suivant

**B4b minimal** — child `awaiting_swap` → global lock → fresh swap → attach → settlement B3c.

---

## Références

- [S4_PRODUCT_LOCKS_MATRIX.md](S4_PRODUCT_LOCKS_MATRIX.md) §4.6
- `services/product_locks/global_user_transaction_lock.py`
