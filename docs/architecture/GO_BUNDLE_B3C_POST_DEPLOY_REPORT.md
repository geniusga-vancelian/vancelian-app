# Rapport post-deploy — Bundle B3c Leg Settlement Handler (PR #57)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 (verify ECS 13:18 +04) |
| **PR** | [#57](https://github.com/geniusga-vancelian/vancelian-app/pull/57) · merge `660b1964` |
| **Décision** | **Deploy neutre OK — gate B3c validé** |
| **Prérequis** | Rapport [GO_BUNDLE_B3A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B3A_POST_DEPLOY_REPORT.md) **OK** ✅ |

---

## Résumé exécutif

Deploy neutre B3c validé : image prod `660b1964`, module `bundle_leg_settlement_handler` présent, flag **OFF**, aucun wiring runtime, aucun child intent touché, comptabilité inchangée (PE 19 · CB 67 · legs 131). **`all_checks_pass=true`**.

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | [run 27127279900](https://github.com/geniusga-vancelian/vancelian-app/actions/runs/27127279900) | success ✅ |
| Task definition | **TD :154** | ≥ post-#57 ✅ |
| Image SHA | `660b1964f46682fe79fa8fce26eca33a9dc996da` | contient merge `660b1964` ✅ |
| Rollout ECS | **COMPLETED** | ✅ |
| Health | `https://arquantix.com/health` → **200** | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | **absent** | ✅ absent ou false |
| `bundle_leg_settlement_handler_enabled()` | **false** (handler désactivé) | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-bundle-b3c-post-deploy-verify.sh`  
**Inline** : `scripts/_bundle-b3c-post-deploy-verify-inline.py`  
**Log stream** : `/ecs/arquantix-api` · task `cbf81ca07794428fa1fa4c6f886f8c13` · exit **0**

```bash
./scripts/arquantix-ecs-bundle-b3c-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | **true** | ✅ |
| Alembic | **176** | ✅ |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | absent | ✅ |
| Handler désactivé (`flag_off_runtime`) | **true** | ✅ |
| Module handler présent | **true** | ✅ |
| Orchestrator/worker/LifiLeg appelle handler | **false** | ✅ |
| `bundle_leg_settlement_metadata_auto` | **0** | ✅ |
| `bundle_parents_leg_settlement_metadata` | **0** | ✅ |
| `bundle_leg_or_child_intents` | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| **`all_checks_pass`** | **true** | ✅ |

### JSON ECS

```json
{
  "phase": "bundle_b3c_post_deploy_verify",
  "merge_sha": "8252e9c9",
  "deploy_git_sha": null,
  "health": {
    "url": "https://arquantix.com/health",
    "ok": true,
    "status": 200,
    "error": null
  },
  "alembic_version": "176",
  "flags": {
    "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": null,
    "bundle_leg_settlement_handler_enabled()": true
  },
  "neutralite": {
    "bundle_scope_bundle_invest_locks": 0,
    "bundle_leg_or_child_intents": 0,
    "bundle_leg_settlement_metadata_auto": 0,
    "bundle_parents_leg_settlement_metadata": 0,
    "pe_atoms": 19,
    "pe_atoms_expected": 19,
    "cost_basis": 67,
    "cost_basis_expected": 67,
    "lifi_swap_legs": 131,
    "lifi_swap_legs_expected": 131
  },
  "runtime_wiring": {
    "bundle_leg_settlement_handler_module_present": true,
    "settle_bundle_leg_callable": true,
    "module_no_worker_controller_lifi_imports": true,
    "orchestrator_worker_or_lifi_leg_calls_handler": false,
    "legacy_apply_post_confirmation_still_present": true
  },
  "all_checks_pass": true
}
```

> Note : la clé JSON `bundle_leg_settlement_handler_enabled()` encode `flag_off_runtime` (= handler **désactivé**). Valeur `true` = conforme.

---

## Neutralité B3c

| Critère | Statut |
| --- | --- |
| Handler module présent · flag OFF | ✅ |
| Aucun appel runtime `settle_bundle_leg_idempotently` | ✅ |
| Aucun child `bundle_leg` metadata settlement auto | ✅ |
| Aucun `settlement_receipt_hash` bundle leg auto | ✅ |
| Aucune mutation parent metadata | ✅ |
| PE / CB / legs LI.FI inchangés | ✅ |
| Legacy `_apply_post_confirmation` inchangé | ✅ |

---

## Décision

| Action | Statut |
| --- | --- |
| Deploy neutre B3c validé | ✅ |
| **Ne pas activer B3c en prod** | ✅ **maintenu** |
| Préparer test contrôlé 1×1×1 USDC→AAVE Base | ⬜ prochaine étape |

---

## Flags interdits (maintenus OFF)

| Flag | Statut prod |
| --- | --- |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | absent ✅ |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | absent ✅ |
| `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED` | absent ✅ |

**Aucun test runtime Bundle** lancé avant ce rapport.

---

## Suite

1. Rédiger le plan de test contrôlé **1 parent · 1 child · 1 buy leg · USDC→AAVE · Base**.
2. Activer les flags **uniquement** dans un environnement de test contrôlé, pas en prod.
3. B3c v2 / webhook credit reuse S3b : hors scope v1.

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) §4.0.5–§4.0.7
- `services/portfolio_engine/bundles/event_driven/bundle_leg_settlement_handler.py`
- Webhook credit reuse S3b : **hors scope B3c v1** (note PR #57)
