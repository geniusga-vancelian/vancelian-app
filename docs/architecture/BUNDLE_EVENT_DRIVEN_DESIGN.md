# Bundle Event-Driven — Audit & Design (v0)

| Champ | Valeur |
| --- | --- |
| **Type** | Audit + design · **aucun code runtime** |
| **Date** | 2026-06-07 |
| **Statut** | Draft design — pré-implémentation |
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
    → pour chaque allocation :
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

### 4.1 Principes directeurs

1. **Bundle = orchestrateur multi-transactions**, pas N clones du handler LI.FI standalone.
2. **Réutiliser la plomberie** outbox / worker / Settlement Layer **via router** `product_type` — pas réinventer ledger.
3. **`is_bundle_internal_swap=true`** reste la frontière ; legs bundle **ne passent jamais** par `lifi_swap_controller` v1.
4. **Intent parent** porte le cycle de vie global ; **chaque leg** a son propre pipeline settlement + controller leg (ou step interne équivalent).
5. **Controller parent** = premier cas ADR 003 multi-leg — agrège enfants, allocations, residual, double spend.
6. **Migration progressive** : dual-run sous flag ; LI.FI standalone **gelé** ; pas de régression prod pilote.

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
4. Snapshot comptable (metadata parent) :
     trading_available USDC (source funding)
     bundle_cash + bundle_position (scope bundle)
     allocations cible (plan)
     balance_snapshot_hash
5. Funding interne (event / settlement step) :
     trading_available → bundle_cash_leg
     mouvement PE interne — pas swap externe
     phase parent : FUNDED (ou équivalent)
6. Créer bundle legs (plan d’exécution) :
     leg 1 : USDC → BTC
     leg 2 : USDC → ETH
     leg 3 : USDC → AAVE
     chaque leg : swap record + lien parent
7. Pour chaque leg (séquentiel ou parallèle contrôlé) :
     a. Enregistrer leg (child intent OU leg state machine)
     b. Quote LI.FI (bundle handler dédié)
     c. Submit on-chain
     d. Outbox : bundle_leg.settle (PAS intent.settle standalone)
     e. Settlement Layer handler bundle_leg → Privy + receipt
     f. PE atoms leg (via settlement handler — pas HTTP direct)
     g. Cost basis bundle-scoped
     h. Controller leg → RECONCILED (bundle_leg)
8. Controller parent :
     - toutes legs RECONCILED ou terminal explicite (skipped_failed)
     - allocation finale vs cible (tolérance drift)
     - aucun double spend USDC
     - cash residual / dust documenté
     - agrégation report hash multi-leg
9. Release Product Lock parent
10. Phase parent finale :
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
  "planned_legs": [...],
  "child_intent_ids": ["uuid", "..."],
  "funding": { "amount_usdc": "...", "snapshot_hash": "..." }
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
2. Snapshot metadata parent :
   - `trading_available` USDC (source)
   - `bundle_cash` + `bundle_position` agrégés (resolver S4 L3 existe)
   - allocations planifiées + hash canonique
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
  → settlement/bundle_funding handler
  → debit pe.direct_overlay (trading_available)
  → credit pe.bundle_cash_leg
  → audit pe + optional bundle_ledger mirror
  → parent phase : FUNDED
  → enqueue leg creation events
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

**Checks agrégés** :

| Check | Détail |
| --- | --- |
| Couverture legs | N planned vs N terminal |
| Allocation finale | Poids spot vs `pe_target_allocations` (tolérance drift rebalance) |
| Double spend | Somme débits USDC legs ≤ funding − buffer |
| Cash residual | `bundle_cash_leg` restant documenté (dust / skipped legs) |
| Lock | Product lock encore actif → refuse release until OK |
| Enfants | Aucune leg `RECONCILIATION_RETRYABLE_FAILURE` sans policy |
| Report | Hash agrégé : parent + child hashes + allocations + residual |

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

**Comptabilisation parent Controller** :

```text
funded_usdc = snapshot.funding.amount
executed_usdc = sum(leg.debit_usdc for reconciled legs)
residual_usdc = bundle_cash_leg.available
invariant: executed_usdc + residual_usdc + buffer ≈ funded_usdc
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
| **B2** | `bundle_product_locks.py` · acquire/release parent scope `bundle` · snapshot PE · flag + allowlist | ❌ Module only · **non branché legacy** | **🟡 PR ouverte** |
| **B2b** | Dual-run metadata lock + S4 lock · tests concurrence (swap vs bundle) | Staging | ⏸ |

**B2 livré (module)** :

| Fonction | Rôle |
| --- | --- |
| `acquire_bundle_parent_lock` | Lock S4 `scope=bundle` · `asset=USDC` · `intent_id=parent` |
| `release_bundle_parent_lock` | Release slot bundle parent |
| `build_bundle_parent_snapshot` | Snapshot canonique (trading · bundle_cash · bundle_position · allocations · buffer · hash) |

Gating : `TRANSACTION_PRODUCT_LOCKS_ENABLED` **+** `TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS` (fail-closed L5a). Flag OFF ou hors allowlist → **no-op strict**.

**Non modifié en B2** :

- `pe_portfolios.metadata.bundle_invest_lock` (legacy intact)
- Orchestrateur Bundle legacy · child intents · settlement · Controller · PE writers

Prérequis S4 : L1–L5 merged (table, engine, snapshot, middleware, router) — cf. [S4_IMPLEMENTATION_ROADMAP.md](S4_IMPLEMENTATION_ROADMAP.md) L6.

### Phase B3 — Settlement Layer Bundle

| PR | Scope | Runtime |
| --- | --- | --- |
| **B3a** | Handler `bundle_funding` · router L5 · receipt hash parent | Flag OFF |
| **B3b** | Handler `bundle_leg` · remplace `apply_swap_settlement` direct · idempotence | Flag OFF |
| **B3c** | PE atoms + cost basis **via handlers only** · retire writers HTTP | Flag OFF |

### Phase B4 — Outbox & worker Bundle

| PR | Scope | Runtime |
| --- | --- | --- |
| **B4a** | Events `bundle.fund`, `bundle_leg.settle` · worker routes | Flag OFF |
| **B4b** | Child intent creation · parent orchestration loop | Flag OFF |
| **B4c** | Finalize `bundle.finalize` · E.2 terminal statuses | Flag OFF |

### Phase B5 — Controller Bundle

| PR | Scope | Runtime |
| --- | --- | --- |
| **B5a** | Controller leg spec + tests · `bundle_leg_controller.py` | No prod |
| **B5b** | Controller parent spec + tests · agrégation multi-leg | No prod |
| **B5c** | Worker `bundle_leg.reconcile` + `intent.reconcile` parent · manual test 1 bundle | Pilot only |

### Phase B6 — Migration & deprecation

| PR | Scope | Runtime |
| --- | --- | --- |
| **B6a** | Dual-run : legacy HTTP path + event path (flag) | Staging |
| **B6b** | Retire `submit-tx` settlement sync · deprecate metadata lock | Prod Go |
| **B6c** | Retire `POST /invest/resume` client · orchestrator internal retry only | Prod Go |

### Phase B7 — Rebalance & Withdraw

| PR | Scope |
| --- | --- |
| **B7** | Même pattern parent/child pour `bundle_withdraw` · rebalance batch |

### Dépendances externes

```mermaid
flowchart TD
  S4L5[S4 L5 Settlement Router] --> B3[B3 Settlement Handlers]
  B1[B1 Parent/Child Model] --> B4[B4 Outbox Worker]
  B2[B2 Product Locks] --> B4
  B3 --> B4
  B4 --> B5[B5 Controller Bundle]
  B5 --> B6[B6 Migration Prod]
  LI FI[LI.FI Standalone FROZEN] -.->|no regression| B3
```

---

## 11. Snapshot comptable requis

Snapshot parent au lock (inspiré S4 L3 + bundle-specific) :

```json
{
  "version": "bundle-invest-v1",
  "source": "pe",
  "scopes": {
    "trading_available": { "USDC": "100.00" },
    "bundle_cash": { "USDC": "0" },
    "bundle_position": {}
  },
  "funding": {
    "amount_usdc": "100.00",
    "entry_asset": "USDC"
  },
  "planned_allocations": [
    { "asset": "CBBTC", "weight_bps": 4000, "planned_usdc": "40.00" },
    { "asset": "CBETH", "weight_bps": 3500, "planned_usdc": "35.00" },
    { "asset": "AAVE", "weight_bps": 2500, "planned_usdc": "25.00" }
  ],
  "execution_buffer_usdc": "1.00",
  "balance_snapshot_hash": "<sha256 canonical>"
}
```

**Usage** :

- Product Lock release gate
- Controller parent allocation check
- Debug partial fill / residual
- **Ne pas** comparer trading snapshot vs wallet Privy (leçon Controller v1.2)

---

## 12. Interdictions (rappel)

- ❌ Aucun code runtime dans ce chantier design
- ❌ Aucune activation prod Bundle event-driven
- ❌ Aucun changement LI.FI standalone (S3b, Controller v1.2, flags pilote)
- ❌ Aucun branchement worker bundle sans Go explicite
- ❌ Ne pas traiter Bundle comme N× handler `reconcile_lifi_swap_intent`
- ❌ Ne pas commencer par Controller parent avant modèle parent/child + settlement leg

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

## 14. Décision ouverte (review CTO)

| # | Question | Recommandation draft |
| --- | --- | --- |
| 1 | Child intents (A) vs leg table (B) ? | **A** — child intents |
| 2 | Legs parallèles ou séquentiels strict ? | Séquentiel v1 event-driven (simplicité cash leg) · parallèle v2 |
| 3 | Conserver shadow `bundle_ledger_entries` ? | Oui en miroir · pas gate COMPLETED |
| 4 | Renommer `bundle_invest` lock metadata ? | Deprecate après B2b |
| 5 | Controller parent avant COMPLETED bundle UI ? | Oui — ADR 003 · UI peut rester sur statuts E.2 |

**Prochaine action** : review CTO de ce document → GO **B1** (modèle parent/child + migration additive) **sans** runtime.
