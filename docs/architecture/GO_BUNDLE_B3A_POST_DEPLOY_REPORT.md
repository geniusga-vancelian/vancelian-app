# Rapport post-deploy — Bundle B3a Funding Handler (PR #56)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 (verify ECS 12:45 +04) |
| **PR** | [#56](https://github.com/geniusga-vancelian/vancelian-app/pull/56) · merge `5822be6e` |
| **Décision** | **Deploy neutre OK — GO merge #57** |
| **Gate suivant** | Merge #57 · deploy neutre B3c · verify B3c |

---

## Résumé exécutif

Deploy neutre B3a validé : image prod `5822be6e`, module `bundle_funding_handler` présent, flag **OFF**, aucun wiring runtime, comptabilité inchangée (PE 19 · CB 67 · legs 131). **`all_checks_pass=true`**.

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | [run 27124436753](https://github.com/geniusga-vancelian/vancelian-app/actions/runs/27124436753) | success ✅ |
| Task definition | **TD :153** | ≥ post-#56 ✅ |
| Image SHA | `5822be6e0a6d0a787384eca915f231ac5a3704db` | contient merge `5822be6e` ✅ |
| Rollout ECS | **COMPLETED** (steady state 12:13 +04) | ✅ |
| Health | `https://arquantix.com/health` → **200** | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | **absent** | ✅ absent ou false |
| `bundle_funding_handler_enabled()` | **false** (handler désactivé) | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-bundle-b3a-post-deploy-verify.sh`  
**Inline** : `scripts/_bundle-b3a-post-deploy-verify-inline.py`  
**Log stream** : `/ecs/arquantix-api` · task `b5d8627bbe324225b8c7b985fec2c8a8` · exit **0**

```bash
./scripts/arquantix-ecs-bundle-b3a-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | **true** | ✅ |
| Alembic | **176** | ✅ |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | absent | ✅ |
| Handler désactivé (`flag_off_runtime`) | **true** | ✅ |
| Module handler présent | **true** | ✅ |
| Orchestrator/worker appelle handler | **false** | ✅ |
| `bundle_funding_receipt_or_settled_parents` | **0** | ✅ |
| `bundle_leg_or_child_intents` | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| **`all_checks_pass`** | **true** | ✅ |

### JSON ECS

```json
{
  "phase": "bundle_b3a_post_deploy_verify",
  "merge_sha": "5822be6e",
  "deploy_git_sha": null,
  "health": {
    "url": "https://arquantix.com/health",
    "ok": true,
    "status": 200,
    "error": null
  },
  "alembic_version": "176",
  "flags": {
    "BUNDLE_FUNDING_HANDLER_ENABLED": null,
    "bundle_funding_handler_enabled()": true
  },
  "neutralite": {
    "bundle_scope_bundle_invest_locks": 0,
    "bundle_leg_or_child_intents": 0,
    "bundle_funding_receipt_or_settled_parents": 0,
    "pe_atoms": 19,
    "pe_atoms_expected": 19,
    "cost_basis": 67,
    "cost_basis_expected": 67,
    "lifi_swap_legs": 131,
    "lifi_swap_legs_expected": 131
  },
  "runtime_wiring": {
    "bundle_funding_handler_module_present": true,
    "settle_bundle_funding_callable": true,
    "module_no_worker_controller_lifi_imports": true,
    "orchestrator_or_worker_calls_funding_handler": false
  },
  "all_checks_pass": true
}
```

> Note : la clé JSON `bundle_funding_handler_enabled()` encode en fait `flag_off_runtime` (= handler **désactivé**). Valeur `true` = conforme.

---

## Neutralité B3a

| Critère | Statut |
| --- | --- |
| Handler module présent · flag OFF | ✅ |
| Aucun appel runtime `settle_bundle_funding_idempotently` | ✅ |
| Aucun `bundle_funding_receipt_hash` auto | ✅ |
| Aucun `bundle_funding.settled=true` auto | ✅ |
| PE / CB / legs LI.FI inchangés | ✅ |
| Legacy `fund_bundle_cash_leg_from_self_trading` inchangé | ✅ (orchestrator non câblé) |

---

## Décision

| Action | Statut |
| --- | --- |
| Deploy neutre B3a validé | ✅ |
| **GO merge PR #57** | ✅ **autorisé** |

---

## Suite (hors scope immédiat)

1. Merger [#57](https://github.com/geniusga-vancelian/vancelian-app/pull/57) (B3c leg settlement handler).
2. Deploy neutre B3c (`BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` absent/false).
3. `./scripts/arquantix-ecs-bundle-b3c-post-deploy-verify.sh` → `GO_BUNDLE_B3C_POST_DEPLOY_REPORT.md`.
4. **Ne pas activer** `BUNDLE_FUNDING_HANDLER_ENABLED`, `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED`, `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED`.
5. **Aucun test runtime Bundle** avant rapport B3c neutre.

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) §4.0 · B3a
- `services/portfolio_engine/bundles/event_driven/bundle_funding_handler.py`
