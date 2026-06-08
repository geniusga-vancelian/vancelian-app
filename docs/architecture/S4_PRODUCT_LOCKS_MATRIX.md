# S4 — Product Locks Matrix (gouvernance)

| Champ | Valeur |
| --- | --- |
| **Type** | Inventaire / gouvernance · **aucun code** |
| **Date** | 2026-06-07 |
| **Statut** | Validé CTO v1 — Global User Transaction Lock V1 mergé (PR #59 · deploy neutre TD :156) |
| **Prérequis validés** | Rail event-driven LI.FI standalone prod (#37–#40) |
| **Références** | [ADR 004](adr/004-ledger-authority.md) · [ADR 001 §5bis](adr/001-intent-as-orchestrator.md) · [SETTLEMENT_LAYER_CONTRACT_v1](SETTLEMENT_LAYER_CONTRACT_v1.md) · [PHASE2 POC](PHASE2_POC_LIFI_STANDALONE_SWAP.md) |

---

## Objectif

Empêcher qu’un **Bundle**, un **Vault**, un **Lombard** ou un futur produit (RWA, Equities) **contourne** les garanties construites pour LI.FI standalone sur le rail transactionnel partagé :

```
Intent → Outbox → Worker → Settlement → Ledger → (Controller) → COMPLETED
```

Ce document est la **matrice de gouvernance** (S4 inventaire). L’implémentation technique (`transaction_product_locks`, `balance_snapshot_hash`, middleware 409) est découpée en PRs — voir [S4_IMPLEMENTATION_ROADMAP.md](S4_IMPLEMENTATION_ROADMAP.md) et [PHASE2 POC § S4 checklist](PHASE2_POC_LIFI_STANDALONE_SWAP.md).

**Règle d’or** : si la matrice est bonne, Bundle / Lombard / Vault **réutilisent** le rail prouvé sur LI.FI ; ils ne réinventent pas la plomberie ledger.

---

## 1. Cartographie des Intent Types

Source code : `services/transaction_intents/enums.py` (`IntentProductType`, `IntentOperationType`).

### 1.1 Produits — mapping cible vs code actuel

| Produit métier | `product_type` (code) | `operation_type` typique | Statut rail orchestrateur | Notes |
| --- | --- | --- | --- | --- |
| **LI.FI Swap standalone** | `lifi_swap` | `swap` | ✅ **Prod validé** (allowlist) | Phase 2 orchestrateur · outbox `intent.created` / `intent.settle` |
| **Bundle Invest** | `bundle_invest` | `invest` / `bundle_leg` | ⚠️ **Legacy PE** (hors outbox Phase 2) | `bundle_invest_lock` (par portfolio) + **Global Lock** si flag ON (`legacy_bundle_global_lock.py`) |
| **Bundle Withdraw** | `bundle_withdraw` | `withdraw` / `bundle_leg` | ⚠️ **Legacy PE** | Miroir invest lock |
| **Morpho Vault (Earn)** | `morpho_earn` | `supply` / `withdraw` | 🔶 Intent sync existant · settlement legacy | `vault_funding.py` |
| **Ledgity Vault** | `ledgity_vault` | `deposit` / `withdraw` | 🔶 Intent sync existant · settlement legacy | Idem |
| **Lombard Open / Borrow** | `lombard_borrow` | `borrow` (+ étapes collateral) | 🔶 **Multi-step P1** | `lombard_funding.py` · **casse l’hypothèse 1 intent → 1 écriture** |
| **Lombard Close / Repay** | `lombard_borrow` | `repay` | 🔶 Futur | Même famille produit |
| **Privy Deposit (webapp)** | `privy_deposit` | `deposit` | ⏸ Dormant | Enum présent · pas de parcours webapp actif |
| **Dépôt externe observé** | `observed_external_deposit` | — | 📋 **S6** (ADR 004 §6) | Webhook Privy → intent technique · pas crédit direct cible |
| **RWA / Equities** | *à définir* | *à définir* | ⏸ | Hors codebase Phase 2 |

### 1.1bis Lombard — naming métier vs code

> **Objectif** : éviter de créer un futur `loan_open` en doublon alors que le code existant utilise déjà `lombard_borrow`.

| Vocabulaire | Valeurs |
| --- | --- |
| **Métier** | `loan_open` / `loan_close` |
| **Code actuel** | `product_type = lombard_borrow` · `operation_type = borrow` / `repay` |

Ne pas introduire de `product_type` séparé `loan_open` / `loan_close` sans migration explicite — le vocabulaire métier reste documentaire.

### 1.2 Outbox — event types canoniques

Source : `services/transaction_outbox/enums.py`

| Event | Rôle | LI.FI Phase 2 | Autres produits |
| --- | --- | --- | --- |
| `intent.created` | Worker S2b · CREATED → QUEUED | ✅ Implémenté | 🔶 À généraliser |
| `intent.settle` | Settlement S3a/S3b | ✅ Implémenté | 🔶 À router par `product_type` |
| `intent.provider_submitted` | Preuve provider | 🔶 Partiel | Lombard / vault |
| `intent.reconcile` | Controller (ADR 003) | ⏸ | ⏸ |
| `deposit.observed` | Webhook Privy (Phase 2b) | 📋 S6 | Lecture → intent technique |

### 1.3 Phases orchestrateur (LI.FI référence)

Source : `services/transaction_outbox/intent_phases.py`

```
CREATED → VALIDATED → QUEUED → PROCESSING → ONCHAIN_CONFIRMED → LEDGER_SETTLED → RECONCILED → COMPLETED
```

| Produit | Phases prouvées prod | Écart |
| --- | --- | --- |
| LI.FI standalone | CREATED → … → **LEDGER_SETTLED** | Controller / COMPLETED non activés |
| Bundle | N/A (lock metadata, pas phase2_orchestrator uniforme) | Pas le même rail |
| Lombard | Intent health P1 · statuts `retryable_failed` | **Plusieurs étapes économiques par intent** |
| Vault | Intent sync · funding direct | Pas settlement layer unifié |

---

## 2. Cartographie des Writers autorisés

**Doctrine ADR 004** : seule la **Settlement Layer** (`settle_transaction_intent_idempotently`) est le writer économique **cible**. Le tableau ci-dessous décrit l’**état actuel** (dual-run / legacy) et la **cible S4+**.

Légende : ✅ autorisé cible · ⚠️ legacy temporaire · ❌ interdit cible · 👁 lecture / observation uniquement

| Writer / chemin | LI.FI standalone | Bundle | Lombard | Vault | Cible ADR 004 |
| --- | --- | --- | --- | --- | --- |
| **Settlement Layer** (`settle_transaction_intent_idempotently`) | ✅ S3b actif (allowlist) | 🔶 À encapsuler (`pe_settlement`, `bundle_funding`) | 🔶 À encapsuler (`lombard_funding`) | 🔶 À encapsuler (`vault_funding`) | ✅ **Seul writer** |
| **`apply_swap_settlement`** (legacy LI.FI) | ⚠️ Skip si orchestrateur actif (#38) | ❌ | ❌ | ❌ | ❌ Supprimer post-migration |
| **`settle_lifi_swap_idempotently`** (reconciliation / tick) | ⚠️ Maintenance tick · débit legacy possible · CB skip orchestrateur (#40) | ❌ (legs = `is_bundle_internal_swap`) | ❌ | ❌ | ❌ Déléguer à Settlement uniquement |
| **`swap_session_maintenance`** (cron tick) | ⚠️ Poll swaps · appelle reconciliation | ❌ | ❌ | ❌ | 👁 → enqueue outbox only |
| **Webhook Privy** (`webhook_service`) | 👁 Crédit direct **aujourd’hui** · source prod double-credit évité par #39 | 👁 | 👁 | 👁 | 👁 → `deposit.observed` → Settlement (S6) |
| **`ingest_lifi_swap_settlement`** (cost basis) | ⚠️ Via reconciliation legacy · **skip orchestrateur (#40)** | ❌ (`ingest_bundle_lifi` séparé) | 🔶 Via settlement Lombard | 🔶 Via settlement vault | ✅ Via Settlement uniquement |
| **`bundle_funding` / `pe_settlement`** | ❌ | ⚠️ **Writer direct aujourd’hui** | ❌ | ❌ | 🔶 Sous Settlement |
| **`vault_funding`** | ❌ | ❌ | ❌ | ⚠️ **Writer direct aujourd’hui** | 🔶 Sous Settlement |
| **`lombard_funding`** | ❌ | ❌ | ⚠️ **Writer direct aujourd’hui** | ❌ | 🔶 Sous Settlement |
| **Routes HTTP** (swap, bundle, vault) | 👁 Déclenche intent / quote | 👁 | 👁 | 👁 | ❌ Pas d’écriture Tier 1 |
| **Portal Next.js** | 👁 OVT / UX | 👁 | 👁 | 👁 | ❌ Jamais ledger |

### 2.1 Guards existants (Phase 2 — à généraliser en S4)

| Guard | Fichier | Règle |
| --- | --- | --- |
| `skip_legacy_swap_settlement_for_orchestrator` | `orchestrator_settle_enqueue.py` | Intent Phase 2 + allowlist + flag → pas `apply_swap_settlement` |
| `skip_legacy_cost_basis_for_orchestrator` | idem + `lifi_swap_reconciliation.py` | Idem → pas CB via reconciliation legacy |
| `is_bundle_internal_swap` | `bundle_transaction_scope.py` | Swap avec `bundle_leg_context` → **exclu** S3b standalone · CB bundle séparé |
| `validate_lifi_standalone_eligible` | `settlement/lifi_ledger.py` | `product_type == lifi_swap` · pas bundle internal · CONFIRMED · tx_hash |
| Allowlist pilot | `orchestrator_allowlist.py` | Worker / ledger / orchestrator par personne |
| Outbox idempotence | migration 174 | `(intent_id, event_type)` unique |

---

## 3. Liste négative (interdictions par produit)

> **C’est la section anti-catastrophe.** Toute PR qui viole une ligne ci-dessous = **Architecture Review obligatoire** ([TRANSACTION_ENGINE_GOVERNANCE](TRANSACTION_ENGINE_GOVERNANCE.md)).

### 3.1 LI.FI standalone (orchestrateur actif)

Un swap **LI.FI standalone** (`lifi_swap`, `phase2_orchestrator=true`, allowlist) **ne peut jamais** :

- Passer par `apply_swap_settlement` legacy (guard #38)
- Recevoir un second crédit destination si webhook/backfill a déjà crédité sur le même `tx_hash` (guard #39 / `detect_swap_ledger_legs`)
- Recevoir cost basis via `settle_lifi_swap_idempotently` (guard #40)
- Être traité comme `is_bundle_internal_swap` sans contexte bundle explicite
- Atteindre `COMPLETED` sans Controller (ADR 003)
- Faire écrire le portal ou une route HTTP directement dans `person_wallet_deposits` / `pe_position_atoms`

### 3.2 Bundle (`bundle_invest` / `bundle_withdraw`)

Un **Bundle** **ne peut jamais** :

- Appeler `apply_swap_settlement` sur un leg **standalone** (confusion Mon Trading ↔ bundle)
- Écrire directement dans `person_wallet_balances` hors Settlement Layer (cible ADR 004)
- Écrire directement dans `pe_position_atoms` via orchestrator HTTP sans passer par settlement bundle encapsulé
- Créer `cost_basis_executions` via `ingest_lifi_swap_settlement` (chemin Mon Trading) — utiliser `ingest_bundle_lifi`
- Marquer `COMPLETED` sans reconciliation batch
- Réutiliser le handler outbox **`intent.settle` LI.FI S3b** pour un intent `bundle_invest` (router settlement par `product_type`)
- Partager un lock USDC avec LI.FI standalone **sans** Product Lock S4 (concurrence non sérialisée)

**Leg LI.FI interne** (allocation / rebalance / withdraw_sell) :

- Doit porter `bundle_leg_context` + `is_bundle_internal_swap == true`
- **Exclu** du settlement S3b standalone
- Cost basis via chemin bundle · pas standalone

### 3.3 Vault (`morpho_earn` / `ledgity_vault`)

Un **Vault** **ne peut jamais** :

- Appeler `apply_swap_settlement` ou reconciliation LI.FI swap
- Consommer le même USDC qu’un swap LI.FI pending **sans** lock produit (S4)
- Écrire ledger via `vault_funding.py` en runtime **après** migration Settlement (cible)
- Créer cost basis via chemin LI.FI standalone
- Marquer COMPLETED sans Controller vault-specific

### 3.4 Lombard (`lombard_borrow`) — **risque prioritaire**

**Naming** (cf. §1.1bis) : métier `loan_open` / `loan_close` · code `lombard_borrow` + `operation_type` `borrow` / `repay`.

Un **Lombard** **ne peut jamais** :

- Réutiliser le settlement **LI.FI S3b** (`lifi_swap` projection)
- Supposer **1 intent → 1 écriture ledger** sans modèle de **sous-étapes** explicites
- Appeler `apply_swap_settlement` / swap maintenance
- Écrire collateral + borrow + loan position dans un seul appel HTTP sans outbox séquencée
- Marquer COMPLETED avant validation collateral + borrow + réconciliation on-chain
- Partager le lock cbBTC / USDC avec swap ou vault sans matrice de locks

**Modèle cible Lombard** (multi-étape — Controller requis) :

```
Intent lombard_borrow (1 intent parent)
    ↓
Collateral deposit (attempt / on-chain)
    ↓
Controller check (collateral suffisant)
    ↓
Borrow USDC (attempt)
    ↓
Settlement Layer (ledger + loan position)
    ↓
RECONCILED → COMPLETED
```

→ **Ne pas coder Lombard sur le rail LI.FI** ; **router** par `product_type` dans Settlement + outbox dédiés.

### 3.5 Webhook Privy (transversal)

Le webhook **ne peut jamais** (cible ADR 004 §6) :

- Créditer définitivement sans intent + settlement (état actuel = dette · pilot #39 a mitigé le double crédit LI.FI)
- Être la **seule** preuve de settlement pour un swap orchestrateur actif
- Muter un dépôt déjà lié à un swap settlement

### 3.6 Tableau synthèse « qui ne touche pas quoi »

| Action interdite | LI.FI orch. | Bundle | Lombard | Vault |
| --- | --- | --- | --- | --- |
| `apply_swap_settlement` | ❌ | ❌ | ❌ | ❌ |
| S3b `lifi_ledger` sans `lifi_swap` | ❌ | ❌ | ❌ | ❌ |
| CB via reconciliation legacy | ❌ | ❌ | ❌ | ❌ |
| Écriture directe Tier 1 (cible) | ❌ | ❌ | ❌ | ❌ |
| COMPLETED sans Controller | ❌ | ❌ | ❌ | ❌ |
| Lock USDC ignoré (futur S4) | ❌ | ❌ | ❌ | ❌ |

---

## 4. Product Locks techniques (cible — pas implémenté ici)

Cette section liste les **mécanismes à implémenter** après validation de la matrice. Référence checklist : [PHASE2 POC § S4 L1–L11](PHASE2_POC_LIFI_STANDALONE_SWAP.md).

> **S4 Product Locks ≠ Controller**
>
> S4 Product Locks **ne marque jamais** `RECONCILED` ou `COMPLETED`.
> S4 **ne remplace pas** le Controller (ADR 003).
> S4 empêche les **conflits concurrentiels** produit / asset / scope.
> Le Controller reste une **phase ultérieure**, notamment pour Bundle et Lombard.

### 4.1 Router settlement par `product_type`

```python
# Cible — seul point d'entrée (ADR 004)
settle_transaction_intent_idempotently(db, intent_id)
    → match intent.product_type:
        lifi_swap        → S3b (existant)
        bundle_invest    → settle_bundle_invest (à encapsuler)
        bundle_withdraw  → settle_bundle_withdraw
        lombard_borrow   → settle_lombard_* (multi-leg)
        morpho_earn / ledgity_vault → settle_vault_*
        observed_external_deposit → settle_observed_deposit
```

**Lock produit** : handler inconnu → `ProductLockViolation` / `settlement.product_not_supported` (pattern S3b existant).

### 4.2 Guards à généraliser (au-delà de LI.FI)

| Pattern existant | Généralisation S4 |
| --- | --- |
| `skip_legacy_*_for_orchestrator` | Tout writer legacy par produit + allowlist |
| `is_bundle_internal_swap()` | `is_product_scoped_execution(intent, swap)` |
| `validate_lifi_standalone_eligible` | `validate_settlement_eligible(intent, linked_entity)` par produit |
| Allowlist par personne | + lock par `person:wallet:asset:scope` |
| `detect_swap_ledger_legs` | `detect_ledger_legs(intent, linked_entity)` par famille produit |

### 4.3 Locks pessimistes + snapshot optimiste (ADR 001 §5bis)

| Mécanisme | Clé | Moment |
| --- | --- | --- |
| Lock pessimiste | `person:{id}:wallet:{id}:asset:{symbol}` | VALIDATED → PROCESSING |
| Lock scope | `…:scope:trading_available \| vault \| bundle \| lombard_collateral \| financial_transaction` | Idem |
| Snapshot | `metadata.balance_snapshot.{available, version, hash}` | À VALIDATED |
| Re-check | `BALANCE_VERSION_MISMATCH` / `BALANCE_CHANGED` | Avant PROCESSING · avant settlement |

**Scénario critique** : USDC = 100 · swap LI.FI + vault deposit + bundle invest simultanés → **un seul** gagne ; les autres 409 sans écriture ledger.

### 4.4 Lombard — extension obligatoire

| Hypothèse LI.FI (validée) | Hypothèse Lombard (non validée) |
| --- | --- |
| 1 intent → 1 swap → 1 settlement | 1 intent → N étapes économiques |
| 2 jambes ledger (debit + credit) | Collateral lock + borrow + loan atom |
| Pas de Controller en prod | **Controller obligatoire** avant COMPLETED |

**Lock S4 Lombard** : ne pas begin implementation until:

1. Matrice validée (ce document)
2. Modèle de sous-phases / attempts documenté (ADR 001 + ADR 003)
3. Settlement encapsule `lombard_funding.py` (plus d’appel direct routes)

### 4.6 Global User Transaction Lock V1 (pré-B4b)

> **Doctrine V1** : **1 user = 1 transaction financière active** (cross-produit).
> **V2** (future) : optimisation par `wallet` / `asset` / scope fin — les locks fins S4 restent pour audit et granularité.

| Champ | Valeur |
| --- | --- |
| **Module** | `services/product_locks/global_user_transaction_lock.py` |
| **Scope** | `financial_transaction` |
| **Clé logique** | `person:{id}:wallet:GLOBAL:asset:GLOBAL:scope:financial_transaction` |
| **Flag** | `GLOBAL_USER_TRANSACTION_LOCK_ENABLED=false` (défaut OFF) |
| **Indépendance** | Ne dépend **pas** de `TRANSACTION_PRODUCT_LOCKS_ENABLED` |
| **Wiring legacy WebApp** | `legacy_bundle_global_lock.py` → `BundleOrchestrator` LI.FI invest/resume · flag OFF par défaut |
| **Wiring B4b** | `bundle_b4b_runtime_bridge.py` (controlled test · flag OFF prod) |

**Comportement flag OFF** : no-op strict · aucune écriture `transaction_product_locks` · aucun 409.

**Comportement flag ON** :

| Cas | Résultat |
| --- | --- |
| Même `intent_id` | Idempotent |
| Autre intent même `person_id` | `ProductLockConflict` → `409 transaction_in_progress` |
| Autre `person_id` | Autorisé |
| Release | Idempotent |
| Lock expiré | Ignoré après cleanup · nouvel acquire autorisé |

**Coexistence** : le lock global **ne remplace pas** les locks fins (`trading_available`, `bundle`, …) — les deux peuvent coexister sur le même user (orthogonalité par scope).

**Gate Bundle** : **B4b** (premier pont blockchain) doit être branché **après** merge + deploy neutre de ce lock global.

### 4.5 Tests bloquants attendus (future PRs S4)

| Test | Assertion |
| --- | --- |
| Concurrence swap + vault même USDC | 1 succès · 1 `BALANCE_VERSION_MISMATCH` |
| Bundle leg ≠ standalone | S3b refuse · bundle settlement accepte |
| Lombard ≠ lifi_swap router | `settlement.product_not_supported` |
| Orchestrateur + maintenance tick | Pas de CB legacy (#40 regression) |
| Webhook + swap same tx | Pas de double crédit (#39 regression) |

---

## 5. État de maturité (CTO — juin 2026)

| Sujet | Maturité | Prochaine action |
| --- | --- | --- |
| Rail event-driven LI.FI | **95 %** | Gel · smoke non-régression optionnel |
| Settlement Layer | **85 %** | Router multi-produit |
| Gouvernance pilot (allowlist, flags, rollback) | **90 %** | Figée · [`GO_PILOT_PROD_STEP3_FINAL_EXECUTION_REPORT.md`](GO_PILOT_PROD_STEP3_FINAL_EXECUTION_REPORT.md) |
| **Product Isolation (S4)** | **0 % → inventaire fait** | Validation matrice · puis L1–L11 |
| Controller | **20 %** | Après S4 · surtout Lombard |
| Bundle event-driven | **0 %** | Encapsuler writers · outbox |
| Lombard event-driven | **0 %** | Modèle multi-étape d’abord |

---

## 6. Ordre recommandé (post-Étape 3)

```
1. Valider cette matrice (Architecture Review)
2. Gel LI.FI standalone (prod :127 · worker/ledger OFF)
3. Implémenter S4 technique (locks + snapshot + middleware 409)
4. Encapsuler writers legacy (bundle / vault / lombard) sous Settlement
5. Controller (ADR 003) — priorité Lombard
6. Élargissement allowlist / nouveaux produits
```

**Interdit avant S4** : coder Bundle ou Lombard « vite » sur le rail LI.FI · élargir allowlist · activer Controller prod.

---

## 7. Références ops Étape 3

| Artefact | Lien |
| --- | --- |
| Clôture Étape 3 | [GO_PILOT_PROD_STEP3_FINAL_EXECUTION_REPORT.md](GO_PILOT_PROD_STEP3_FINAL_EXECUTION_REPORT.md) |
| Incident idempotence webhook | [GO_PILOT_PROD_STEP3_S3B_IDEMPOTENCE_INCIDENT.md](GO_PILOT_PROD_STEP3_S3B_IDEMPOTENCE_INCIDENT.md) |
| PR #39 S3b webhook reuse | Mergée |
| PR #40 skip legacy CB | Mergée |
| Pilot runbook | [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) |

---

## Changelog

| Date | Version | Changement |
| --- | --- | --- |
| 2026-06-07 | v1 | Inventaire initial post-clôture Étape 3 |
| 2026-06-07 | v1.1 | Revue CTO · Lombard naming · S4 ≠ Controller |
| 2026-06-08 | v1.2 | Global User Transaction Lock V1 · scope `financial_transaction` · pré-B4b |
| 2026-06-08 | v1.3 | Global Lock câblé legacy Bundle Invest WebApp (`legacy_bundle_global_lock.py`) · incident concurrent invests |
