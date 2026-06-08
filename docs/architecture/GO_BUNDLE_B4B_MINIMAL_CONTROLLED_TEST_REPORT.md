# Rapport GO — Test contrôlé Bundle B4b minimal (prod)

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-08 |
| **Compte pilote** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **PR / merge** | [#60](https://github.com/geniusga-vancelian/vancelian-app/pull/60) · `55889379` |
| **Hotfix test** | `1aa113db` — resume `swap_attached` · CI [run 27147546023](https://github.com/geniusga-vancelian/vancelian-app/actions/runs/27147546023) |
| **Task definition** | **`arquantix-api:158`** (post-hotfix) |
| **Plan** | [GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md](GO_BUNDLE_B4B_MINIMAL_TEST_PLAN.md) |
| **Prérequis** | [GO_BUNDLE_B4B_POST_DEPLOY_REPORT.md](GO_BUNDLE_B4B_POST_DEPLOY_REPORT.md) ✅ · Go explicite **« B4b Controlled Test »** |
| **Décision** | **✅ B4b controlled test = GO** |

---

## 1. Décision

**B4b controlled test = GO**

Premier rail quasi bout-en-bout Bundle validé en production :

```text
Parent REBALANCE_PLAN_FROZEN
  → run_bundle_b4b_minimal_bridge(parent_intent_id)  [flags ON job only]
  → Child #0 auto (B4a) · awaiting_swap
  → Global User Transaction Lock acquis
  → Fresh swap LI.FI USDC→AAVE Base · bundle_execution=true
  → Attach automatique · metadata status swap_attached
  → CONFIRMED (shim contrôlé execute_fresh_swap · LIFI_SWAPS_MOCK=1 job only)
  → settle_bundle_leg_idempotently (B3c inline)
  → Child LEDGER_SETTLED
  → Global lock released
  → 2ᵉ run bridge = no-op économique (mêmes hashes)
```

Sans setup parent/child manuel · sans attach swap manuel · sans intervention humaine intermédiaire · flags TD ECS restent **OFF**.

**Estimation post-GO** : rail transactionnel Bundle ~**90–95 %** du premier bundle réel — prochain chantier **B5 Parent Controller**, puis test WebApp Bundle Invest petit montant.

---

## 2. Identifiants

| Champ | Valeur |
| --- | --- |
| `test_run_id` | `8c446cc0a0b94f6584fc42d92981a854` |
| `parent_intent_id` | `0ef6517e-10c1-453b-bce7-3e6ff08c866d` |
| `child_intent_id` | `38edba08-a7ab-4b77-968d-3b275fb7e4aa` |
| `swap_id` | `6bcbffed-0784-4807-a10f-93a757a53045` |
| `portfolio_id` | `ab4ae920-f3e8-481b-8f82-a41a81d5779d` (Crypto Majors) |
| `plan_hash` | `sha256:ed579996c0bef170416c760b6b6cda00071e2a445681955f378f42b80b4efa9e` |
| `settlement_receipt_hash` | `sha256:66fd7886a3b2e0d2a3af5f6b6c385d72e1dd16f3392df7a9977f108a20e9b9fc` |
| `child_report_hash` | `sha256:305085131defd5a39b01ef308173a16217e9fc8cd098f1285bc750936de5ae62` |
| `tx_hash` (swap) | `0xmock-b4b-6bcbffed07844807a10f93a757a53045` |
| `amount_usdc` | `1` |

---

## 3. Étapes exécutées

Script : `scripts/arquantix-ecs-bundle-b4b-minimal-test.sh`

| # | Mode | ECS task (suffix) | Résultat |
| --- | --- | --- | --- |
| 0 | `baseline` | *(pré-test)* | `all_checks_pass=true` · PE **19** / CB **67** / legs **131** · locks **0** |
| 1 | `create_frozen_parent` | *(pré-test)* | Parent FROZEN · **0 child** · plan_hash stable |
| 2 | `run_b4b_bridge` (1er) | *(pré-hotfix)* | Child créé · lock acquis · **fresh swap** `6bcbffed…` · `swap_attached` · `awaiting_swap_confirmation` |
| 2b | `execute_fresh_swap` | *(pré-hotfix)* | Swap **CONFIRMED** via `LIFI_SWAPS_MOCK=1` (job only) · quote LI.FI réel en step 2 |
| 3 | `run_b4b_bridge` (settle) | `fa8ce47c…` | **LEDGER_SETTLED** · lock released · `all_checks_pass=true` |
| 4 | `audit` | `4189cb45…` | `all_checks_pass=true` · parent ≠ RECONCILED/COMPLETED |
| 5 | `run_b4b_bridge` (REPEAT) | `45837186…` | `idempotent=true` · `child_already_ledger_settled` · économie inchangée |
| 6 | `baseline` (post) | `0ee58bf5…` | Flags OFF ✅ · PE/CB/legs baseline ✅ · locks **0** · health 503 transitoire depuis task *(curl externe 200)* |

Flags activés **uniquement** dans le process ECS des jobs `run_b4b_bridge` / `execute_fresh_swap` — TD ECS reste flag **OFF**.

---

## 4. Résultats par critère observé

### Fresh swap (pas de réutilisation accidentelle)

| Check | Valeur |
| --- | --- |
| Swap créé par bridge | `6bcbffed-0784-4807-a10f-93a757a53045` (nouveau) |
| `bundle_execution` | **true** |
| `bundle_internal` | **true** |
| `bundle_leg_context` | `plan_hash` · `planner_version` · `parent/child_intent_id` · `leg_index=0` |

### Global lock

| Check | Valeur |
| --- | --- |
| Lock acquis (1er bridge) | **true** (`global_lock_acquired=true`) |
| Lock actif post-succès | **0** (`active_financial_locks_zero`) |
| Lock released au settle | **true** |

### Transitions child

| Phase | Statut |
| --- | --- |
| Après B4a | `awaiting_swap` |
| Après attach | `metadata.status = swap_attached` |
| Après B3c | `bundle_leg_settlement.phase = LEDGER_SETTLED` |

### Parent inchangé

| Check | Valeur |
| --- | --- |
| `current_phase` | `created` |
| `metadata_phase` | `CHILD_LEGS_CREATED` |
| RECONCILED / COMPLETED | **non** |

### Idempotence (2ᵉ run)

| Check | Valeur |
| --- | --- |
| `bridge_result.idempotent` | **true** |
| `reason` | `child_already_ledger_settled` |
| `settlement_receipt_hash` | stable |
| `child_report_hash` | stable |
| PE / CB / legs avant/après | **19 / 67 / 131** (inchangé) |

### Baseline économique

| Métrique | Avant test | Après test |
| --- | --- | --- |
| PE | 19 | 19 |
| CB | 67 | 67 |
| `lifi_swap_legs` | 131 | 131 |
| `dead_letter` | 0 | 0 |
| `COMPLETED` | 0 | 0 |
| Active locks | 0 | 0 |

---

## 5. Critères GO

| Critère | Statut |
| --- | --- |
| Fresh swap créé par le bridge (pas d'attach manuel) | ✅ |
| `bundle_leg_context` : `plan_hash` · `planner_version` · parent/child · `leg_index` | ✅ |
| Child `swap_attached` puis **LEDGER_SETTLED** | ✅ |
| Global lock acquis puis **0** actif post-succès | ✅ |
| `dead_letter=0` · `COMPLETED=0` | ✅ |
| 2ᵉ run = no-op économique (mêmes hashes) | ✅ |
| Parent pas RECONCILED/COMPLETED | ✅ |
| Flags TD **OFF** hors job ECS | ✅ |
| PE/CB/legs deltas économiques réels (1 USDC on-chain) | ⚠️ **N/A mock** — voir §6 |

---

## 6. Périmètre de preuve — ce que ce rapport valide (et ce qu’il ne valide pas)

> **Artefact de preuve** — à lire avant tout test WebApp ou extension N legs.
> Ce rapport **ne doit pas** être interprété comme une validation swap on-chain réel.

| Capacité | Validé par B4b controlled test |
| --- | --- |
| Quote LI.FI réel | ✅ |
| Fresh swap créé par B4b | ✅ |
| Rail Bundle complet (orchestration) | ✅ |
| Confirmation blockchain réelle | ❌ |
| Signature Privy réelle | ❌ |
| `LIFI_SWAPS_MOCK=1` dans le job ECS (shim contrôlé) | ✅ (documenté) |

**État projet après B4b** :

| Avant B4b | Après B4b |
| --- | --- |
| Architecture validée ~**80 %** | Architecture + orchestration ~**95 %** |
| Risque principal : comptabilité · settlement · lock · orchestration | Risque restant : **intégration blockchain réelle** (Privy → signature → swap Base → confirmation → settlement économique réel) |

Le **dernier ~5 %** est l’intégration on-chain réelle — pas l’architecture. Prochain jalon opérationnel : **test WebApp Bundle Invest 1 USDC Base** après **B5 Parent Controller**.

---

## 7. Incident résolu en cours de test + shim confirmation

### Hotfix `swap_attached` resume (`1aa113db`)

Le **2ᵉ `run_b4b_bridge`** (après attach, swap CONFIRMED) échouait sur TD `:157` :

```text
BundleB4bBridgeError: child status='swap_attached' — awaiting_swap requis
```

**Cause** : `_validate_single_child_awaiting_swap` n'acceptait que `awaiting_swap` alors que le follow-up `swap_attached` est le statut attendu entre attach et settlement.

**Fix** : accepter `{awaiting_swap, swap_attached}` pour le resume. Déployé TD **`:158`**. Settlement + idempotence **verts** après hotfix.

### Shim `execute_fresh_swap` (confirmation contrôlée)

B4b ne signe/soumet **pas** on-chain. Le plan prévoit un 2ᵉ job si le swap reste `QUOTE_RECEIVED`. En prod, mode **`execute_fresh_swap`** ajouté au script :

- Quote LI.FI **réel** au 1er bridge ;
- Confirmation via **`LIFI_SWAPS_MOCK=1` uniquement dans le job ECS** (pas en TD) ;
- `tx_hash` mock `0xmock-b4b-…`.

**Ce que ce test prouve** : orchestration automatique parent → child → lock → fresh swap → attach → settle → release, idempotence.

**Ce que ce test ne prouve pas encore** : signature Privy / soumission on-chain réelle depuis le bridge (reste au WebApp ou worker futur). Les compteurs PE/CB/legs sont restés à la baseline car aucun mouvement on-chain réel n'a été exécuté — cohérent avec le shim mock, à revalider au **premier test WebApp Bundle Invest** avec petit montant réel.

---

## 8. Rollback / état résiduel

| Élément | État |
| --- | --- |
| Global lock orphelin | **aucun** (`active_financial_locks=0`) |
| Parent test | `0ef6517e…` · FROZEN · `CHILD_LEGS_CREATED` — laissé documenté |
| Flags TD | **OFF** |
| Action requise | Aucune urgence — parent/child/swap de test conservés pour audit |

---

## 9. Prochaine étape

1. **B5 Parent Controller** — transitions parent post-legs, sans `RECONCILED`/`COMPLETED` prématuré.
2. **Premier test WebApp Bundle Invest** — petit montant réel · swap on-chain réel · deltas PE attendus.
3. Ne pas activer flags B4b / global lock / B3c en TD prod sans GO explicite.

---

## Références

- [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) § Phase B4
- `services/portfolio_engine/bundles/event_driven/bundle_b4b_runtime_bridge.py`
- `scripts/_bundle-b4b-minimal-test-inline.py`
- Hotfix : commit `1aa113db`
