# Rapport post-deploy — Bundle B4a Child Factory (PR #58)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 (verify ECS · TD :155) |
| **PR** | [#58](https://github.com/geniusga-vancelian/vancelian-app/pull/58) · merge `8711c92d` |
| **Décision** | **Deploy neutre OK — gate B4a validé** |
| **Prérequis** | [GO_BUNDLE_B3C_POST_DEPLOY_REPORT.md](GO_BUNDLE_B3C_POST_DEPLOY_REPORT.md) ✅ · [GO_BUNDLE_B3C_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B3C_CONTROLLED_TEST_REPORT.md) ✅ |

---

## Résumé exécutif

Deploy neutre B4a validé : image prod `8711c92d`, module `bundle_child_factory` présent, **aucun runtime branché**, aucun child auto via factory, comptabilité inchangée (PE 19 · CB 67 · legs 131). **`all_checks_pass=true`**.

B4a = dernier morceau **sans blockchain** du rail Bundle event-driven. B4b = premier pont runtime (swap + settlement).

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | [run 27133421251](https://github.com/geniusga-vancelian/vancelian-app/actions/runs/27133421251) | success ✅ |
| Task definition | **TD :155** | ≥ post-#58 ✅ |
| Image SHA | `8711c92d9fde9d2d7474c4a267a2b7488ab13617` | contient merge `8711c92d` ✅ |
| Rollout ECS | **COMPLETED** | ✅ |
| Health | `https://arquantix.com/health` → **200** | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | **absent** | ✅ |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | **absent** | ✅ |
| `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED` | **absent** | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-bundle-b4a-post-deploy-verify.sh`  
**Inline** : `scripts/_bundle-b4a-post-deploy-verify-inline.py`  
**Log stream** : `/ecs/arquantix-api` · task `f180cc636d3a41c78f8c75abaeb3d425` · exit **0**

```bash
./scripts/arquantix-ecs-bundle-b4a-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | **true** | ✅ |
| Alembic | **176** | ✅ |
| Flags Bundle | tous **absents** | ✅ |
| Module factory présent | **true** | ✅ |
| Orchestrator/worker appelle factory | **false** | ✅ |
| `bundle_child_factory_metadata_auto` | **0** | ✅ |
| `bundle_parents_child_factory_metadata` | **0** | ✅ |
| `bundle_parents_child_legs_created_factory` | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| **`all_checks_pass`** | **true** | ✅ |

> Note : `bundle_leg_or_child_intents_total=1` = child B3c controlled test (`d9e30021…`) — **pas** créé par B4a factory. Critère factory : metadata `bundle_child_factory` = **0**.

### JSON ECS

```json
{
  "phase": "bundle_b4a_post_deploy_verify",
  "merge_sha": "8711c92d",
  "health": { "ok": true, "status": 200 },
  "alembic_version": "176",
  "neutralite": {
    "bundle_child_factory_metadata_auto": 0,
    "bundle_parents_child_factory_metadata": 0,
    "bundle_parents_child_legs_created_factory": 0,
    "pe_atoms": 19,
    "cost_basis": 67,
    "lifi_swap_legs": 131
  },
  "runtime_wiring": {
    "bundle_child_factory_module_present": true,
    "orchestrator_worker_or_lifi_leg_calls_factory": false
  },
  "all_checks_pass": true
}
```

---

## Neutralité B4a

| Critère | Statut |
| --- | --- |
| Factory module présent · aucun wiring runtime | ✅ |
| Aucun child auto `bundle_child_factory` metadata | ✅ |
| Aucun parent `child_factory` audit auto | ✅ |
| Aucun swap · LI.FI · settlement · worker/outbox | ✅ |
| PE / CB / legs LI.FI inchangés | ✅ |
| Pas de test WebApp | ✅ |
| Pas d'activation Bundle runtime | ✅ |

---

## Progression rail

| Gate | Statut |
| --- | --- |
| B1 parent/child | ✅ |
| B2/B2b locks | ✅ |
| B3b planner | ✅ |
| B3a funding handler | ✅ |
| B3c settlement handler + test contrôlé prod | ✅ |
| **B4a child factory** | **✅ deploy neutre** |
| B4b child runtime (swap → settle) | ⬜ prochain |

**Estimation progression** : ~**80 %** du Bundle event-driven après B4a neutre.

---

## Suite

1. **B4b minimal** — child `awaiting_swap` → fresh swap → attach → `settle_bundle_leg_idempotently` (B3c).
2. Enrichir child : `entry_instrument_id` / `target_instrument_id` avant settlement.
3. Durcir idempotence race en worker B4b.
4. Pas de WebApp · pas de Controller · pas de N legs avant B4b validé.

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) § Phase B4
- `services/portfolio_engine/bundles/event_driven/bundle_child_factory.py`
