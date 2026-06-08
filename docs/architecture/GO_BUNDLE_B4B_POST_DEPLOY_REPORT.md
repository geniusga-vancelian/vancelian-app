# Rapport post-deploy — Bundle B4b Minimal Runtime Bridge (PR #60)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 (verify ECS · TD :157) |
| **PR** | [#60](https://github.com/geniusga-vancelian/vancelian-app/pull/60) · merge `55889379` |
| **Décision** | **Deploy neutre OK — gate B4b validé** |
| **Prérequis** | [GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md) ✅ · [GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md](GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md) ✅ |

---

## Résumé exécutif

Deploy neutre B4b validé : image prod `55889379`, module `bundle_b4b_runtime_bridge` présent, **aucun runtime branché**, flags OFF, comptabilité inchangée (PE 19 · CB 67 · legs 131). **`all_checks_pass=true`**.

Controlled test B4b : **en attente** Go explicite « B4b Controlled Test » — **pas de WebApp**.

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | [run 27145245464](https://github.com/geniusga-vancelian/vancelian-app/actions/runs/27145245464) | success ✅ |
| Task definition | **TD :157** | ≥ post-#60 ✅ |
| Image SHA | `55889379c12d0e6b0ed89159a89f3d83ffe5a853` | contient merge PR #60 ✅ |
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
**Log stream** : `/ecs/arquantix-api` · task `02275b65df924058ba61a5db13d1e1b7` · exit **0**

```bash
./scripts/arquantix-ecs-bundle-b4b-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | **true** | ✅ |
| Alembic | **176** | ✅ |
| Flags B4b / global lock / B3c | tous **absents** | ✅ |
| Module bridge présent | **true** | ✅ |
| Orchestrator/worker appelle bridge | **false** | ✅ |
| `bundle_b4b_bridge_metadata_auto` | **0** | ✅ |
| `bundle_b4b_linked_swaps_auto` | **0** | ✅ |
| `financial_transaction_locks_active` | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| `dead_letter` | **0** | ✅ |
| `COMPLETED` | **0** | ✅ |
| **`all_checks_pass`** | **true** | ✅ |

### JSON ECS

```json
{
  "phase": "bundle_b4b_post_deploy_verify",
  "health": { "ok": true, "status": 200 },
  "alembic_version": "176",
  "neutralite": {
    "financial_transaction_locks_active": 0,
    "bundle_b4b_bridge_metadata_auto": 0,
    "pe_atoms": 19,
    "cost_basis": 67,
    "lifi_swap_legs": 131,
    "dead_letter": 0,
    "completed": 0
  },
  "runtime_wiring": {
    "bundle_b4b_module_present": true,
    "orchestrator_worker_calls_bridge": false
  },
  "all_checks_pass": true
}
```

---

## Follow-ups review (inclus merge `2ccc727f`)

| # | Écart | Statut |
| --- | --- | --- |
| 1 | `metadata.status = swap_attached` après attach | ✅ |
| 2 | `bundle_leg_context` enrichi (`plan_hash`, `planner_version`, `leg_index`, parent/child) | ✅ |
| 3 | Scripts ECS B4b + rapports | ✅ |

---

## Prochaine étape

1. Go explicite **« B4b Controlled Test »** ([GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md](GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md))
2. `./scripts/arquantix-ecs-bundle-b4b-minimal-test.sh baseline` puis rail complet
3. Rapport [GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md)

**Pas de WebApp** avant controlled test GO.
