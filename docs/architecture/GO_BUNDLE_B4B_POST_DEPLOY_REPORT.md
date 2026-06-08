# Rapport post-deploy — Bundle B4b Minimal Runtime Bridge (PR #60)

| Champ | Valeur |
| --- | --- |
| **Date** | *(à compléter après verify ECS)* |
| **PR** | [#60](https://github.com/geniusga-vancelian/vancelian-app/pull/60) |
| **Décision** | **NON EXÉCUTÉ — en attente deploy neutre + verify ECS** |
| **Prérequis** | [GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md) ✅ · [GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md](GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md) ✅ |

---

## Résumé exécutif

Deploy neutre B4b : module `bundle_b4b_runtime_bridge` présent · **aucun runtime branché** · flags OFF · comptabilité inchangée (PE 19 · CB 67 · legs 131).

**Ne pas lancer** le controlled test B4b avant ce rapport validé (`all_checks_pass=true`).

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | *(run URL)* | success |
| Task definition | **TD :___** | ≥ post-#60 |
| Image SHA | *(SHA)* | contient merge PR #60 |
| Rollout ECS | **COMPLETED** | ✅ |
| Health | `https://arquantix.com/health` → **200** | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED` | **absent** | ✅ |
| `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` | **absent** | ✅ |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | **absent** | ✅ |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | **absent** | ✅ |
| `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED` | **absent** | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-bundle-b4b-post-deploy-verify.sh`  
**Inline** : `scripts/_bundle-b4b-post-deploy-verify-inline.py`

```bash
./scripts/arquantix-ecs-bundle-b4b-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | | **true** |
| Alembic | | **176** |
| Flags B4b / global lock / B3c | tous **absents** | ✅ |
| Module bridge présent | | **true** |
| Orchestrator/worker appelle bridge | | **false** |
| `bundle_b4b_bridge_metadata_auto` | | **0** |
| `financial_transaction_locks_active` | | **0** |
| PE atoms | | **19** |
| Cost basis | | **67** |
| Legs `lifi-swap:%` | | **131** |
| `dead_letter` | | **0** |
| `COMPLETED` | | **0** |
| **`all_checks_pass`** | | **true** |

---

## Prochaine étape

1. Go explicite **« B4b Controlled Test »** après relecture [GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md](GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md)
2. Exécuter `scripts/arquantix-ecs-bundle-b4b-minimal-test.sh`
3. Produire [GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md)

**Pas de WebApp** avant controlled test GO.
