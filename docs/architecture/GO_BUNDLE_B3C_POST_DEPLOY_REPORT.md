# Rapport post-deploy — Bundle B3c Leg Settlement Handler (PR #57)

| Champ | Valeur |
| --- | --- |
| **Date** | _À compléter après exécution ECS_ |
| **PR** | [#57](https://github.com/geniusga-vancelian/vancelian-app/pull/57) · merge _SHA à compléter_ |
| **Décision** | _À compléter : Deploy neutre OK / KO_ |
| **Prérequis** | Rapport [GO_BUNDLE_B3A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B3A_POST_DEPLOY_REPORT.md) **OK** |

---

## Résumé exécutif

Deploy neutre B3c : module `bundle_leg_settlement_handler` présent en image, flag **OFF**, aucun wiring runtime, aucun child intent touché automatiquement.

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | _lien run_ | success |
| Task definition | _TD :___ | ≥ post-#57 |
| Image SHA | _SHA deploy_ | contient merge B3c |
| Rollout ECS | _COMPLETED / …_ | ✅ |
| Health | `https://arquantix.com/health` → _200_ | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | _absent / false_ | ✅ absent ou false |
| `bundle_leg_settlement_handler_enabled()` | _false_ | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-bundle-b3c-post-deploy-verify.sh`  
**Inline** : `scripts/_bundle-b3c-post-deploy-verify-inline.py`  
**Log stream** : _/ecs/arquantix-api · task id_

```bash
./scripts/arquantix-ecs-bundle-b3c-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | _true_ | ✅ |
| Alembic | **176** | ✅ |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | absent/false | ✅ |
| `bundle_leg_settlement_handler_enabled()` | **false** | ✅ |
| Module handler présent | **true** | ✅ |
| Orchestrator/worker/LifiLeg appelle handler | **false** | ✅ |
| `bundle_leg_settlement_metadata_auto` | **0** | ✅ |
| `bundle_parents_leg_settlement_metadata` | **0** | ✅ |
| `bundle_leg_or_child_intents` | **0** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | ✅ |
| Legs `lifi-swap:%` | **131** | ✅ |
| **`all_checks_pass`** | _true_ | ✅ |

### JSON ECS (coller ici)

```json
{
  "_paste_ecs_output": true
}
```

---

## Neutralité B3c

| Critère | Statut |
| --- | --- |
| Handler module présent · flag OFF | _⬜_ |
| Aucun appel runtime `settle_bundle_leg_idempotently` | _⬜_ |
| Aucun child `bundle_leg` metadata settlement auto | _⬜_ |
| Aucun `settlement_receipt_hash` bundle leg auto | _⬜_ |
| Aucune mutation parent metadata | _⬜_ |
| PE / CB / legs LI.FI inchangés | _⬜_ |
| Legacy `_apply_post_confirmation` inchangé | _⬜_ |

---

## Décision

| Action | Statut |
| --- | --- |
| Deploy neutre B3c validé | _⬜_ |
| **Ne pas activer B3c en prod** | _⬜_ |
| Préparer test contrôlé 1×1×1 USDC→AAVE Base | _⬜_ |

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) §4.0.5–§4.0.7
- `services/portfolio_engine/bundles/event_driven/bundle_leg_settlement_handler.py`
- Webhook credit reuse S3b : **hors scope B3c v1** (note PR #57)
