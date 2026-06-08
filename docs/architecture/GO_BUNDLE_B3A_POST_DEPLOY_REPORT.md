# Rapport post-deploy — Bundle B3a Funding Handler (PR #56)

| Champ | Valeur |
| --- | --- |
| **Date** | _À compléter après exécution ECS_ |
| **PR** | [#56](https://github.com/geniusga-vancelian/vancelian-app/pull/56) · merge `5822be6e` |
| **Décision** | _À compléter : Deploy neutre OK / KO_ |
| **Gate suivant** | Merge #57 bloqué tant que ce rapport n’est pas **OK** |

---

## Résumé exécutif

Deploy neutre B3a : module `bundle_funding_handler` présent en image, flag **OFF**, aucun wiring runtime, comptabilité inchangée.

---

## Déploiement

| Élément | Valeur | Attendu |
| --- | --- | --- |
| Workflow CI | _lien run_ | success |
| Task definition | _TD :___ | ≥ post-#56 |
| Image SHA | _SHA deploy_ | contient merge `5822be6e` |
| Rollout ECS | _COMPLETED / …_ | ✅ |
| Health | `https://arquantix.com/health` → _200_ | ✅ |

---

## Flags runtime (ECS task definition)

| Flag | Valeur | Attendu |
| --- | --- | --- |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | _absent / false_ | ✅ absent ou false |
| `bundle_funding_handler_enabled()` | _false_ | ✅ |

---

## Vérifications prod (ECS one-shot)

**Script** : `scripts/arquantix-ecs-bundle-b3a-post-deploy-verify.sh`  
**Inline** : `scripts/_bundle-b3a-post-deploy-verify-inline.py`  
**Log stream** : _/ecs/arquantix-api · task id_

```bash
./scripts/arquantix-ecs-bundle-b3a-post-deploy-verify.sh
```

| Check | Valeur | Attendu |
| --- | --- | --- |
| `health.ok` | _true_ | ✅ |
| Alembic | **176** | ✅ |
| `BUNDLE_FUNDING_HANDLER_ENABLED` | absent/false | ✅ |
| `bundle_funding_handler_enabled()` | **false** | ✅ |
| Module handler présent | **true** | ✅ |
| Orchestrator/worker appelle handler | **false** | ✅ |
| `bundle_funding_receipt_or_settled_parents` | **0** | ✅ |
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

## Neutralité B3a

| Critère | Statut |
| --- | --- |
| Handler module présent · flag OFF | _⬜_ |
| Aucun appel runtime `settle_bundle_funding_idempotently` | _⬜_ |
| Aucun `bundle_funding_receipt_hash` auto | _⬜_ |
| Aucun `bundle_funding.settled=true` auto | _⬜_ |
| PE / CB / legs LI.FI inchangés | _⬜_ |
| Legacy `fund_bundle_cash_leg_from_self_trading` inchangé | _⬜_ |

---

## Décision

| Action | Statut |
| --- | --- |
| Deploy neutre B3a validé | _⬜_ |
| **GO merge PR #57** | _⬜ après B3a OK_ |

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) §4.0 · B3a
- `services/portfolio_engine/bundles/event_driven/bundle_funding_handler.py`
