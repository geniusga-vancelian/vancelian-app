# Design — Orchestrateur de rééquilibrage serveur (driver ré-entrant)

| Champ | Valeur |
| --- | --- |
| **Statut** | 🎯 Design — à valider avant implémentation |
| **Date** | 2026-06-12 |
| **Objectif** | Exécuter un rééquilibrage de portefeuille **100 % serveur**, leg après leg, sans navigateur, en réutilisant la fonction atomique `run_virtual_wallet_swap_server_side` |
| **Pré-requis (mergés)** | Exécution serveur déléguée (`execute_prepared_swap_server_side`), fonction unique (`run_virtual_wallet_swap_server_side`), worker `intent.execute` |
| **Références** | [CONTROLLED_PROD_ROLLOUT_SERVER_SIDE_SWAP_EXECUTION.md](CONTROLLED_PROD_ROLLOUT_SERVER_SIDE_SWAP_EXECUTION.md) · [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) |

---

## 1. Problème

Un rééquilibrage = **snapshot NAV** du portefeuille → comparaison à l'**allocation cible** → **deltas par brique/asset** → suite d'actions **SELL** puis **BUY**.

Aujourd'hui ce chaînage vit **dans le navigateur** (`runSequentialTrades`) : 1 leg à la fois, signature client par leg, et un **"resume" serveur entre chaque leg**. On veut le porter côté serveur pour pouvoir l'exécuter via le worker (file d'intents), sans interaction utilisateur.

### Contrainte décisive : dépendance séquentielle des montants

Les montants des **BUY dépendent du produit RÉEL des SELL** (LI.FI fige le `fromAmount`, le `toAmount` est estimé puis réconcilié au montant réellement reçu — slippage). **On ne peut donc pas figer tous les legs à l'avance.** Il faut **re-planifier après chaque leg**.

→ Cela exclut une sous-file pré-remplie d'actions figées (« file dans la file »).

---

## 2. Décision d'architecture

> **MISE À JOUR (post-audit `rebalance_executor.py`).** L'orchestrateur de chaînage
> **existe déjà** : `BundleRebalanceExecutor` enchaîne SELL→BUY leg par leg, gère
> l'idempotence par `plan_hash`, la reprise, la terminalisation, le residual cash,
> le plan-drift et les legs morts. Il fonctionne par **triggers** (`manual`, `deposit`,
> `recovery`, `cron`). Le seul « trou » : il ne sait **pas signer côté serveur** (pour
> les triggers non-client, un quote non signé est expiré).
>
> **Décision retenue : greffer un trigger `server` sur l'executor existant** plutôt que
> construire un driver parallèle. La signature serveur par leg réutilise
> `execute_prepared_swap_server_side`. Tout le reste (ordonnancement, idempotence,
> terminalisation, compta bundle via `submit_signed_trade`) est **réutilisé tel quel**.

**Principe conservé, implémentation par réutilisation :**

| Option | Verdict |
| --- | --- |
| A — Enfiler tous les legs d'un coup (montants figés) | ❌ BUY faux, slippage composé |
| B — Driver parallèle `intent.rebalance_step` | ⚠️ duplique l'ordonnancement déjà testé |
| **C — Trigger `server` dans `BundleRebalanceExecutor`** | ✅ **Retenu** — réutilisation maximale |

On **réutilise l'existant** — aucune nouvelle file, aucun nouvel orchestrateur :
- `BundleRebalanceExecutor` (chaînage SELL→BUY, resume, idempotence, terminal status)
- `execute_prepared_swap_server_side` = **signataire serveur par leg** (le trou comblé)
- `submit_signed_trade` → routage compta bundle automatique
- planification = `drift_rebalance_plan` recalculé par le worker à chaque cycle (NAV → drift)

---

## 3. Modèle

```
intent PARENT (rééquilibrage)                       ← existant : bundle parent + legs[] + statut agrégé
  metadata_json.legs[] : [{leg_id, swap_id, side, asset, status, tx_hash}, ...]
  statut recalculé : AWAITING_SIGNATURE | SUBMITTED | PARTIAL | CONFIRMED | FAILED
  │
  └─ outbox: intent.rebalance_step                  ← NOUVEAU : un seul event "driver", ré-enfilé
       worker (tick DeFi), à CHAQUE passage :
         0. acquérir/valider le LOCK batch (portfolio+batch)         ← isolation
         1. snapshot NAV + recompute plan (planner) → legs pending restants (SELL d'abord)
         2. s'il reste un leg pending :
              run_virtual_wallet_swap_server_side(wallet_from, wallet_to, volume_from)
                = quote LI.FI → signature Privy déléguée → submit → settlement
                  (ledger wallets, atoms PE, PRU/PnL, valorisation EUR/USD figée)
         3. recompute statut parent depuis legs[]
         4. reste-t-il des legs ? → ré-enfile intent.rebalance_step
            sinon → finalise parent (CONFIRMED | PARTIAL) + release lock batch
```

### Pourquoi « 1 leg par passage »
- Unité courte et observable (pas de transaction longue qui bloque le worker).
- Reprise après crash triviale : l'état est en base (legs[] + outbox), le tick suivant repart au prochain leg pending.
- Re-planification naturelle entre legs (étape 1 rejouée à chaque passage).

---

## 4. Isolation — lock scopé batch (décision validée)

Pendant toute la durée d'un rééquilibrage, **aucune autre action du même user ne doit s'intercaler** (ni swap simple, ni autre rééquilibrage).

- Lock **scopé portfolio/batch** (réutilise `bundle_invest_lock` + le scope Product Locks), acquis à l'étape 0 du premier passage, **libéré** quand le parent atteint un statut terminal (`CONFIRMED` / `FAILED` / `PARTIAL` réconcilié).
- Les legs individuels passent par le `lock_key` par-asset existant ; le lock batch est un **lock parent** qui chapeaute la séquence.
- Conséquence : un swap simple sur un autre asset **attend** la fin du rééquilibrage (comportement voulu — cohérence NAV).

---

## 5. Transitions du parent

| Legs[] | Statut parent |
| --- | --- |
| Tous `confirmed` | `CONFIRMED` → finalise + release lock |
| Tous `failed` | `FAILED` → release lock |
| Mix confirmed + (pending/failed) | `PARTIAL` → stop driver, réconciliation |
| Au moins un `submitted`/`pending` | `SUBMITTED` / `AWAITING_SIGNATURE` → ré-enfile step |

Règle de réutilisation : `recompute_bundle_parent_status` (déjà existant) — on ne réinvente pas la machine à états.

---

## 6. Contrat du planner (re-planification)

Le driver appelle le **planner de rééquilibrage existant** (celui qui alimente déjà `sell_results` / `buy_results` / `v3_status` côté API). Contrat attendu :

```
plan_next_rebalance_legs(db, *, person_id, portfolio_id, batch_id) -> RebalancePlan
  RebalancePlan:
    v3_status: RUNNING | COMPLETED | PARTIAL | FAILED
    pending_legs: [PendingLeg]   # SELL d'abord puis BUY, déjà ordonnés
    PendingLeg: {leg_id, side, wallet_from_id, wallet_to_id, volume_from, asset, ...}
```

- `volume_from` = montant exact d'entrée (exact-in LI.FI), recalculé à partir de la NAV courante (donc tient compte du réel des SELL déjà exécutés).
- Si `pending_legs` vide et `v3_status` terminal → fin.

> À l'implémentation : identifier la fonction serveur qui produit aujourd'hui `PortfolioRebalancingPayload` (endpoint `/rebalance` + `resume`) et l'exposer comme primitive réutilisable par le driver.

---

## 7. Robustesse — propriétés garanties

| Propriété | Mécanisme |
| --- | --- |
| **Idempotence par leg** | `execute_prepared_swap_server_side` ne re-signe pas un swap déjà `CONFIRMED`/`SUBMITTED` |
| **Reprise après crash** | État en base (legs[] + outbox `pending`) ; le tick suivant reprend au prochain leg |
| **Échec partiel propre** | 1 leg échoue → parent `PARTIAL`, driver s'arrête, lock libéré, réconciliation possible |
| **Pas de double exécution** | `insert_event_idempotent_per_intent_type` (1 seul `intent.rebalance_step` actif par parent) |
| **Sérialisation globale** | lock batch + `lock_key` par-asset → pas de collision avec swap simple |
| **Fallback délégation** | si wallet non délégué → `awaiting_signature`, rééquilibrage non démarré côté serveur (le client peut toujours opérer) |

---

## 8. Plan d'incréments (flags OFF par défaut)

| # | Incrément | Tests |
| --- | --- | --- |
| R1 | Primitive planner serveur réutilisable (`plan_next_rebalance_legs`) extraite de l'existant | unit : NAV → deltas → legs ordonnés SELL/BUY |
| R2 | Lock batch parent (acquire/release scopé portfolio+batch) | unit : acquisition, release sur terminal, blocage swap concurrent |
| R3 | Event `intent.rebalance_step` + handler driver (1 leg + re-enqueue) | unit : 1 leg/passage, re-planification, idempotence |
| R4 | Enregistrement dans le tick DeFi derrière `LIFI_REBALANCE_WORKER_ENABLED` (OFF) | e2e : chaîne SELL→BUY complète en mock |
| R5 | Rollout allowlist + runbook + observabilité (legs[], transitions) | e2e partiel + échec leg → PARTIAL |

---

## 9. Réutilisabilité (vision « fonction par fonction »)

- `run_virtual_wallet_swap_server_side` = brique atomique testée, **réutilisée telle quelle** par le driver (et demain par d'autres produits : DCA, vault rebalance, withdraw).
- Le driver `intent.rebalance_step` est **agnostique du produit** : il consomme un planner + une action atomique. Un autre produit fournirait son propre planner et réutiliserait le même squelette de chaînage.

---

## 10. Hors scope (ce design ne fait PAS)

- Pas de changement du flux client existant (`runSequentialTrades` reste le chemin par défaut tant que le flag serveur est OFF).
- Pas de nouvelle table de file (réutilise `transaction_outbox`).
- Pas de signature non-déléguée côté serveur (fallback client préservé).
