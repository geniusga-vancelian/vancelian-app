# Plan d'exécution — Test contrôlé Bundle B5 minimal (prod)

| Champ | Valeur |
| --- | --- |
| **Statut** | **✅ EXÉCUTÉ — GO** ([rapport](GO_BUNDLE_B5_MINIMAL_CONTROLLED_TEST_REPORT.md)) |
| **Objectif** | Prouver l'agrégateur parent : tous children `LEDGER_SETTLED` → parent `RECONCILED` + `parent_report_hash` |
| **Prérequis** | [GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md) ✅ · [GO_BUNDLE_B5_REVIEW.md](GO_BUNDLE_B5_REVIEW.md) ✅ |
| **Parent cible** | `0ef6517e-10c1-453b-bce7-3e6ff08c866d` (B4b · child `38edba08…` déjà `LEDGER_SETTLED`) |
| **Rapport** | `GO_BUNDLE_B5_MINIMAL_CONTROLLED_TEST_REPORT.md` *(à produire)* |

---

## Ce que ce test prouve

```text
Parent CHILD_LEGS_CREATED
  → reconcile_bundle_parent_idempotently(parent)  [flag ON job only]
  → vérifie child LEDGER_SETTLED + hashes
  → parent RECONCILED + parent_report_hash
  → 2ᵉ call = no-op idempotent
```

**Sans** : settlement · swap · PE/CB · lock release · COMPLETED.

---

## Étapes

| # | Mode | Vérifications |
| --- | --- | --- |
| 0 | `baseline` | Flag OFF · PE/CB/legs baseline · COMPLETED=0 |
| 1 | `reconcile_parent` | Parent `RECONCILED` · `parent_report_hash` · child inchangé |
| 2 | `audit` | `all_checks_pass` |
| 3 | `reconcile_parent` REPEAT | Idempotence · économie inchangée |

```bash
./scripts/arquantix-ecs-bundle-b5-controlled-test.sh baseline
BUNDLE_B5_TEST_CONFIRM=1 PARENT_INTENT_ID=0ef6517e-10c1-453b-bce7-3e6ff08c866d \
  ./scripts/arquantix-ecs-bundle-b5-controlled-test.sh reconcile_parent
PARENT_INTENT_ID=0ef6517e-10c1-453b-bce7-3e6ff08c866d \
  ./scripts/arquantix-ecs-bundle-b5-controlled-test.sh audit
BUNDLE_B5_TEST_CONFIRM=1 PARENT_INTENT_ID=0ef6517e-10c1-453b-bce7-3e6ff08c866d \
  ./scripts/arquantix-ecs-bundle-b5-controlled-test.sh reconcile_parent
```

---

## Critères GO

- [ ] Parent `phase=RECONCILED` · `parent_report_hash` présent
- [ ] Child metadata **inchangé**
- [ ] PE/CB/legs **19/67/131** inchangés
- [ ] `COMPLETED=0`
- [ ] 2ᵉ reconcile = idempotent
- [ ] Flags TD **OFF** hors job

---

## Après GO B5

**WebApp Bundle Invest 1 USDC Base** — seul jalon restant pour sortir du laboratoire (Privy réel · swap réel · confirmation réelle · settlement économique réel).
