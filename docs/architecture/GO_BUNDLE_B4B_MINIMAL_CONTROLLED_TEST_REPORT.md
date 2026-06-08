# Rapport GO — Test contrôlé Bundle B4b minimal (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | **NON EXÉCUTÉ** |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **PR / merge** | [#60](https://github.com/geniusga-vancelian/vancelian-app/pull/60) |
| **Task definition** | *(TD post-deploy neutre)* |
| **Plan** | [GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md](GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md) |
| **Prérequis** | [GO_BUNDLE_B4B_POST_DEPLOY_REPORT.md](GO_BUNDLE_B4B_POST_DEPLOY_REPORT.md) ✅ · Go explicite **« B4b Controlled Test »** |
| **Décision** | **⏸ En attente** |

---

## 1. Décision

*(À compléter après exécution)*

Rail minimal attendu :

```text
Parent REBALANCE_PLAN_FROZEN
  → run_bundle_b4b_minimal_bridge(parent_intent_id)  [flags ON job only]
  → Child auto (B4a)
  → Global lock acquis/released
  → Fresh swap LI.FI USDC→AAVE Base · bundle_execution=true
  → Attach · status swap_attached
  → settle B3c si CONFIRMED
  → Child LEDGER_SETTLED
```

---

## 2. Identifiants

| Champ | Valeur |
| --- | --- |
| `test_run_id` | |
| `parent_intent_id` | |
| `child_intent_id` | |
| `swap_id` | |
| `portfolio_id` | |
| `plan_hash` | |
| `settlement_receipt_hash` | |
| `child_report_hash` | |
| `tx_hash` (swap) | |
| `amount_usdc` | |

---

## 3. Étapes exécutées

Script : `scripts/arquantix-ecs-bundle-b4b-minimal-test.sh`

| # | Mode | ECS task | Résultat |
| --- | --- | --- | --- |
| 0 | `baseline` | | |
| 1 | `create_frozen_parent` | | Parent FROZEN · **0 child** |
| 2 | `run_b4b_bridge` | | Child + fresh swap + attach |
| 3 | `run_b4b_bridge` *(repeat si async)* | | CONFIRMED → LEDGER_SETTLED |
| 4 | `audit` | | `all_checks_pass` |
| 5 | `run_b4b_bridge` *(REPEAT)* | | Idempotence |

Flags activés **uniquement** dans le process ECS des jobs `run_b4b_bridge` — TD ECS reste flag **OFF**.

---

## 4. Critères GO

- [ ] Fresh swap créé par le bridge (pas d'attach manuel)
- [ ] `bundle_leg_context` : `plan_hash` · `planner_version` · `parent/child` · `leg_index`
- [ ] Child `status=swap_attached` puis `LEDGER_SETTLED`
- [ ] Global lock acquis puis **0** actif post-succès
- [ ] PE/CB/legs deltas cohérents
- [ ] `dead_letter=0` · `COMPLETED=0`
- [ ] 2ᵉ run = no-op économique
- [ ] Parent pas RECONCILED/COMPLETED

---

## 5. Rollback

Si lock orphelin : `rollback_or_cleanup` ou release manuel `intent_id=parent_intent_id`.

Ne pas activer flags en TD.
