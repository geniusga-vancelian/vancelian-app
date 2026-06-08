# Rapport GO — Test contrôlé Bundle B3c (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **PR / merge** | [#57](https://github.com/geniusga-vancelian/vancelian-app/pull/57) · `660b1964` |
| **Task definition** | **`arquantix-api:154`** |
| **Plan** | [GO_BUNDLE_B3C_CONTROLLED_TEST_PLAN.md](GO_BUNDLE_B3C_CONTROLLED_TEST_PLAN.md) |
| **Prérequis** | [GO_BUNDLE_B3A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B3A_POST_DEPLOY_REPORT.md) ✅ · [GO_BUNDLE_B3C_POST_DEPLOY_REPORT.md](GO_BUNDLE_B3C_POST_DEPLOY_REPORT.md) ✅ |
| **Décision** | **✅ B3c controlled test = GO** |

---

## 1. Décision

**B3c controlled test = GO**

Rail minimal validé en production :

```text
1 parent → 1 child → 1 buy leg USDC→AAVE Base
→ settle_bundle_leg_idempotently(child_intent_id)
→ Child LEDGER_SETTLED
```

Le handler `bundle_leg_settlement_handler` (B3c) est **prouvé en prod** : metadata child, receipts, idempotence, parent inchangé.  
**Pas** d’activation permanente des flags en TD ECS.

---

## 2. Identifiants

| Champ | Valeur |
| --- | --- |
| `test_run_id` | `982b2731039b4893af9fb1b390207669` |
| `parent_intent_id` | `8d5b9e9a-bf38-4186-abab-befc2cf2b152` |
| `child_intent_id` | `d9e30021-a909-40ff-b468-8a7d89e6b946` |
| `swap_id` | `c0e985ca-7c9b-47e3-853c-5ba8275eae8b` |
| `portfolio_id` | `ab4ae920-f3e8-481b-8f82-a41a81d5779d` (Crypto Majors) |
| `plan_hash` | `sha256:9e3f185d72969b0f95dca5333d6a8c31ad05da2e5fb134bb5a66de7bea8f0895` |
| `settlement_receipt_hash` | `sha256:646ac1f4eae14fc6bd094ee99474ccd8f702f31e5648ede92b84c4debb40a09b` |
| `child_report_hash` | `sha256:1f45417a0a37154b814438b1c9fe9ce8c3ecdacc91427ff3d132084701ad0122` |
| `tx_hash` (swap) | `0xd3cf584dfb97f527847ba2717cf5290699c8e85189dc13d6eecf2bb0da8301c0` |
| `amount_usdc` | `1.266673` |

---

## 3. Étapes exécutées

Script : `scripts/arquantix-ecs-bundle-b3c-controlled-test.sh`

| # | Mode | ECS task | Résultat |
| --- | --- | --- | --- |
| 0 | `baseline` | `7adb7b75…` | `baseline_ok=true` · `all_checks_pass=true` |
| 1 | `setup_parent_child` | `a0c97ef1…` | Parent FROZEN + child `awaiting_swap` créés |
| 2 | `attach_existing_swap` | `476a9a51…` | Swap lié · `bundle_internal=true` |
| 3 | `settle_child` | `ee152604…` | Child **LEDGER_SETTLED** · receipts écrits |
| 4 | `audit` | `5f2047e1…` | `all_checks_pass=true` |
| 5 | `settle_child` (REPEAT) | `84f77de1…` | Idempotence · `already_settled` ×2 |

**Git ops** : scripts versionnés `5376ef7d` · fixes S3 payload `c08f0a17`.

Handler activé **uniquement dans le process ECS** des jobs `settle_child` — TD ECS reste flag **OFF**.

---

## 4. Résultats par étape

### Baseline

| Check | Valeur |
| --- | --- |
| Health | **200** |
| Flags OFF | ✅ |
| PE / CB / legs | **19 / 67 / 131** |
| Active locks / dead_letter | **0 / 0** |
| USDC disponible | **162.14** |
| Candidat attach (option B) | `c0e985ca` · CONFIRMED · `bundle_execution=true` |

### Attach

| Check | Valeur |
| --- | --- |
| `bundle_internal` | **true** |
| `linked_table` | `person_wallet_swaps` |
| `linked_id` | `c0e985ca-…` |
| Paire / chains | USDC→AAVE · Base/Base |

### Settle (1er passage)

| Check | Valeur |
| --- | --- |
| `result.settled` | **true** |
| Child phase | **LEDGER_SETTLED** |
| `settlement_receipt_hash` | présent |
| `child_report_hash` | présent |
| Parent | **inchangé** |
| `all_checks_pass` | **true** |

### Audit

| Check | Valeur |
| --- | --- |
| `child_ledger_settled` | ✅ |
| `plan_hash_match` | ✅ |
| `parent_not_reconciled` / `not_completed` | ✅ |
| PE / CB / legs | **19 / 67 / 131** |
| `all_checks_pass` | **true** |

### Idempotence (REPEAT)

| Check | Valeur |
| --- | --- |
| `result_first.idempotent` | **true** (`already_settled`) |
| `result_second.idempotent` | **true** |
| `receipt_stable` | **true** (même hash) |
| Économie avant/après | **inchangée** |
| `all_checks_pass` | **true** |

---

## 5. Critères validés

| Critère | Statut |
| --- | --- |
| Parent inchangé · `REBALANCE_PLAN_FROZEN` | ✅ |
| Child **LEDGER_SETTLED** | ✅ |
| `settlement_receipt_hash` présent | ✅ |
| `child_report_hash` présent | ✅ |
| `plan_hash` parent = child | ✅ |
| PE = **19** (inchangé) | ✅ |
| CB = **67** (inchangé) | ✅ |
| Legs = **131** (inchangé) | ✅ |
| Pas de double écriture (idempotence) | ✅ |
| `dead_letter` = **0** | ✅ |
| `COMPLETED` = **0** | ✅ |
| Flags TD **OFF** (funding · leg · dual-run) | ✅ |

---

## 6. Note importante — Option B (swap pré-existant)

Ce test a utilisé l’**option B** du plan : attacher un swap **déjà CONFIRMED** plutôt que créer un swap via le runtime legacy/UI.

| Fait | Détail |
| --- | --- |
| Swap pré-existant | `c0e985ca` était déjà **CONFIRMED** on-chain (USDC→AAVE Base) |
| Legacy déjà appliqué | `audit_log` contenait déjà `swap_settled` + `bundle_pe_atoms_applied` |
| Comportement B3c | Handler a **réutilisé** l’état Privy/PE existant (pas de second débit/crédit) |
| Ce que B3c a écrit | Metadata child : `bundle_leg_settlement` · `LEDGER_SETTLED` · `settlement_receipt_hash` · `child_report_hash` |

**Ce que ce test prouve :**

- Le **child settlement handler** B3c et son **idempotence** en prod.
- Le rail minimal : parent FROZEN → child → settle → **LEDGER_SETTLED** sans toucher le parent.

**Ce que ce test ne prouve pas encore :**

- Un bundle **end-to-end depuis UI/WebApp**.
- La **création automatique** du swap ni des child legs (B4).
- Un swap **frais** non settlé par le legacy avant passage handler B3c.

---

## 7. Hors scope (maintenu)

| Élément | Statut |
| --- | --- |
| WebApp Bundle end-to-end | hors scope |
| Funding runtime automatique (B3a branché) | hors scope |
| Child creation runtime (B4b) | hors scope |
| Worker / outbox bundle | hors scope |
| Controller parent (B5) | hors scope |
| N legs · parallèle | hors scope |
| Sell legs | hors scope |
| Partial fill | hors scope |
| `COMPLETED` parent | hors scope |
| Webhook credit reuse parité S3b (B3c v2) | hors scope |

---

## 8. Prochaine étape recommandée — B4 minimal

1. **B4b** : création automatique du child intent depuis `rebalance_plan_after_funding` (plan gelé).
2. Test contrôlé **1 parent / 1 child / 1 fresh swap** si un swap non settlé legacy est disponible ou créable sans ouvrir l’UI Bundle legacy.
3. **Seulement ensuite** : envisager un test WebApp contrôlé end-to-end.

**Ne pas activer** `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` en TD prod sans GO explicite post-B4.

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) §4.0.5–§4.0.7 · critère succès B3c
- `services/portfolio_engine/bundles/event_driven/bundle_leg_settlement_handler.py`
- `scripts/_bundle-b3c-controlled-test-inline.py`
