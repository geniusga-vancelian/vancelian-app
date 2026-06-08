# Rapport GO — Test contrôlé Bundle B5 minimal (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **Merge** | `bc9f8845` |
| **Task definition** | **`arquantix-api:160`** |
| **Plan** | [GO_BUNDLE_B5_MINIMAL_TEST_PLAN.md](GO_BUNDLE_B5_MINIMAL_TEST_PLAN.md) |
| **Prérequis** | [GO_BUNDLE_B5_POST_DEPLOY_REPORT.md](GO_BUNDLE_B5_POST_DEPLOY_REPORT.md) ✅ · [GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md) ✅ |
| **Décision** | **✅ B5 controlled test = GO** |

---

## 1. Décision

**B5 controlled test = GO**

Premier agrégateur parent validé en production :

```text
Parent CHILD_LEGS_CREATED (post-B4b)
  → reconcile_bundle_parent_idempotently(parent)  [flag ON job only]
  → vérifie child LEDGER_SETTLED + hashes
  → parent RECONCILED + parent_report_hash
  → 2ᵉ run idempotent (parent_already_reconciled)
```

Metadata-only · aucune écriture PE/CB · child inchangé · pas de COMPLETED.

---

## 2. Identifiants

| Champ | Valeur |
| --- | --- |
| `parent_intent_id` | `0ef6517e-10c1-453b-bce7-3e6ff08c866d` |
| `child_intent_id` | `38edba08-a7ab-4b77-968d-3b275fb7e4aa` |
| `swap_id` (B4b) | `6bcbffed-0784-4807-a10f-93a757a53045` |
| `plan_hash` | `sha256:ed579996c0bef170416c760b6b6cda00071e2a445681955f378f42b80b4efa9e` |
| `parent_report_hash` | `sha256:3c2c8703dee6bf0d2e62360ea2568823714209e5634ea623e5d1362676926df3` |
| `child_report_hash` | `sha256:305085131defd5a39b01ef308173a16217e9fc8cd098f1285bc750936de5ae62` |
| `settlement_receipt_hash` | `sha256:66fd7886a3b2e0d2a3af5f6b6c385d72e1dd16f3392df7a9977f108a20e9b9fc` |

---

## 3. Étapes exécutées

Script : `scripts/arquantix-ecs-bundle-b5-controlled-test.sh`

| # | Mode | ECS task (suffix) | Résultat |
| --- | --- | --- | --- |
| 0 | `baseline` | `53a51d75…` | `all_checks_pass=true` · flag OFF |
| 1 | `reconcile_parent` | `81ba17e9…` | Parent **RECONCILED** · `parent_report_hash` écrit |
| 2 | `audit` | `88eeb3e2…` | `all_checks_pass=true` |
| 3 | `reconcile_parent` REPEAT | `38ddb7e3…` | `idempotent=true` · `parent_already_reconciled` |

Flag `BUNDLE_PARENT_CONTROLLER_ENABLED` activé **uniquement** dans le job `reconcile_parent`.

---

## 4. Critères validés

| Critère | Statut |
| --- | --- |
| Parent → **RECONCILED** | ✅ |
| `parent_report_hash` présent | ✅ |
| Child metadata **inchangé** | ✅ |
| PE = **19** | ✅ |
| CB = **67** | ✅ |
| legs = **131** | ✅ |
| `COMPLETED` = **0** | ✅ |
| `dead_letter` = **0** | ✅ |
| 2ᵉ run **idempotent** | ✅ |
| Flags TD **OFF** hors job | ✅ |

---

## 5. Périmètre de preuve (rappel)

| Validé par B5 | Non validé |
| --- | --- |
| Agrégation metadata parent | Swap on-chain réel |
| Cohérence hashes child → parent | Signature Privy réelle |
| Idempotence controller parent | Settlement économique réel WebApp |
| Pas d'écriture PE/CB | |

B4b + B5 prouvent l'**orchestration + contrôle** bout-en-bout en metadata. Le **dernier jalon** reste le test WebApp 1 USDC Base.

---

## 6. Prochaine étape

[GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_PLAN.md](GO_BUNDLE_WEBAPP_INVEST_1USDC_TEST_PLAN.md) — premier investissement réel **1 USDC** via WebApp Bundle Invest sur Base.

**Ne pas** ouvrir N legs · sell · rebalance · withdraw avant WebApp vert.
