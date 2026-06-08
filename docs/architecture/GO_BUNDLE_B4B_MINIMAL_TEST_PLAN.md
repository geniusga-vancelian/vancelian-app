# Plan d'exécution — Test contrôlé Bundle B4b minimal (prod)

| Champ | Valeur |
| --- | --- |
| **Statut** | **✅ EXÉCUTÉ — GO** ([rapport](GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md)) |
| **Objectif** | Prouver le premier pont runtime Bundle : **parent FROZEN → child auto (B4a) → global lock → fresh swap LI.FI → attach → settle B3c → child LEDGER_SETTLED** |
| **Prérequis code** | PR B4b mergée · TD **≥ :156** · image post-merge |
| **Prérequis gate** | [GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md](GO_BUNDLE_B4A_POST_DEPLOY_REPORT.md) ✅ · [GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md](GO_GLOBAL_USER_TRANSACTION_LOCK_CONTROLLED_TEST_REPORT.md) ✅ · [GO_BUNDLE_B3C_CONTROLLED_TEST_REPORT.md](GO_BUNDLE_B3C_CONTROLLED_TEST_REPORT.md) ✅ |
| **Feu vert requis** | **Go « B4b Controlled Test » explicite** après relecture de ce plan |
| **Rapport d'exécution** | `GO_BUNDLE_B4B_MINIMAL_CONTROLLED_TEST_REPORT.md` *(à produire après run)* |

---

## Position

### Ce que ce test prouve

```text
Parent REBALANCE_PLAN_FROZEN
  → run_bundle_b4b_minimal_bridge(parent_intent_id)  [flag ON dans le job seulement]
  → Child #0 auto (B4a) · awaiting_swap
  → Global User Transaction Lock acquis (parent_intent_id)
  → Fresh swap LI.FI USDC→AAVE Base/Base · bundle_execution=true
  → Swap attaché au child (linked_table · entry/target_instrument_id)
  → settle_bundle_leg_idempotently(child) si swap CONFIRMED (B3c)
  → Child LEDGER_SETTLED
  → Global lock released
```

| Critère B4b | Preuve attendue |
| --- | --- |
| Fresh swap | Nouveau `person_wallet_swaps` créé par le bridge · **pas** d'attach manuel |
| No manual setup | **Pas** de `setup_parent_child` · **pas** de `attach_existing_swap` séparé |
| Child auto | B4a invoqué depuis le bridge si child absent |
| Global lock | 1 lock actif pendant le run · **0** après succès |
| Settlement B3c | Child `bundle_leg_settlement.phase = LEDGER_SETTLED` |
| Idempotence | 2ᵉ run → no-op économique · child déjà settled |
| Parent inchangé | Pas de `RECONCILED` · pas de `COMPLETED` · pas de finalize |
| Flags TD | Restent **OFF** hors job ECS |

### Ce plan ne fait pas

- activation permanente des flags B4b / global lock / B3c en TD ECS ;
- WebApp Bundle ;
- Controller parent (B5) ;
- finalize parent · `COMPLETED` · `RECONCILED` parent ;
- N legs · sell · parallèle ;
- worker long-running / outbox ;
- exécution avant Go explicite.

Référence doctrine : [BUNDLE_EVENT_DRIVEN_DESIGN.md](BUNDLE_EVENT_DRIVEN_DESIGN.md) § Phase B4.

---

## État prod connu (post-gate Global Lock · TD `:156`)

| Élément | Valeur |
| --- | --- |
| Task definition | **`arquantix-api:156`** |
| `BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED` | **absent** |
| `GLOBAL_USER_TRANSACTION_LOCK_ENABLED` | **absent** |
| `BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED` | **absent** |
| Compte pilote | `gaelitier@gmail.com` → `person_id` **`8b0e0044-f1ef-47a5-99d4-370598a77492`** |
| Client PE | **`080358a8-4519-4acf-b5da-25485446c967`** |
| Baseline économique | PE **19** · CB **67** · legs **131** |
| Active locks | **0** |
| `dead_letter` | **0** |
| `COMPLETED` bundle parent | **0** |

**Gate pré-test** : relancer `baseline` (§ 1). **STOP** si un écart.

---

## Design du test — 1×1×1 strict

### Contrainte d'isolation

```
person_id     = 8b0e0044-f1ef-47a5-99d4-370598a77492
from_asset    = USDC
to_asset      = AAVE
chains        = base / base
leg_index     = 0
direction     = buy
montant       = 1 USDC (recommandé — ajustable via NOTIONAL_USDC)
```

**Interdit** : setup manuel parent/child · attach manuel swap · UNI · ETH · sell · 2ᵉ leg · Controller · finalize parent · UI Bundle legacy · flags ON en TD.

### Flow attendu (automatique)

1. Créer parent `REBALANCE_PLAN_FROZEN` avec `rebalance_plan_after_funding` 1 leg BUY USDC→AAVE Base.
2. Appeler **une seule fois** `run_bundle_b4b_minimal_bridge(db, parent_intent_id)` avec flags ON dans le process ECS.
3. Le bridge crée child (B4a), quote LI.FI, attache swap, attend CONFIRMED (on-chain ou mock contrôlé selon script).
4. Après CONFIRMED : settlement B3c inline ou second job `bridge_resume` si swap async.

> **Note** : si le fresh swap reste `QUOTE_RECEIVED` dans le premier job, un second job avec le même `parent_intent_id` doit reprendre idempotent (lock ré-acquis même intent) jusqu'à CONFIRMED puis settle.

---

## Outils

| Artefact | Rôle |
| --- | --- |
| `scripts/arquantix-ecs-bundle-b4b-minimal-test.sh` | Orchestration ECS modes |
| `scripts/_bundle-b4b-minimal-test-inline.py` | Logique inline (à créer avec la PR) |
| `run_bundle_b4b_minimal_bridge` | Handler B4b |
| `settle_bundle_leg_idempotently` | Handler B3c (appelé par B4b si CONFIRMED) |

Flags activés **uniquement** dans le process ECS du job — TD ECS reste **OFF**.

---

## Étapes

| # | Mode | Vérifications |
| --- | --- | --- |
| 0 | `baseline` | Health 200 · flags OFF · PE/CB/legs baseline · locks=0 · dead_letter=0 · COMPLETED=0 |
| 1 | `create_frozen_parent` | Parent `REBALANCE_PLAN_FROZEN` · plan_hash · 1 leg BUY USDC→AAVE · **0** child |
| 2 | `run_b4b_bridge` | Child créé · lock acquis · fresh swap · attach · metadata enrichie |
| 3 | `wait_confirmed` *(si async)* | Swap `CONFIRMED` · `tx_hash` présent · `bundle_execution=true` |
| 4 | `run_b4b_bridge` *(repeat si besoin)* | Child `LEDGER_SETTLED` · lock released |
| 5 | `audit` | PE/CB/legs deltas attendus · dead_letter=0 · COMPLETED=0 · parent phase ≠ RECONCILED |
| 6 | `run_b4b_bridge` *(REPEAT)* | Idempotence · no-op économique |

---

## Critères GO / NO-GO

### GO si tous vrais

- [ ] Fresh swap créé par le bridge (audit `bundle_leg_context` · `bundle_execution=true`)
- [ ] Aucun setup manuel parent/child hors script
- [ ] Aucun attach manuel swap hors bridge
- [ ] Child `LEDGER_SETTLED` avec receipts B3c
- [ ] Global lock acquis puis **0** lock actif post-succès
- [ ] PE atoms + bundle cash leg deltas cohérents avec montant test (1 USDC typique)
- [ ] `dead_letter = 0`
- [ ] `COMPLETED = 0` (parent)
- [ ] 2ᵉ run bridge = no-op économique
- [ ] Flags TD ECS inchangés (OFF)

### NO-GO si

- Lock orphelin actif post-run
- Double settlement / double PE write
- Parent `RECONCILED` ou `COMPLETED`
- Swap non taggé bundle internal
- Flags laissés ON en TD

---

## Rollback

1. Vérifier `find_active_global_user_transaction_lock` → release si lock orphelin (`intent_id` du parent test).
2. Documenter intent IDs dans le rapport.
3. Ne pas activer flags en TD.
4. Baseline PE/CB/legs doit revenir à l'équilibre attendu (hors effet économique voulu du leg test).

---

## WebApp

Test WebApp Bundle Invest **uniquement après** B4b controlled test **GO** et rapport publié.
