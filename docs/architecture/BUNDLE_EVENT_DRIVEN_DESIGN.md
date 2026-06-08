# Bundle Event-Driven — Audit & Design (v0)

| Champ | Valeur |
| --- | --- |
| **Type** | Audit + design · **aucun code runtime** |
| **Date** | 2026-06-07 |
| **Statut** | Design actif — B1/B2/B2b/B3b/B3a mergés · deploy neutre B3a · **GO B3c** (rail minimal USDC→AAVE · Base) |
| **Prérequis validés** | Rail LI.FI standalone event-driven · Controller v1.2 chain-aware · GO manuel 3/3 RECONCILED |
| **Interdictions** | Pas de migration · pas de changement settlement/locks/controller standalone · pas d’activation prod |

---

## Résumé exécutif

Bundle crypto (`crypto_bundle` / `bundle_invest`) est aujourd’hui un **orchestrateur PE legacy** : funding comptable interne, legs LI.FI on-chain, écritures **synchrones** (Privy + PE + cost basis) dans le thread HTTP de confirmation de leg. Il **ne suit pas** le rail prouvé :

```
Intent → Outbox → Worker → Settlement → Ledger → Controller → RECONCILED
```

La cible est un **orchestrateur multi-transactions** : 1 intent parent, N legs économiques, settlement et réconciliation **par leg**, puis **Controller parent** agrégateur — **pas** « N swaps LI.FI standalone mis bout à bout ».

**Recommandation de fond** : figer d’abord le modèle **parent / child + locks + settlement par leg** ; le Controller parent vient ensuite (premier vrai cas ADR 003 multi-leg), **sans** commencer par le Controller.

**Doctrine CTO (2026-06-08)** : **Bundle Invest = Funding + Rebalance-to-target** — le bundle ne répartit pas simplement le montant USDC entrant selon les poids cibles ; il **fonde**, **recalcule l’état réel global**, puis **génère un plan de rebalance** dont dérivent les legs. Voir [§4.0](#40-doctrine-funding--rebalance-to-target).

**État livré** : B1 parent/child schema ✅ · B2 Product Lock parent ✅ · B2b dual-run locks ✅ (flag OFF prod · deploy neutre TD `:151`).

---

## 1. État actuel du Bundle

### 1.1 Différence fondamentale vs swap simple

| Dimension | LI.FI standalone | Bundle invest (actuel) |
| --- | --- | --- |
| Intent | 1 intent `lifi_swap` | 1 intent parent `bundle_invest` |
| Exécution | 1 swap | Funding + N legs LI.FI |
| Settlement | Worker outbox → S3b | Synchrone HTTP dans `BundleLifiLegService` |
| Ledger Privy | S3b seul writer (prod gelé) | `apply_swap_settlement` legacy direct |
| PE / cost basis | Post-settlement orchestrateur | Inline dans `_apply_post_confirmation` |
| Controller | v1.2 `RECONCILED` (manuel validé) | **Exclu** (`controller.bundle_internal_swap`) |
| Lock | S4 `transaction_product_locks` (allowlist OFF) | JSON `pe_portfolios.metadata.bundle_invest_lock` |
| Phases orchestrateur | `CREATED → … → LEDGER_SETTLED → RECONCILED` | N/A — statuts intent `partial` / `confirmed` ad hoc |

### 1.2 Flow actuel — Invest LI.FI (simplifié)

```text
POST /bootstrap/bundle/invest
  → BundleOrchestrator.invest_into_bundle
    → acquire bundle_invest_lock (batch_id)          [pe_portfolios.metadata]
    → ensure_bundle_parent_intent                    [transaction_intents ×1]
    → fund_bundle_cash_leg_from_self_trading         [PE direct — pas Privy]
    → plan_allocation_legs (legacy)                  [⚠️ split du cash entrant par poids — pas rebalance global]
    → pour chaque leg planifiée :
         BundleLifiLegService.quote_leg / prepare-sign / submit-tx
           → person_wallet_swaps + audit bundle_leg_context
           → register_bundle_leg dans metadata_json.legs[]
           → si CONFIRMED (dans submit-tx HTTP) :
                apply_swap_settlement                  [Privy legacy sync]
                apply_*_leg_atoms                      [PE direct]
                ingest_bundle_lifi_swap_settlement     [cost basis inline]
                bundle_ledger shadow                   [miroir PE]
                mark_bundle_leg_confirmed + recompute parent status
    → release / terminal lock selon status batch
```

**Rebalance** et **withdraw** suivent le même pattern (`BundleRebalanceOrchestrator`, `BundleWithdrawOrchestrator`) avec actions `rebalance_*` / `withdraw_sell` dans `bundle_leg_context`.

### 1.3 Tables et modèles de persistance

| Artefact | Table / emplacement | Rôle |
| --- | --- | --- |
| Produit catalogue | `pe_product_definitions` (`product_type=crypto_bundle`) | Définition bundle admin |
| Portfolio bundle | `pe_portfolios` (`portfolio_type=bundle_portfolio`) | Conteneur positions + **lock JSON** |
| Cash leg | `pe_position_atoms` (`position_type=cash`, `metadata.role=bundle_cash_leg`) | USDC funding interne bundle |
| Positions spot | `pe_position_atoms` (spot alloués) | Positions post-leg |
| Allocations cibles | `pe_target_allocations` | Poids instruments |
| Swap par leg | `person_wallet_swaps` | Exécution LI.FI ; `audit_log` → `bundle_leg_context` |
| Intent parent | `transaction_intents` (`product_type=bundle_invest`) | **1 row** ; legs = `metadata_json.legs[]` |
| Legs (pas de table) | Embedded dans parent metadata | `{leg_id, swap_id, asset, status, tx_hash}` |
| Shadow ledger | `bundle_ledger_entries` | Append-only miroir (Phase 4A) — **non autoritaire** ADR 004 |
| Cost basis | `cost_basis_executions` | PRU scoped `portfolio_scope=bundle` |
| Privy ledger | `person_wallet_deposits` | Via `apply_swap_settlement` |
| Self-trading source | `pe_position_atoms` (direct overlay) | Débit funding |

**Pas de** table `bundle_legs`, `bundle_execution_groups`, ni child intents séparés aujourd’hui.

### 1.4 Frontière bundle vs standalone

Signal canonique : `is_bundle_internal_swap()` dans `bundle_transaction_scope.py`.

```text
person_wallet_swaps.audit_log
  → event: bundle_leg_context
  → bundle_execution: true
  → batch_id, leg_id, portfolio_id, bundle_action
```

Conséquences si tag présent :

| Composant | Comportement |
| --- | --- |
| `orchestrator_settle_enqueue` | Pas de `intent.settle` (`reason=bundle_internal_swap`) |
| `settlement/lifi_ledger.py` (S3b) | Refus `settlement.bundle_internal_swap` |
| `lifi_intent_sync` | Pas d’intent `lifi_swap` standalone |
| `lifi_swap_controller` v1.2 | Terminal `controller.bundle_internal_swap` |

**Risque bypass** : swap sans `bundle_execution=true` pourrait entrer dans le rail standalone — le tagging dans `_attach_bundle_context` est la barrière critique.

### 1.5 Observabilité / réconciliation existante (read-only)

| Composant | Fichier | Rôle |
| --- | --- | --- |
| Read model E.2-A | `bundle_reconciliation_read_model.py` | Agrège lock, swaps batch, intent, cash residual |
| Scans anomalies | `transaction_intent_reconciliation.py` | `_scan_bundle_invest_gaps` |
| Shadow vs PE | `bundle_ledger/reconciliation.py` | Réconciliation comptable shadow |
| Cleanup ops legacy | `bundle_legacy_cleanup.py` | E.2-C zombies (batch `8486fb48`) |

Statuts read model : `completed`, `completed_with_cash_residual`, `partial_in_progress`, `reconciliation_required`, `impossible`.

Spec orchestration cible : [R4.5-E.2_BUNDLE_PARTIAL_RECONCILIATION_SPEC.md](../arquantix/R4.5-E.2_BUNDLE_PARTIAL_RECONCILIATION_SPEC.md) — finalize session unique, skip leg après retry, pas de recovery client post-session.

### 1.6 Classification gouvernance S4

[S4_PRODUCT_LOCKS_MATRIX.md](S4_PRODUCT_LOCKS_MATRIX.md) §1.1 :

> **Bundle Invest** · `bundle_invest` · ⚠️ **Legacy PE (hors outbox Phase 2)**

Coexistence documentée : `bundle_invest_lock` metadata vs `transaction_product_locks` scope `bundle` jusqu’à encapsulation L6.

---

## 2. Writers économiques actuels

| Writer | Fichier / fonction | Moment | Autorité ADR 004 |
| --- | --- | --- | --- |
| Funding PE | `bundle_funding.fund_bundle_cash_leg_from_self_trading` | Avant legs | ❌ Direct PE, hors Settlement Layer |
| Privy wallet | `lifi_swap_settlement.apply_swap_settlement` | Post-CONFIRMED leg (HTTP) | ❌ Legacy sync, pas S3b |
| PE atoms leg | `pe_settlement.apply_allocation_leg_atoms` (+ rebalance/withdraw) | Post-CONFIRMED leg | ❌ Direct |
| Cost basis | `ingest_bundle_lifi.ingest_bundle_lifi_swap_settlement` | Post-PE (try/except) | ❌ Inline, non bloquant |
| Shadow ledger | `bundle_ledger/service.record_*` | Miroir depuis PE settlement | 📋 Projection |
| Parent intent | `bundle_intent_sync.*` | Observabilité legs | 📋 Non gate |
| Transaction attempts | `dual_write` protocol `INTERNAL_BUNDLE` | Protocol trace | 📋 |

**Funding** : mouvement **comptable interne** uniquement — `direct_portfolio` → `bundle_cash_leg` ; **ledger Privy inchangé** (doc `bundle_funding.py`).

**Ordre post-confirmation leg** (`BundleLifiLegService._apply_post_confirmation`) :

1. `apply_swap_settlement` (Privy)
2. `_apply_pe_atoms_for_leg` (PE cash debit + spot credit)
3. `_ingest_bundle_cost_basis`
4. `bundle_ledger` (via pe_settlement)

---

## 3. Risques actuels

| Risque | Sévérité | Détail |
| --- | --- | --- |
| Settlement synchrone HTTP | **Haute** | Pas de retry worker ; échec mid-request → état ambigu PE/Privy |
| Double système de lock | **Haute** | Metadata lock vs S4 product locks non unifiés |
| Legs embedded vs query | **Moyenne** | Pas de FK child intent ; agrégation Controller difficile |
| Partial / zombie batch | **Haute** | Lock actif + legs pending ; E.2-B pas entièrement câblé orchestrateur |
| Cost basis silencieux | **Moyenne** | Échec ingest non bloquant → PRU incomplet |
| Bypass rail standalone | **Critique** | Tag `bundle_leg_context` manquant → swap pourrait passer S3b/Controller |
| Shadow ledger confusion | **Moyenne** | Risque de traiter shadow comme source de vérité |
| Resume client API | **Moyenne** | `POST /invest/resume` contredit doctrine E.2 (recovery post-session) |
| Pas de gate COMPLETED | **Moyenne** | Intent parent `confirmed` sans Controller parent |
| Dust / residual USDC | **Moyenne** | Buffer execution (~1 USDC) + cash leg residual — comptabilisé PE mais pas dans report canonique unique |

---

## 4. Modèle cible event-driven

### 4.0 Doctrine : Funding + Rebalance-to-target

> **Le bundle n’est pas un split proportionnel du dépôt.** C’est un moteur de rebalance vers l’allocation cible, alimenté par du funding USDC.

#### Anti-pattern legacy (à remplacer)

```text
invest_amount → split selon pe_target_allocations → N legs USDC→asset
```

Ce modèle ignore : positions spot existantes · cash leg résiduel · drift · prix de marché · seuils minimum · sur/sous-pondération globale.

#### Modèle cible

```text
1. funding USDC (trading_available → bundle_cash_leg)
2. état réel portefeuille bundle APRÈS funding
     = positions spot existantes + cash leg (incl. nouveau funding)
3. rebalance planner (fonction pure réutilisable)
     input  : portfolio_after_funding · target_allocation · prices · policies
     output : rebalance_plan_after_funding
4. bundle legs = trades nécessaires pour exécuter le plan
     (achats ET ventes · pas seulement allocation du cash entrant)
5. exécution on-chain (LI.FI) · settlement · controller leg
6. controller parent : allocation finale ≈ target · residual expliqué · drift toléré
```

#### Rebalance planner — fonction réutilisable (spec B3b)

| Cas d’usage | Input funding | Output |
| --- | --- | --- |
| **Invest** (nouveau cash) | `funding_usdc > 0` | `rebalance_plan_after_funding` |
| **Rebalance périodique** | `funding_usdc = 0` | legs drift-only |
| **Correction de drift** | optionnel micro-funding | legs minimales |
| **Withdraw / rebalance futur** (B7) | `funding_usdc < 0` ou sell-first | plan sortie + rebalance résiduel |

**Propriétés attendues** (tests purs B3b) :

- Déterministe à prix et état portfolio fixes
- Respecte `min_trade_usdc` / dust policy par instrument
- Ne double-compte pas cash déjà en bundle_cash_leg
- Tient compte des positions existantes (sur/sous-pondération)
- Produit `expected_portfolio_after_execution` + `residual_policy`
- Hash canonique `plan_hash` stable

**Gate avant runtime** : **ne pas** brancher outbox/worker/settlement bundle tant que B3b (spec + tests purs) n’est pas validé CTO — sinon on settlerait des legs générées par une logique trop simpliste.

#### 4.0.1 Discipline S4 — séparation Décision / Exécution / Settlement / Contrôle

Le succès S4/S4d ne vient pas des locks seuls, mais de la **séparation progressive** de quatre responsabilités, chacune **rejouable et auditée** :

```text
Décision     → quoi faire (plan figé · plan_hash)
Exécution    → comment le faire on-chain (swap · submit · confirm)
Settlement   → écritures autoritaires (Privy · PE · receipt)
Contrôle     → le plan a-t-il été exécuté ? (Controller · RECONCILED)
```

**Anti-pattern à éviter** (legacy Bundle) : un seul handler HTTP qui mélange funding · calcul allocations · création legs · exécution · settlement.

**Modèle cible** : une étape = un handler / un event / un receipt. Même philosophie que LI.FI standalone event-driven.

#### 4.0.2 Machine à phases parent (metadata)

Phases logiques du parent `bundle_invest` — **metadata `phase`** au début (pas de colonne DB dédiée en B3) :

```text
CREATED
   ↓  (Product Lock · snapshot initial)
FUNDED
   ↓  (B3a funding handler · bundle_funding_receipt_hash)
REBALANCE_PLAN_FROZEN
   ↓  (B3b planner · plan_hash · planner_version — gel définitif)
CHILD_LEGS_CREATED
   ↓  (B4b · 1 row child intent par leg du plan)
EXECUTING
   ↓  (quote · sign · submit on-chain)
SETTLING
   ↓  (B3c settlement handler · receipt leg)
RECONCILED
   ↓  (B5 Controller parent · terminal)
```

| Phase | Qui écrit | Receipt / hash |
| --- | --- | --- |
| `CREATED` | API / orchestrateur | — |
| `FUNDED` | `bundle_funding_handler` (B3a) | `bundle_funding_receipt_hash` |
| `REBALANCE_PLAN_FROZEN` | planner step (B4a ou handler dédié) | `plan_hash` + `planner_version` |
| `CHILD_LEGS_CREATED` | child factory (B4b) | child idempotency keys liés à `plan_hash` |
| `EXECUTING` | leg executor | swap record · tx_hash |
| `SETTLING` | `bundle_leg` settlement handler (B3c) | `settlement_receipt_hash` (leg) |
| `RECONCILED` | Controller parent (B5) | `parent_report_hash` |

Transitions **monotones** sauf abandon explicite du parent (`FAILED` · `SUPERSEDED`).

#### 4.0.3 Gel du plan — `REBALANCE_PLAN_FROZEN`

**Règle fondamentale** :

> Après `REBALANCE_PLAN_FROZEN` = **interdiction de recalculer le plan** sauf abandon explicite du parent intent.

Conséquences :

| Autorisé | Interdit |
| --- | --- |
| Exécuter la leg #N du `plan_hash` X | Recalculer portefeuille cible |
| Settlement + Controller de la leg | Recalculer les poids |
| Retry / skip leg (E.2) | Nouvelle décision d’investissement |
| Abandon parent → terminal + release lock | Re-planner mid-flight |

**Contrat child intent** :

```text
Parent
  plan_hash = X
  planner_version = v1
Child #0
  execute leg 0 of plan X
Child #1
  execute leg 1 of plan X
Child #N
  execute leg N of plan X
```

Chaque child **référence** `parent_intent_id` · `leg_index` · `plan_hash` — jamais `plan_rebalance_after_funding()` au runtime leg.

**Invariant** :

> Pour un parent intent donné, le triplet `(parent_intent_id, planner_version, plan_hash)` identifie de manière unique le plan d’investissement. Tous les child intents créés à partir de ce parent doivent référencer **exactement** ce triplet. **Aucun child intent ne peut exister sans `plan_hash`.**

**Gate B4b** : pas de child intent sans `REBALANCE_PLAN_FROZEN` + `plan_hash` présent en metadata parent.

**Controller B5** : ne se demande plus « qu’aurait-on dû faire ? » — il vérifie « le plan X a-t-il été exécuté ? » (même philosophie que Controller LI.FI).

#### 4.0.4 Plan versioning (`planner_version`)

Le `plan_hash` seul ne suffit pas pour l’audit historique. Tout plan gelé inclut :

```json
{
  "planner_version": "v1",
  "plan_hash": "sha256:...",
  "prices_used": { "...": "..." },
  "rebalance_plan_after_funding": { "...": "..." },
  "expected_portfolio_after_execution": { "...": "..." },
  "frozen_at": "2026-06-08T12:00:00Z"
}
```

| Champ | Rôle |
| --- | --- |
| `planner_version` | Version de la logique planner (drift · tolérances · min_trade · residual) |
| `plan_hash` | Hash canonique du plan seul (indépendant du snapshot complet) |
| `frozen_at` | Horodatage du gel — immuable |

**Pourquoi** : dans 18 mois, drift · seuils · gestion cash résiduel · ventes automatiques évolueront. Pouvoir dire « ce bundle a été généré avec Planner v1 » vs v2 est indispensable pour audit · recalculs historiques · rebalancing périodique · withdraw partiel · multi-wallet · vaults · RWA (B7+).

**Règle** : `plan_hash` est calculé sur le contenu canonique du plan **à une `planner_version` donnée**. Changer la version planner → nouveau hash même état portfolio.

#### 4.0.5 Scope B3c minimal (discipline S4d)

B3c n’est **plus un chantier d’architecture** — c’est un **chantier d’exécution**. L’architecture est en place (B1–B3a · freeze · planner_version). B3c prouve le **rail** Parent → Child → Swap → Settlement, pas encore le Bundle complet.

Reproduire la discipline S4d : **encore plus petit que le scope initial** — cas simple jusqu’au bout.

**Flow B3c v1 — objectif** :

```text
FUNDED
   ↓
REBALANCE_PLAN_FROZEN
   ↓
child #0 (leg_index=0)
   ↓
swap USDC → AAVE (buy leg · Base uniquement)
   ↓
settlement (handler bundle_leg · idempotent)
   ↓
child SETTLED / receipt leg
```

**B3c v1 — uniquement** :

| Dimension | Scope B3c v1 | Hors scope B3c v1 |
| --- | --- | --- |
| Parent | 1 parent intent | N parents parallèles |
| Child | 1 child intent | 2+ child intents |
| Leg | 1 buy leg (`leg_index=0`) | sell leg · rebalance complet · N legs |
| Paire | **USDC → AAVE** | UNI · ETH · multi-asset |
| Chain | **Base uniquement** | multi-chain |
| Swap | 1 swap LI.FI interne | allocation multiple |
| Settlement | 1 settlement idempotent | partial fill orchestration |
| Controller | ❌ | Controller leg (B5a) · Controller parent (B5b) |
| Runtime | Handler isolé · flag OFF | Worker / outbox branché |
| Concurrence | Séquentiel · 1 child | 3 childs en parallèle |

**But B3c** : prouver le rail — **pas** prouver le Bundle multi-legs.

**Échelle S4d (ne pas sauter d’étapes)** :

```text
1 child  → validation → GO
2 childs → validation → GO
N childs → validation → GO
```

Créer 3 childs + 3 swaps + 3 settlements + 1 parent dès B3c réintroduit immédiatement : concurrence · ordering · retry · partial completion · parent state machine. **Trop tôt.**

**Prérequis B3c** : doctrine `REBALANCE_PLAN_FROZEN` (§4.0.3) · B3a mergé · **deploy neutre validé** · flag `BUNDLE_FUNDING_HANDLER_ENABLED` OFF.

**Frontière B3a vs B3c** :

```text
B3a : PE interne uniquement (trading_available → bundle_cash_leg)
B3c : bundle_cash → swap LI.FI → wallet → settlement → PE atom → cost basis
```

#### 4.0.6 Doctrine B3c — child = mini LI.FI standalone

Le child intent bundle leg est traité comme un **mini LI.FI standalone** : même discipline settlement · receipt · idempotence — **sans** regarder le parent au moment du settlement.

```text
Parent Bundle (bundle_invest)
   │
   └── Child Intent (product_type = bundle_leg)
          ├── parent_intent_id
          ├── plan_hash          ← triplet invariant §4.0.3
          ├── planner_version
          ├── leg_index
          └── swap LI.FI interne (is_bundle_internal_swap=true)
```

| Couche | Question | Scope |
| --- | --- | --- |
| **Settlement B3c** | « Cette leg a-t-elle été correctement exécutée ? » | Child seul · receipt leg · PE atom · cost basis leg |
| **Controller B5** (plus tard) | « Toutes les legs du plan X ont-elles été exécutées ? » | Parent · agrégation child reports · plan fidelity |

**Règle fondamentale** : le settlement handler **ne doit jamais regarder le parent**. Il settle une leg comme le ferait S3b pour un swap standalone — avec `product_type=bundle_leg` et tagging `bundle_leg_context`.

**Interdit en B3c** : logique parent dans le settlement (re-plan · agrégation · partial parent · release lock parent).

### 4.1 Principes directeurs

1. **Bundle = orchestrateur multi-transactions**, pas N clones du handler LI.FI standalone.
2. **Séparation stricte** Décision → Exécution → Settlement → Contrôle (§4.0.1) — jamais mélangé dans un handler HTTP.
3. **Décision unique** : plan gelé à `REBALANCE_PLAN_FROZEN` · legs n’exécutent que · ne décident pas (§4.0.3).
4. **Réutiliser la plomberie** outbox / worker / Settlement Layer **via router** `product_type` — pas réinventer ledger.
5. **`is_bundle_internal_swap=true`** reste la frontière ; legs bundle **ne passent jamais** par `lifi_swap_controller` v1.
6. **Intent parent** porte le cycle de vie global ; **chaque leg** a son propre pipeline settlement + controller leg (ou step interne équivalent).
7. **Controller parent** = premier cas ADR 003 multi-leg — vérifie exécution du `plan_hash`, pas re-décision.
8. **Migration progressive** : dual-run sous flag ; LI.FI standalone **gelé** ; pas de régression prod pilote · discipline S4d (cas simple d’abord).

### 4.2 Architecture cible — Bundle Invest

```text
1. User confirme investissement bundle
2. Créer parent intent :
     product_type = bundle_invest
     operation_type = invest
     bundle_execution_group_id = batch_id (correlation)
3. Acquire Product Lock (S4) :
     asset = USDC (entry)
     scope = bundle
     amount = montant total investi
     intent_id = parent
4. Snapshot comptable (metadata parent) — voir [§11](#11-snapshot-comptable-requis) :
     portfolio_before · funding_usdc · portfolio_after_funding
     target_allocation · rebalance_plan_after_funding
     expected_portfolio_after_execution · prices_used · plan_hash
5. Funding interne (event / settlement step — B3a) :
     trading_available → bundle_cash_leg
     mouvement PE interne — pas swap externe
     phase parent : FUNDED · bundle_funding_receipt_hash
6. Rebalance planner (B3b — après funding) :
     portfolio_after_funding + target → rebalance_plan_after_funding
     planner_version · plan_hash · prices_used · expected_portfolio_after_execution
7. Gel du plan (gate obligatoire — §4.0.3) :
     phase parent : REBALANCE_PLAN_FROZEN
     interdiction de re-planner sauf abandon parent
8. Créer child intents depuis le plan gelé (B4b) :
     phase parent : CHILD_LEGS_CREATED
     chaque child = « exécuter leg #N du plan_hash X » — pas de décision locale
9. Pour chaque leg (séquentiel en B3c pilote · parallèle contrôlé plus tard) :
     a. Enregistrer leg (child intent OU leg state machine)
     b. Quote LI.FI (bundle handler dédié)
     c. Submit on-chain
     d. Outbox : bundle_leg.settle (PAS intent.settle standalone)
     e. Settlement Layer handler bundle_leg → Privy + receipt
     f. PE atoms leg (via settlement handler — pas HTTP direct)
     g. Cost basis bundle-scoped
     h. Controller leg → RECONCILED (bundle_leg)
10. Controller parent :
     - legs exécutées selon rebalance_plan (pas seulement count)
     - allocation finale ≈ target (tolérance drift)
     - residual USDC expliqué · drift résiduel dans tolérance
     - aucun double spend
     - parent report hash = snapshot + child hashes + rebalance_plan + residual
     - aucun double spend USDC
     - cash residual / dust documenté
     - agrégation report hash multi-leg
11. Release Product Lock parent
12. Phase parent finale :
     RECONCILED | PARTIALLY_FILLED | FAILED | RETRYABLE
     (mapping sémantique E.2 : completed_full / completed_partial / failed_no_allocation)
```

### 4.3 Nouvelles notions à introduire

| Notion | Définition proposée |
| --- | --- |
| **Parent intent** | `bundle_invest` · porte lock, snapshot, plan, statut global, `bundle_execution_group_id` |
| **Bundle execution group** | Correlation `batch_id` · lie parent, legs, swaps, locks, reports |
| **Bundle leg** | Unité économique : 1 swap LI.FI interne · funding source = bundle cash leg |
| **Child intent** (approche A) | Row `transaction_intents` enfant · `parent_intent_id` · `product_type=bundle_leg` |
| **Leg state** (approche B) | Entité logique / table dédiée · machine à états par leg sous parent |
| **Controller leg** | Réconciliation 1 débit + 1 crédit par swap bundle · exclut checks standalone |
| **Controller parent** | Agrégateur multi-leg · allocation · residual · lock release gate |

### 4.4 Events outbox cibles (à définir — pas implémenter)

| Event | Product types | Rôle |
| --- | --- | --- |
| `intent.created` | `bundle_invest` | Worker bundle : funding + plan legs |
| `bundle.fund` | parent | Step funding PE interne |
| `bundle_leg.created` | leg | Quote / queue signature |
| `bundle_leg.settle` | leg | Settlement handler bundle (≠ S3b standalone) |
| `bundle_leg.reconcile` | leg | Controller leg |
| `intent.reconcile` | parent | Controller parent |
| `bundle.finalize` | parent | Terminalisation batch + release lock |

Router Settlement Layer (post-L5 S4) : `product_type` + `operation_type` → handler — **pas** branchement direct `settlement/lifi_ledger.py` standalone pour legs bundle.

---

## 5. Parent / child intent model — comparaison A vs B

### Approche A — Child `TransactionIntent` par leg

**Modèle** :

```text
transaction_intents (parent, bundle_invest)
  ├── child intent leg_1 (product_type=bundle_leg, parent_intent_id, linked swap)
  ├── child intent leg_2
  └── child intent leg_3
```

| Critère | Évaluation |
| --- | --- |
| **Avantages** | Réutilise infra intent/outbox/phases existante ; Controller leg ≈ Controller standalone adapté ; queries SQL simples (`parent_intent_id`) ; aligné ADR 001 « intent pilote » ; trace transitions par leg |
| **Risques** | Explosion rows intents ; confusion UI si child visible ; nécessite `parent_intent_id` + enums `bundle_leg` |
| **Complexité** | Moyenne — extension schéma intent |
| **Product Locks** | Lock parent sur USDC total ; legs consomment cash leg PE (sous-lock logique ou dérivation snapshot) |
| **Controller** | Leg controller indépendant ; parent agrège `child.current_phase` |
| **Migration** | Dual-write : embedded legs metadata + child rows ; read model lit les deux puis bascule |

### Approche B — Parent intent + leg state machine interne

**Modèle** :

```text
transaction_intents (parent)
  metadata_json.legs[]  OU  table bundle_leg_executions
    state: planned | quoted | submitted | ledger_settled | reconciled | skipped_failed
```

| Critère | Évaluation |
| --- | --- |
| **Avantages** | Proche code actuel ; moins de rows intent ; UX parent unique |
| **Risques** | Legs restent second-class pour outbox/worker ; agrégation phases ad hoc ; répète dette actuelle (`recompute_bundle_parent_status`) |
| **Complexité** | Faible à court terme · **haute** long terme (Controller, retry, idempotence) |
| **Product Locks** | Compatible mais lock release couplé à logique metadata |
| **Controller** | Parent doit parser legs embedded — pas de réutilisation Controller leg standalone |
| **Migration** | Minimale — **dette structurelle** reportée |

### Recommandation

**Approche A (child intents)** pour le rail event-driven cible.

Raisons :

1. ADR 001 exige intent traçable **par écriture économique** — chaque leg = swap settleable.
2. Controller leg réutilise le pattern v1.2 prouvé (adapté `product_type=bundle_leg`).
3. Outbox/worker idempotent par `intent_id` leg — impossible proprement avec JSON array seul.
4. Lombard (L8) suivra le même pattern parent + steps — Bundle pose le précédent.

**Compromis migration** : Phase 0 dual-run — child intents créés en parallèle du array metadata jusqu’à bascule read paths.

Champ proposé parent :

```json
{
  "bundle_execution_group_id": "<batch_id>",
  "rebalance_plan_after_funding": { "legs": [...], "skipped": [...] },
  "child_intent_ids": ["uuid", "..."],
  "funding_usdc": "...",
  "plan_hash": "sha256:...",
  "snapshot_hash": "sha256:..."
}
```

---

## 6. Lock strategy

### 6.1 État actuel

- Lock : `pe_portfolios.metadata.bundle_invest_lock` (`bundle_invest_lock.py`)
- Statuts actifs : `pending_signature`, `signature_requested`, `submitted`, `partial_pending`, …
- TTL : `BUNDLE_INVEST_LOCK_TTL_MINUTES` (default 120)
- **Aucun** wiring `transaction_product_locks` dans le code bundle runtime

### 6.2 Cible S4

| Lock | Scope | Asset | Montant | Intent |
| --- | --- | --- | --- | --- |
| Parent invest | `bundle` | USDC (entry) | Montant investi total | Parent `bundle_invest` |

**Règles** :

1. Acquire lock **avant** funding PE (même ordre que LI.FI standalone S4).
2. Snapshot metadata parent (post-lock · voir §11) :
   - `portfolio_before` · `funding_usdc` · `portfolio_after_funding`
   - `target_allocation` · **`rebalance_plan_after_funding`** (remplace `planned_allocations` split-dépôt)
   - `expected_portfolio_after_execution` · `prices_used` · `plan_hash`
   - `execution_buffer_usdc` · `residual_policy`
   - ⚠️ B2/B2b actuels : snapshot intermédiaire `planned_allocations` (preview poids) — **à migrer** vers rebalance plan en B3b+
3. **Pas de lock LI.FI standalone** sur legs — consommation via **bundle cash leg** PE, pas wallet trading.
4. Release lock **uniquement** après Controller parent terminal (ou échec terminal explicite `failed_no_allocation`).
5. Coexistence temporaire metadata lock + S4 lock pendant migration (flag) — puis deprecation metadata lock.

**Conflits** (matrice S4) : swap standalone USDC · vault · Lombard → 409 si lock bundle actif.

---

## 7. Settlement strategy

### 7.1 Séparation handlers

| Handler | Périmètre | Writer Privy | Writer PE leg |
| --- | --- | --- | --- |
| `settlement/lifi_ledger.py` (S3b) | `lifi_swap` standalone | ✅ seul (prod gelé) | N/A wallet |
| **`settlement/bundle_leg.py`** (nouveau, futur) | `bundle_leg` / internal swap | ✅ via Settlement Layer | ✅ atoms bundle via handler |
| **`settlement/bundle_funding.py`** (nouveau, futur) | Funding step parent | ❌ (PE only) | ✅ direct → cash leg |

**Interdit** : appeler `apply_swap_settlement` depuis `BundleLifiLegService.submit_leg_tx` HTTP une fois migré.

### 7.2 Pipeline par leg (cible)

```text
ONCHAIN_CONFIRMED
  → outbox bundle_leg.settle
  → worker
  → Settlement handler bundle_leg :
       idempotency lifi-swap:{swap_id}:debit|:credit (réutiliser clés)
       Privy wallet movements (bundle wallet context)
       settlement_receipt_hash on child intent
  → phase child : LEDGER_SETTLED
  → outbox bundle_leg.reconcile
  → Controller leg (bundle_leg_controller)
  → phase child : RECONCILED
  → signal parent orchestrator (all legs terminal?)
```

### 7.3 Funding step (pas swap externe)

```text
Parent FUNDING_REQUESTED
  → settlement/bundle_funding handler (B3a)
  → debit pe.direct_overlay (trading_available)
  → credit pe.bundle_cash_leg
  → audit pe + optional bundle_ledger mirror
  → parent phase : FUNDED
  → rebalance planner (B3b) : portfolio_after_funding → rebalance_plan
  → enqueue child leg creation depuis rebalance_plan (B4b)
```

**Invariant** : funding ne touche **pas** Privy — identique au modèle actuel Vancelian.

### 7.4 Idempotence

Réutiliser :

- `swap_settlement_already_applied` / clés `lifi-swap:%`
- `_pe_atoms_already_applied` / audit `bundle_pe_atoms_applied`
- `ingest_bundle_lifi` idempotent par swap_id

Ajouter :

- `settlement_receipt_hash` par child intent (comme standalone)
- `bundle_funding_receipt_hash` sur parent

---

## 8. Controller strategy

### 8.1 Ne pas réutiliser Controller standalone tel quel

`lifi_swap_controller` v1.2 :

- Périmètre `lifi_swap` post `LEDGER_SETTLED`
- Rejette `is_bundle_internal_swap`

Les legs bundle ont des **invariants différents** :

- Source débit = **bundle cash leg** (PE), pas trading wallet snapshot
- Contexte parent requis (batch, allocation cible)
- Pas de comparaison PE snapshot trading vs wallet Privy (même problème v1.1 mais scope différent)

### 8.2 Controller leg (bundle_leg)

**Entrée** : child intent `bundle_leg` · phase `LEDGER_SETTLED` · swap taggé `bundle_execution=true`.

**Checks** (inspirés v1.2) :

| Check | Détail |
| --- | --- |
| Jambes ledger | 1 débit USDC + 1 crédit asset · tx_hash · chain-aware |
| Montants | Tolérance slippage bundle (config existante) |
| PE atoms | Cohérence cash leg debit + spot credit |
| Parent link | `parent_intent_id` + `batch_id` match |
| Exclusions | Pas standalone ; pas double crédit |

**Outcome** : `RECONCILED` | `RECONCILIATION_*` · report hash par leg.

**Balance check** : comparer **bundle cash leg PE** avant/après leg (pas wallet trading) — ou warning-only phase 1.

### 8.3 Controller parent (premier cas multi-leg ADR 003)

**Entrée** : parent `bundle_invest` · toutes legs terminal (`RECONCILED` | `skipped_failed` | `failed`).

**Checks agrégés** (rebalance-to-target) :

| Check | Détail |
| --- | --- |
| Plan fidelity | Legs exécutées correspondent au `rebalance_plan_after_funding` (asset · direction · ordre de grandeur) |
| Couverture legs | N planned (plan) vs N terminal (enfants) |
| Allocation finale | Poids spot post-exécution ≈ `target_allocation` (tolérance `allocation_drift_bps`) |
| Drift résiduel | Écart final documenté · dans tolérance ou warning |
| Double spend | Aucun double débit USDC · somme legs ≤ budget plan + buffer |
| Cash residual | `bundle_cash_leg` restant expliqué par `residual_policy` (buffer · dust · skipped legs) |
| Lock | Product lock actif → refuse release until OK |
| Enfants | Aucune leg `RECONCILIATION_RETRYABLE_FAILURE` sans policy |
| Report | `parent_report_hash` = `plan_hash` + parent snapshot + child report hashes + residual |

**Outcomes parent** :

| Outcome | Condition |
| --- | --- |
| `RECONCILED` (full) | Toutes legs RECONCILED · allocation OK · residual ≤ buffer policy |
| `PARTIALLY_FILLED` | ≥1 leg RECONCILED · ≥1 skipped_failed · finalize E.2 |
| `FAILED` | Aucune leg RECONCILED · funding OK ou rollback policy |
| `RETRYABLE` | Leg(s) en retryable · infra ambiguë |

**Release lock** : uniquement sur outcomes terminal parent validés.

### 8.4 Ordre d’implémentation Controller

1. **Spec + tests** Controller leg (sans prod)
2. **Spec + tests** Controller parent (agrégation mock)
3. Wiring worker `bundle_leg.reconcile` puis `intent.reconcile` parent
4. **Pas avant** settlement par leg event-driven stable

---

## 9. Failure / retry / partial fill strategy

### 9.1 Doctrine E.2 (à conserver)

Source : [R4.5-E.2_BUNDLE_PARTIAL_RECONCILIATION_SPEC.md](../arquantix/R4.5-E.2_BUNDLE_PARTIAL_RECONCILIATION_SPEC.md)

| Règle | Event-driven mapping |
| --- | --- |
| Retry **interne** 1× par leg (même session) | Worker retry leg · pas API client resume |
| Skip leg après retry KO | Child → `skipped_failed` · continue orchestrator |
| Finalize obligatoire | Event `bundle.finalize` · lock terminal |
| Cash residual visible | PE cash leg · report parent |
| Pas rollback économique | Legs confirmées conservées |
| `reconciliation_required` | Infra ambiguë seulement — pas nominal partial |

### 9.2 Statuts terminaux cibles

| Statut canon | Condition |
| --- | --- |
| `completed_full_allocation` | Toutes legs RECONCILED |
| `completed_partial_allocation` | Mix RECONCILED + skipped_failed · cash residual |
| `failed_no_allocation` | 0 leg RECONCILED |
| `reconciliation_required` | Divergence PE/LI.FI/lock non classifiable |

Mapping phases parent :

```text
RECONCILED_FULL      ↔ completed_full_allocation
PARTIALLY_FILLED     ↔ completed_partial_allocation
FAILED               ↔ failed_no_allocation
RECONCILIATION_*     ↔ reconciliation_required (infra)
```

### 9.3 Dust / slippage / leftover USDC

| Mécanisme | Actuel | Cible |
| --- | --- | --- |
| Buffer exécution | `BUNDLE_ALLOC_EXECUTION_BUFFER_USDC` (~1 USDC) | Conservé · exclu des legs |
| Cash residual post partial | Reste en cash leg PE | Report parent `cash_residual_usdc` |
| Slippage leg | Tolérance validation bundle | Controller leg tolerance |
| Shadow ledger | Miroir | Projection only · pas gate |

**Comptabilisation parent Controller** (rebalance-to-target) :

```text
portfolio_value_after_funding = sum(positions × prices) + bundle_cash
rebalance_plan = planner(portfolio_after_funding, target, prices)
executed_trades = sum(reconciled legs vs plan)
residual_usdc = bundle_cash_leg.available
invariant: allocation_final ≈ target (± drift_tolerance)
         residual expliqué par residual_policy (buffer · min_trade dust · skipped)
```

Warnings non bloquants si tolérance : `bundle_residual_above_buffer`, `allocation_drift_bps`.

### 9.4 Failures partielles — jamais silencieuses

| Scénario | Comportement cible |
| --- | --- |
| Leg submit fail | Child → retryable ou failed · parent reste IN_PROGRESS |
| Leg settle fail worker | Outbox retry · child RECONCILIATION_RETRYABLE |
| Leg confirmée PE fail | Terminal child · parent partial · alert |
| Funding fail | Parent FAILED · lock release · no legs |
| Parent finalize sans legs terminal | **Interdit** — orchestrator gate |
| Zombie lock | TTL + worker sweep · read model alert |

---

## 10. Roadmap PR par PR

> **Principe** : design d’abord · LI.FI standalone gelé · chaque PR déployable · flags OFF par défaut · pas de Controller parent avant settlement leg stable.

### Phase B0 — Design & gouvernance (cette livraison)

| PR | Scope | Runtime |
| --- | --- | --- |
| **B0** | Ce document + review CTO | ❌ Doc only |

### Phase B1 — Modèle & ADR

| PR | Scope | Runtime | Statut |
| --- | --- | --- | --- |
| **B1** | Migration additive `parent_intent_id` · `intent_role` · `leg_index` · `bundle_execution_id` · enums `bundle_leg` · helpers lecture | ❌ Table + modèle only | **✅ Mergée** (`176` · merge `f8cd1c58` · TD `:149`) |

**B1 livré (schema)** :

| Colonne | Type | Usage |
| --- | --- | --- |
| `parent_intent_id` | UUID FK nullable | Enfant → parent |
| `intent_role` | `parent` / `child` nullable | Standalone reste null |
| `leg_index` | int nullable | Ordre leg sous parent |
| `bundle_execution_id` | UUID nullable | Correlation batch / groupe d’exécution |

Index : `ix_transaction_intents_parent_intent_id` · `ix_transaction_intents_bundle_execution_id` · `uq_transaction_intents_parent_leg_index` (partial unique).

Enums : `IntentProductType.BUNDLE_LEG` · `IntentRole.PARENT` / `CHILD` · `IntentOperationType.BUNDLE_LEG` (existant, réutilisé).

Helpers (lecture seule) : `bundle_parent_child_repository.py` — `find_children` · `find_parent` · `find_bundle_leg` · `find_by_bundle_execution_id`.

**Non modifié en B1** :

- Legacy Bundle (`bundle_intent_sync` · legs embedded metadata · orchestrateur PE)
- Aucune création runtime de child intents en prod
- Rail LI.FI standalone · Product Locks · settlement · Controller

| PR | Scope | Runtime |
| --- | --- | --- |
| **B1b** | Spec events outbox bundle · phases parent/child · diagrammes | Doc only |

### Phase B2 — Product Locks Bundle

| PR | Scope | Runtime | Statut |
| --- | --- | --- | --- |
| **B2** | `bundle_product_locks.py` · acquire/release parent scope `bundle` · snapshot PE · flag + allowlist | ❌ Module only · **non branché legacy** | **✅ Mergée** (`176` · merge `68e3c062` · PR `#53` · deploy neutre TD `:150`) |
| **B2b** | `bundle_dual_run_locks.py` · legacy puis S4 · rollback failure · flag `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED` | ❌ Dual-run only · **pas migration finale** | **✅ Mergée** (merge `f9d57baa` · PR `#54`) |

**B2 livré (module)** :

| Fonction | Rôle |
| --- | --- |
| `acquire_bundle_parent_lock` | Lock S4 `scope=bundle` · `asset=USDC` · `intent_id=parent` |
| `release_bundle_parent_lock` | Release slot bundle parent |
| `build_bundle_parent_snapshot` | Snapshot v1 intermédiaire (trading · bundle_cash · bundle_position · `planned_allocations` preview · buffer) — **à migrer v2 rebalance plan (B3b)** |

Gating : `TRANSACTION_PRODUCT_LOCKS_ENABLED` **+** `TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS` (fail-closed L5a). Flag OFF ou hors allowlist → **no-op strict**.

**Non modifié en B2** :

- `pe_portfolios.metadata.bundle_invest_lock` (legacy intact)
- Orchestrateur Bundle legacy · child intents · settlement · Controller · PE writers

### Phase B2b — Dual-run locks (legacy + S4)

**Objectif** : prouver la coexistence sans lock zombie — le plus critique est le failure path (legacy acquis, S4 échoue → rollback legacy).

| Flag | Défaut | Effet |
| --- | --- | --- |
| `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED` | `false` | OFF → legacy seul (comportement prod inchangé) |
| `TRANSACTION_PRODUCT_LOCKS_ENABLED` + allowlist | OFF | S4 no-op même si dual-run ON |

**Ordre dual-run (flag ON + allowlist OK)** :

1. `acquire_invest_lock` (legacy metadata) — inchangé
2. `ensure_bundle_parent_intent`
3. `try_acquire_s4_after_legacy_invest_lock` → `acquire_bundle_parent_lock` scope `bundle`
4. Échec S4 → `release_invest_lock(terminal_status=failed)` (anti-zombie)
5. Terminal → `release_bundle_dual_run_locks` (legacy clear/failed + S4 release)

**Conflits documentés** :

- Deux `bundle_invest` même wallet/USDC/scope `bundle` → conflit S4 (409)
- `bundle_invest` + swap standalone USDC : scopes **distincts** (`bundle` vs `trading_available`) — pas de blocage inter-produit aujourd'hui ; stratégie globale source USDC = futur (hors B2b)

**B2b n'est pas** la migration finale metadata → S4 (cf. B6b). Dual-run staging uniquement — **ne pas activer en prod**.

Prérequis S4 : L1–L5 merged (table, engine, snapshot, middleware, router) — cf. [S4_IMPLEMENTATION_ROADMAP.md](S4_IMPLEMENTATION_ROADMAP.md) L6.

### Phase B3 — Funding + Rebalance planner + Settlement (réordonné)

> **Pause micro-étape** : formaliser **B3b rebalance planner** (spec + tests purs) **avant** handlers settlement runtime — éviter de settler des legs issues du split-dépôt legacy.

| PR | Scope | Runtime | Statut |
| --- | --- | --- | --- |
| **B3b** | `rebalance_planner.py` · `plan_rebalance_after_funding()` · tests purs rebalance-to-target | ❌ Pure function only | **✅ Mergée** (PR `#55`) |
| **B3a** | `bundle_funding_handler.py` · `settle_bundle_funding_idempotently()` · trading_available → bundle_cash · phase `FUNDED` | Flag OFF (`BUNDLE_FUNDING_HANDLER_ENABLED`) | **✅ Mergée** (PR `#56`) |
| **B3c** | Handler `bundle_leg` settlement · child = mini LI.FI · USDC→AAVE Base · idempotence | Flag OFF | **🟡 Prochaine** — §4.0.5 · §4.0.6 |
| **B3d** | PE atoms + cost basis **via handlers only** · retire writers HTTP | Flag OFF | ⏸ **bloqué avant B3b merge** |

**B3b livrable attendu** :

| Artefact | Contenu |
| --- | --- |
| `rebalance_planner.py` | `plan_rebalance_after_funding(portfolio_before, funding_usdc, portfolio_after_funding, target, prices, policies) → RebalancePlan` |
| Types | `PortfolioSnapshot` · `TargetAllocation` · `RebalanceLeg` · `RebalancePlan` · `ResidualPolicy` |
| Tests purs | ≥ invest nouveau cash · rebalance drift-only · positions existantes · seuils min · hash stable |
| Doc | Ce document §4.0 + §11 snapshot migré |

**Ordre GO** : B3b ✅ → B3a merge + deploy neutre → **B3c scope minimal** (§4.0.5) → B3d PE writers → B4.

### Phase B4 — Outbox & worker Bundle

| PR | Scope | Runtime |
| --- | --- | --- |
| **B4a** | Events `bundle.fund` · worker route funding → `FUNDED` | Flag OFF |
| **B4b** | **Child intent creation depuis `rebalance_plan`** · pas depuis split-dépôt | Flag OFF |
| **B4c** | Events `bundle_leg.settle` · orchestration loop parent | Flag OFF |
| **B4d** | Finalize `bundle.finalize` · E.2 terminal statuses | Flag OFF |

### Phase B5 — Controller Bundle

| PR | Scope | Runtime |
| --- | --- | --- |
| **B5a** | Controller **leg** spec + tests · `bundle_leg_controller.py` | No prod |
| **B5b** | Controller **parent** spec + tests · vérifie rebalance_plan fidelity + allocation finale + residual | No prod |
| **B5c** | Worker `bundle_leg.reconcile` + `intent.reconcile` parent · manual test 1 bundle pilote | Pilot only |

### Phase B6 — Migration & deprecation

| PR | Scope | Runtime |
| --- | --- | --- |
| **B6a** | Dual-run : legacy HTTP path + event path (flag) | Staging |
| **B6b** | Retire `submit-tx` settlement sync · deprecate metadata lock | Prod Go |
| **B6c** | Retire `POST /invest/resume` client · orchestrator internal retry only | Prod Go |

### Phase B7 — Rebalance & Withdraw

| PR | Scope |
| --- | --- |
| **B7** | `bundle_withdraw` + rebalance périodique · **réutilise le même rebalance planner** (§4.0) |

### Dépendances externes

```mermaid
flowchart TD
  B2b[B2b Dual-run Locks DONE] --> B3b[B3b Rebalance Planner Spec]
  B3b --> B3a[B3a bundle_funding handler]
  B3b --> B4b[B4b Child legs from plan]
  B3a --> B3c[B3c bundle_leg settlement]
  B3c --> B3d[B3d PE writers via handlers]
  S4L5[S4 L5 Settlement Router] --> B3a
  B1[B1 Parent/Child Model] --> B4[B4 Outbox Worker]
  B2[B2 Product Locks] --> B4
  B3d --> B4
  B4 --> B5[B5 Controller leg + parent]
  B5 --> B6[B6 Migration Prod]
  LI FI[LI.FI Standalone FROZEN] -.->|no regression| B3c
```

---

## 11. Snapshot comptable requis

Snapshot parent — **cible rebalance-to-target** (remplace `planned_allocations` split-dépôt) :

```json
{
  "version": "bundle-invest-v2-rebalance",
  "source": "pe",
  "portfolio_before": {
    "bundle_cash": { "USDC": "5.00" },
    "bundle_position": { "CBBTC": "0.001", "CBETH": "0.02" },
    "total_value_usdc": "150.00"
  },
  "funding_usdc": "100.00",
  "portfolio_after_funding": {
    "bundle_cash": { "USDC": "105.00" },
    "bundle_position": { "CBBTC": "0.001", "CBETH": "0.02" },
    "total_value_usdc": "250.00"
  },
  "target_allocation": [
    { "asset": "CBBTC", "weight_bps": 4000 },
    { "asset": "CBETH", "weight_bps": 3500 },
    { "asset": "AAVE", "weight_bps": 2500 }
  ],
  "rebalance_plan_after_funding": {
    "legs": [
      { "leg_index": 0, "direction": "buy", "asset": "AAVE", "notional_usdc": "62.50", "reason": "underweight" },
      { "leg_index": 1, "direction": "buy", "asset": "CBBTC", "notional_usdc": "18.00", "reason": "underweight" }
    ],
    "skipped": [
      { "asset": "CBETH", "reason": "within_drift_tolerance" }
    ]
  },
  "expected_portfolio_after_execution": {
    "bundle_cash": { "USDC": "24.50" },
    "bundle_position": { "CBBTC": "0.0012", "CBETH": "0.02", "AAVE": "0.5" },
    "weights_bps": { "CBBTC": 3980, "CBETH": 3520, "AAVE": 2500 }
  },
  "prices_used": {
    "CBBTC": "95000.00",
    "CBETH": "3200.00",
    "AAVE": "125.00",
    "USDC": "1.00"
  },
  "execution_buffer_usdc": "1.00",
  "residual_policy": {
    "buffer_reserved_usdc": "1.00",
    "min_trade_usdc": "5.00",
    "dust_retained_in_cash": true
  },
  "planner_version": "v1",
  "plan_hash": "sha256:<canonical rebalance plan>",
  "frozen_at": "2026-06-08T12:00:00.000Z",
  "phase": "REBALANCE_PLAN_FROZEN",
  "balance_snapshot_hash": "sha256:<full snapshot canonical>"
}
```

**Champs obligatoires** :

| Champ | Rôle |
| --- | --- |
| `portfolio_before` | État PE bundle avant funding (cash + positions) |
| `funding_usdc` | Montant transféré trading → bundle_cash |
| `portfolio_after_funding` | État après funding — **input planner** |
| `target_allocation` | `pe_target_allocations` figées au plan |
| `rebalance_plan_after_funding` | **Source de vérité des legs** — remplace split-dépôt |
| `expected_portfolio_after_execution` | Projection post-plan (Controller drift check) |
| `prices_used` | Prix au moment du plan (audit · reproductibilité) |
| `planner_version` | Version logique planner (audit historique · §4.0.4) |
| `plan_hash` | Hash canonique du plan seul — **gelé** à `REBALANCE_PLAN_FROZEN` |
| `frozen_at` | Horodatage gel — immuable après freeze |
| `phase` | Phase parent metadata (`REBALANCE_PLAN_FROZEN` avant child creation) |
| `execution_buffer_usdc` | Buffer non alloué aux legs |
| `residual_policy` | Règles dust · min_trade · cash retained |

**Migration snapshot** :

| Version | Statut | Contenu |
| --- | --- | --- |
| `bundle-invest-v1` (B2/B2b) | Intermédiaire prod | `planned_allocations` preview poids · pas rebalance global |
| `bundle-invest-v2-rebalance` (B3b+) | Cible | `rebalance_plan_after_funding` complet |

**Usage** :

- Product Lock release gate (B2/B2b → B3b+)
- Controller parent : plan fidelity + allocation finale + residual
- Debug partial fill / drift
- **Ne pas** comparer trading snapshot vs wallet Privy (leçon Controller v1.2)

---

## 12. Interdictions (rappel)

- ❌ Ne pas modifier B2b (mergé · flag OFF prod)
- ❌ Ne pas activer `BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED` en prod sans plan staging
- ❌ Aucun changement LI.FI standalone (S3b, Controller v1.2, flags pilote)
- ❌ **Ne pas démarrer runtime Bundle event-driven** (outbox · settlement · child legs) avant **B3b rebalance planner** spec + tests purs validés CTO
- ❌ Ne pas settler des legs issues du split-dépôt legacy comme modèle cible
- ❌ Aucun branchement worker bundle sans Go explicite
- ❌ Ne pas traiter Bundle comme N× handler `reconcile_lifi_swap_intent`
- ❌ Ne pas commencer Controller parent avant settlement leg stable + rebalance plan
- ❌ **Ne pas re-planner** après `REBALANCE_PLAN_FROZEN` (sauf abandon parent explicite)
- ❌ **Ne pas laisser un child intent** recalculer portefeuille · poids · ou décision d’investissement
- ❌ **Ne pas démarrer B3c** avec N-legs / parallèle / UNI·ETH / multi-chain / Controller — rail minimal §4.0.5 d’abord
- ❌ **Ne pas faire regarder le parent** au settlement leg (§4.0.6) — B5 agrège plus tard
- ❌ **Ne pas sauter l’échelle S4d** (1 child → 2 → N) — pas 3 childs parallèles en B3c v1
- ❌ Ne pas mélanger funding · plan · legs · settlement dans un seul handler HTTP

---

## 13. Références

| Document | Rôle |
| --- | --- |
| [S3_CONTROLLER_LIFI_SWAP_V1.md](S3_CONTROLLER_LIFI_SWAP_V1.md) | Controller standalone référence |
| [GO_S3_CONTROLLER_V1_2_MANUAL_TEST_REPORT.md](GO_S3_CONTROLLER_V1_2_MANUAL_TEST_REPORT.md) | GO manuel standalone |
| [S4_PRODUCT_LOCKS_MATRIX.md](S4_PRODUCT_LOCKS_MATRIX.md) | Gouvernance produits |
| [S4_IMPLEMENTATION_ROADMAP.md](S4_IMPLEMENTATION_ROADMAP.md) | L6 Bundle encapsulation |
| [SETTLEMENT_LAYER_CONTRACT_v1.md](SETTLEMENT_LAYER_CONTRACT_v1.md) | Autorité ledger |
| [adr/001-intent-as-orchestrator.md](adr/001-intent-as-orchestrator.md) | Intent pilote |
| [adr/003-final-reconciliation-controller.md](adr/003-final-reconciliation-controller.md) | Controller gate |
| [adr/004-ledger-authority.md](adr/004-ledger-authority.md) | Writers autoritaires |
| [R4.5-E.2_BUNDLE_PARTIAL_RECONCILIATION_SPEC.md](../arquantix/R4.5-E.2_BUNDLE_PARTIAL_RECONCILIATION_SPEC.md) | Partial / finalize / anti-zombie |
| [BUNDLE_RECONCILIATION_PHASE3_PRD.md](../arquantix/portfolio_engine/BUNDLE_RECONCILIATION_PHASE3_PRD.md) | PRD réconciliation |
| `services/portfolio_engine/bundles/orchestrator.py` | Orchestrateur actuel |
| `services/portfolio_engine/bundle_execution/bundle_lifi_leg_service.py` | Settlement sync actuel |
| `services/transaction_intents/bundle_intent_sync.py` | Parent intent + legs metadata |
| `services/portfolio_engine/bundles/bundle_reconciliation_read_model.py` | Read model E.2-A |

---

## 14. Décisions & prochaine action

| # | Question | Décision |
| --- | --- | --- |
| 1 | Child intents (A) vs leg table (B) ? | **A** — child intents (B1 ✅) |
| 2 | Invest = split dépôt ou rebalance ? | **Rebalance-to-target** (doctrine CTO §4.0) |
| 3 | Ordre B3 ? | **B3b ✅** · B3a merge · **B3c scope 1×1×1×1** · B3d PE writers |
| 4 | Legs source ? | `rebalance_plan_after_funding` gelé (`plan_hash`) · pas `planned_allocations` split |
| 5 | Re-plan après invest ? | **Non** — gate `REBALANCE_PLAN_FROZEN` · abandon parent seul |
| 6 | Plan versioning ? | **`planner_version`** obligatoire avec `plan_hash` (§4.0.4) |
| 7 | Dual-run prod ? | **Non** — B2b flag OFF · staging pilote uniquement |
| 8 | LI.FI standalone ? | **Gelé** — aucune régression |

**Prochaine action** :

1. **Deploy neutre B3a** · `BUNDLE_FUNDING_HANDLER_ENABLED` absent/false
2. Validation flag OFF · zéro call runtime · PE/CB/legs inchangés
3. **GO B3c** — handler `bundle_leg` settlement · rail minimal §4.0.5–§4.0.6 :
   - 1 parent · 1 child · 1 buy leg · **USDC → AAVE** · **Base**
   - settlement child isolé (mini LI.FI) · flag OFF · pas de Controller
