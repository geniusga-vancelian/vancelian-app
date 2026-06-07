# Rapport final exécution — Go Pilot Prod Étape 3

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-07 |
| **Compte** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **Swap pilot** | `6996ea11-aab1-4460-98fc-ea1ed4f7283c` · 1 USDC → ETH · Base |
| **PR idempotence S3b** | [#39](https://github.com/geniusga-vancelian/vancelian-app/pull/39) · `677f8d86` |
| **PR hardening CB** | [#40](https://github.com/geniusga-vancelian/vancelian-app/pull/40) · `dcef5216` |
| **Décision finale** | **ÉTAPE 3 CLOSE** — event-driven validé · réserve CB traitée par #40 |

---

## Résumé exécutif

La chaîne event-driven LI.FI standalone a été **validée en production** sur le swap existant `6996ea11-…`, sans second swap :

```
Confirm → intent.created → worker → QUEUED → auto intent.settle → S3b → LEDGER_SETTLED
→ 1 débit USDC · 0 nouveau crédit ETH · crédit webhook réutilisé
```

**Réserve initiale** : `cost_basis_executions` 66 → 67 lors du tick (ingest legacy dans `settle_lifi_swap_idempotently`, hors S3b).

**Hardening #40** : `skip_legacy_cost_basis_for_orchestrator()` — les swaps orchestrateurs actifs ne recevront plus de cost basis via maintenance/reconciliation legacy. **Pas de re-run Étape 3** requis : le swap pilot reste `LEDGER_SETTLED`.

---

## Chronologie ops

| Heure (UTC) | Action | Résultat |
| --- | --- | --- |
| 10:37 | Merge PR #39 | `677f8d86` |
| 10:37–10:44 | Deploy API | TD `:124` |
| 10:46 | Re-audit idempotence | `SAFE_WEBHOOK_CREDIT_REUSE` |
| 10:48 | Activate worker + ledger | TD `:125` |
| 10:50 | Tick ECS | `LEDGER_SETTLED` · CB 66→67 |
| 10:53 | Rollback worker + ledger | TD `:126` |
| 11:08 | Merge PR #40 | `dcef5216` |
| 11:08–11:18 | Deploy API #40 | TD **`arquantix-api:127`** |
| 11:20 | Post-deploy verify | PE=19 · CB=67 · legs=117 · flags OK |

---

## Validation event-driven (swap `6996ea11-…`)

| Critère | Statut |
| --- | --- |
| `intent.created` processed | ✅ |
| Auto-enqueue `intent.settle` | ✅ |
| `intent.settle` processed | ✅ |
| Phase **`LEDGER_SETTLED`** | ✅ |
| 1 débit USDC `lifi-swap:…:debit` | ✅ |
| 0 nouveau crédit ETH | ✅ |
| Crédit webhook réutilisé | ✅ |
| PE inchangé (19) | ✅ |
| COMPLETED = 0 | ✅ |
| Pas de double crédit | ✅ (#39) |

---

## Réserve cost basis

| Élément | Détail |
| --- | --- |
| Observation tick | CB **66 → 67** |
| Cause | `ingest_lifi_swap_settlement` dans `settle_lifi_swap_idempotently` (swap_maintenance tick, avant worker outbox) |
| S3b en cause ? | **Non** |
| Correctif | PR #40 · `skip_legacy_cost_basis_for_orchestrator()` |
| Re-run swap ? | **Non** — swap déjà `LEDGER_SETTLED` ; guard empêche récurrence sur futurs ticks |

---

## Post-deploy #40 (2026-06-07 ~11:20 UTC)

| Check | Valeur | Attendu |
| --- | --- | --- |
| Task definition | **`arquantix-api:127`** | stable |
| Image SHA | **`dcef5216`** | contient #40 |
| Deploy rollout | **COMPLETED** | ✅ |
| `LIFI_OUTBOX_WORKER_ENABLED` | **false** | ✅ |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | **false** | ✅ |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | **true** | ✅ |
| `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` | **gaelitier@gmail.com** | ✅ |
| PE atoms | **19** | ✅ |
| Cost basis | **67** | stable (drift historique tick) |
| Legs `lifi-swap:%` | **117** | ✅ |
| Intent pilot phase | **LEDGER_SETTLED** | ✅ |
| COMPLETED orchestrateur | **0** | ✅ |
| dead_letter | **0** | ✅ |

**Verrous respectés** : pas de re-tick Étape 3 · pas de second swap · pas de S4 / Controller.

---

## État prod final

| Paramètre | Valeur |
| --- | --- |
| Task definition active | **`arquantix-api:127`** |
| Image | `dcef52167035a2fe801fc19af466f62d6137dd79` |
| Worker / ledger | **OFF** |
| Orchestrator + allowlist | **ON** · `gaelitier@gmail.com` |

---

## Décision finale

**Étape 3 : CLOSE**

- Rail event-driven LI.FI standalone **validé** en prod (cas réel webhook + S3b).
- Réserve CB **identifiée, corrigée (#40), documentée** — pas de re-validation swap nécessaire.
- Prochaine phase (S4 / Controller / COMPLETED) : **hors scope** de ce pilot.

---

## Références

| Doc / PR | Rôle |
| --- | --- |
| [GO_PILOT_PROD_STEP3_S3B_IDEMPOTENCE_INCIDENT.md](GO_PILOT_PROD_STEP3_S3B_IDEMPOTENCE_INCIDENT.md) | Pre-patch double crédit |
| [GO_PILOT_PROD_STEP3_POST_SWAP_AUDIT.md](GO_PILOT_PROD_STEP3_POST_SWAP_AUDIT.md) | Audit pre-tick |
| PR #39 | Idempotence crédit webhook S3b |
| PR #40 | Skip legacy cost basis orchestrateur |
| `scripts/_pilot-step3-baseline-inline.py` | Vérif post-deploy |
