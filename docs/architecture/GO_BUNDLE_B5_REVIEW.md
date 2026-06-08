# Review B5 — Bundle Parent Controller minimal

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Module** | `bundle_parent_controller.py` |
| **Question centrale** | Le Controller parent agrège-t-il uniquement les preuves des enfants sans modifier l'économie, sans replanifier et sans finaliser le parent ? |
| **Décision review** | **✅ GO merge** (après correctifs review · commit post-`d418bb27`) |

---

## Verdict

**Oui** — B5 est un **agrégateur de preuves metadata-only**. Aucun appel settlement · swap · PE · lock release · replan.

Correctifs appliqués pendant la review (écarts initiaux sur `d418bb27`) :

| Écart initial | Correctif |
| --- | --- |
| Flag OFF → `raise` au lieu de no-op | `skipped=True` · `reason=disabled` |
| `parent_report_hash` sans `settlement_receipt_hash[]` / `expected_leg_count` | Hash canonique enrichi |
| Pas de vérif `bundle_leg` / `planner_version` / `settlement_receipt_hash` | Validations ajoutées |
| Bloc metadata `bundle_parent_reconciliation` | Renommé `bundle_parent_controller` |
| Erreurs sans classification retryable/terminal | `BundleParentControllerError.retryable` |
| Tests incomplets | +8 cas (disabled noop · receipts · duplicate · no PE writes · imports) |
| Pas de scripts deploy / controlled test | Scripts ECS B5 livrés |

---

## Checklist review (10 points)

### 1. Flag OFF — ✅

| Check | Statut |
| --- | --- |
| `BUNDLE_PARENT_CONTROLLER_ENABLED=false` par défaut | ✅ `bundle_parent_controller_config.py` |
| No-op strict si flag OFF | ✅ `skipped=True` · aucune mutation |
| Aucune lecture/écriture économique | ✅ pas d'import PE/swap/settlement handler |

### 2. Scope parent — ✅

| Check | Statut |
| --- | --- |
| `bundle_invest` + `intent_role=parent` | ✅ `is_bundle_parent_intent` |
| Phase `CHILD_LEGS_CREATED` ou `RECONCILED` | ✅ |
| `plan_hash` · `planner_version` · `rebalance_plan_after_funding` | ✅ |
| Children via `parent_intent_id` (`find_children`) | ✅ · `child_intent_ids` non requis |

### 3. Enfants — ✅

| Check | Statut |
| --- | --- |
| N children couvrant N legs plan | ✅ |
| `product_type=bundle_leg` · `intent_role=child` | ✅ `is_bundle_child_intent` |
| Même `plan_hash` · même `planner_version` | ✅ |
| `leg_index` unique | ✅ `duplicate_child_leg` terminal |
| Tous `LEDGER_SETTLED` | ✅ |
| `settlement_receipt_hash` + `child_report_hash` | ✅ |

### 4. Report parent — ✅

`parent_report_hash` = SHA256 canonique de :

- `parent_intent_id`
- `plan_hash`
- `planner_version`
- `expected_leg_count`
- `child_proofs[]` triés par `leg_index` (`child_report_hash` + `settlement_receipt_hash`)

### 5. Écritures autorisées — ✅

**Autorisé** : `metadata_json.phase=RECONCILED` · `parent_report_hash` · `bundle_parent_controller`

**Interdit** (vérifié source + tests) : `COMPLETED` · PE · CB · wallets · settlement · swap · child mutation · lock release · replan

### 6. Idempotence — ✅

Parent déjà `RECONCILED` + même hash → `idempotent=True` · `parent_already_reconciled` · pas de `db.add` supplémentaire.

### 7. Erreurs — ✅

| Code | Retryable |
| --- | --- |
| `child_missing` | ✅ |
| `child_not_settled` | ✅ |
| `missing_child_report_hash` | ✅ |
| `missing_settlement_receipt_hash` | ✅ |
| `plan_hash_mismatch` | ❌ terminal |
| `planner_version_mismatch` | ❌ terminal |
| `duplicate_child_leg` | ❌ terminal |
| `unexpected_children` | ❌ terminal |
| `parent_completed` | ❌ terminal |

### 8. Tests — ✅

`test_bundle_b5_parent_controller.py` : happy path · idempotence · disabled noop · missing child · not settled · plan_hash mismatch · missing reports · duplicate leg · no PE writes · forbidden source tokens.

### 9. Deploy neutre — ⏸ post-merge

Script : `scripts/arquantix-ecs-bundle-b5-post-deploy-verify.sh`

Attendu : flag OFF · 0 parent auto RECONCILED · PE=19 · CB=67 · legs=131 · no runtime wiring.

### 10. Controlled test B5 — ⏸ post-deploy neutre

Script : `scripts/arquantix-ecs-bundle-b5-controlled-test.sh`  
Plan : [GO_BUNDLE_B5_MINIMAL_TEST_PLAN.md](GO_BUNDLE_B5_MINIMAL_TEST_PLAN.md)

Parent cible B4b : `0ef6517e-10c1-453b-bce7-3e6ff08c866d` (child déjà `LEDGER_SETTLED`).

---

## Séquence recommandée

1. Merge B5 (review GO)
2. Deploy neutre + `arquantix-ecs-bundle-b5-post-deploy-verify.sh`
3. Controlled test B5 (flag job only)
4. **WebApp Bundle Invest 1 USDC Base** — checklist stricte + rollback

**Ne pas** ouvrir N legs · sell · rebalance · withdraw avant WebApp réel vert.
