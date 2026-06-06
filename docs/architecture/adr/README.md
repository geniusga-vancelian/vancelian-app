# Architecture transactionnelle — ADR & POC

Index des décisions d’architecture pour l’évolution de Vancelian vers un modèle **intent → queue → worker → settlement → reconciliation controller**.

> **Gouvernance PR (obligatoire en review)** : [TRANSACTION_ENGINE_GOVERNANCE.md](../TRANSACTION_ENGINE_GOVERNANCE.md) — 5 règles non négociables, checklist reviewer, rejets automatiques.

| ADR | Titre | Statut |
| --- | --- | --- |
| [001](001-intent-as-orchestrator.md) | Intent as Orchestrator | Accepté |
| [002](002-postgresql-outbox-canonical-queue.md) | PostgreSQL Outbox as Canonical Queue | Accepté |
| [003](003-final-reconciliation-controller.md) | Final Reconciliation Controller | Accepté |
| [004](004-ledger-authority.md) | **Ledger Authority (constitution)** | Accepté |

> **Hiérarchie opérationnelle** : ADR 004 > ADR 001 > ADR 002 > ADR 003. Si ADR 004 est violé, les autres ADR deviennent inopérants.

**Documents liés** : [**Gouvernance transaction engine**](../TRANSACTION_ENGINE_GOVERNANCE.md) · `docs/arquantix/TRANSACTION_INTENTS_DEFI.md` (historique Phase 7) · [PHASE2 POC ticket](../PHASE2_POC_LIFI_STANDALONE_SWAP.md) · [S1 Review Report](../S1_REVIEW_REPORT.md).

---

## Résumé exécutif

### Constat

Le système actuel repose sur des **écritures directes** (ledger, PE scopes) déclenchées de façon synchrone ou best-effort, avec des intents qui ne font qu’**observer** l’état produit. La réconciliation existe mais arrive **après coup**, sans bloquer l’utilisateur ni garantir la cohérence UI.

### Source de vérité transactionnelle (décision structurante)

```
Provider / Blockchain
        ↓
Intent
        ↓
Outbox
        ↓
Worker
        ↓
Settlement Layer    ← seul writer économique (ADR 004)
        ↓
Ledger
        ↓
PE scopes
        ↓
UI
```

**Aucune écriture économique en dehors de la Settlement Layer.** Voir [ADR 004 — constitution](004-ledger-authority.md).

### Quatre responsabilités — ne plus les confondre

| Couche | Responsable | Rôle |
| --- | --- | --- |
| **Décision** | Intent | Qui initie, idempotency, cycle de vie |
| **Exécution** | Worker (+ Outbox) | Transport ordonné, retry |
| **Vérité économique** | **Settlement Layer** | **Seul writer** ledger + PE |
| **Validation finale** | Controller | Gate `COMPLETED` |

Anti-pattern historique à éliminer : API/webhook/cron qui écrivent ledger puis cron qui « répare » — plus personne ne sait qui possède la vérité.

### Noyau universel (tous produits présents et futurs)

Un moteur unique pour spot, vaults, bundles, Lombard, RWA, MiFID — évite de reconstruire la plateforme tous les 6 mois.

### Risque #1 à l’échelle (S4)

Pas le webhook — la **concurrence sur le même solde** (100 USDC × swap + vault + bundle à 50 ms). Protection : **lock pessimiste** + **`balance_snapshot_hash`** optimiste.

### Risque disciplinaire (post-architecture)

Empêcher les futurs développements de contourner ADR 004 « pour aller plus vite » — principale source de dette transactionnelle en fintech.

### Direction validée

Cinq décisions figent la doctrine avant tout code :

1. **L’intent devient l’orchestrateur** — il pilote le cycle de vie, pas seulement la traçabilité (ADR 001).
2. **PostgreSQL outbox est la file officielle** — intent + event dans la même transaction ; worker ECS poll avec `SKIP LOCKED` (ADR 002).
3. **Un contrôleur final est obligatoire** — `COMPLETED` seulement si on-chain = ledger = PE = UI ; sinon `RECONCILIATION_REQUIRED` + blocage assets (ADR 003).
4. **Seule la Settlement Layer écrit le ledger** — API, webhooks, cron et services produit ne touchent plus `person_wallet_deposits` / `pe_position_atoms` directement (ADR 004).
5. **Dépôt webhook = intent technique** — `observed_external_deposit` via outbox `deposit.observed`, pas d’écriture ledger directe par le webhook (ADR 004 §6, Phase 2b).

### Ce qu’on ne fait pas maintenant

- Pas de Redis Streams / SQS / Temporal comme queue primaire
- Pas de réécriture globale des produits
- Pas de code avant validation des ADR

### Premier livrable code (après ADR)

**POC Phase 2 — LI.FI standalone swaps uniquement**, sous feature flag, dual-run avec le flux legacy.

---

## Phase 2 POC — LI.FI standalone swaps

### Objectif

Prouver en staging que le pipeline orchestrateur fonctionne de bout en bout pour les swaps LI.FI **hors bundle interne**, sans régression sur le flux legacy (flag OFF).

### Périmètre

| In scope | Out of scope |
| --- | --- |
| Swap LI.FI standalone (`person_wallet_swaps`) | Bundle legs (`is_bundle_internal_swap`) |
| Flow quote → confirm-execute → approval → submit → poll → settle → reconcile | Vault, Lombard, exchange custodial |
| Tables outbox + transitions | Product locks cross-produit (Phase 4) |
| Worker via tick DeFi étendu | SQS, Temporal |
| Feature flag par env | Blocage UI effectif (log-only en POC) |

### Tables (migrations Alembic additives)

#### `transaction_outbox` (nouvelle)

Voir ADR 002. Migration `173_transaction_outbox.py` (numéro indicatif).

#### `transaction_intent_transitions` (nouvelle)

| Colonne | Type |
| --- | --- |
| `id` | UUID PK |
| `intent_id` | UUID FK |
| `from_status` | VARCHAR(32) |
| `to_status` | VARCHAR(32) |
| `phase` | VARCHAR(64) |
| `actor` | VARCHAR(64) — `api`, `worker`, `controller` |
| `metadata_json` | JSONB |
| `created_at` | TIMESTAMPTZ |

Index : `(intent_id, created_at)`.

#### `transaction_intents` (extensions)

Ajouts non-breaking :

| Colonne | Type | Default |
| --- | --- | --- |
| `correlation_id` | UUID | `gen_random_uuid()` |
| `current_phase` | VARCHAR(64) | `created` |
| `requested_action` | VARCHAR(32) | NULL → backfill `swap` |
| `assets_json` | JSONB | NULL |
| `expires_at` | TIMESTAMPTZ | NULL |
| `reconciliation_report_json` | JSONB | NULL |
| `blocked_assets_json` | JSONB | NULL |

Les colonnes existantes (`person_id`, `product_type`, `idempotency_key`, `linked_table`, `linked_id`, `status`, `metadata_json`) sont conservées.

### Feature flags

| Variable | Défaut | Effet |
| --- | --- | --- |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `false` | Active le pipeline intent → outbox → worker |
| `LIFI_OUTBOX_WORKER_ENABLED` | `false` | Active le traitement outbox dans le tick DeFi |
| `LIFI_RECONCILIATION_BLOCK_ENABLED` | `false` | Active le blocage API si `RECONCILIATION_REQUIRED` (log-only si false) |

**Rollback prod** : les trois flags à `false` → comportement Phase 7 inchangé.

### Worker

**Phase 2a** : extension de `defi_observability_tick` (`tick_service.py`)

Nouvelle step `process_transaction_outbox` :

1. Poll `transaction_outbox` (`pending`, `next_retry_at <= now()`, `LIMIT 20`, `FOR UPDATE SKIP LOCKED`)
2. Dispatch par `event_type` :
   - `intent.created` → validate + transition QUEUED
   - `intent.provider_submitted` → poll LI.FI (`refresh_lifi_status` refactoré, sans settlement direct)
   - `intent.settle` → `settle_transaction_intent_idempotently(intent_id)`
   - `intent.reconcile` → `run_final_reconciliation(intent_id)` (version LI.FI)
3. Marquer outbox `processed` ou retry / dead-letter

**Phase 2b** (post-validation staging) : script ECS dédié `transaction-intent-worker` pour latence < 30s.

### Flux POC (orchestrateur ON)

```
POST /swaps/quote
  TX: intent (CREATED) + person_wallet_swap + outbox(intent.created)

Worker intent.created
  → VALIDATED → QUEUED

POST /swaps/confirm-execute + POST /swaps/{id}/approval
  (inchangé côté client ; transitions intent via hooks)

POST /swaps/{id}/submit
  TX: swap.tx_hash + intent PROVIDER_SUBMITTED + outbox(intent.provider_submitted)

Worker intent.provider_submitted
  → poll LI.FI → ONCHAIN_CONFIRMED
  → outbox(intent.settle)

Worker intent.settle
  → settle_transaction_intent_idempotently(intent_id)
     └─ wrappe settle_lifi_swap_idempotently existant
  → LEDGER_SETTLED
  → outbox(intent.reconcile)

Worker intent.reconcile
  → run_final_reconciliation(intent_id)
  → COMPLETED ou RECONCILIATION_REQUIRED
```

### Refactorings minimaux (liste de travail Phase 2)

| Fichier | Changement |
| --- | --- |
| `lifi_quote_service.py` | Créer intent orchestrateur + outbox en même TX que swap |
| `lifi_execute_service.py` | Submit → outbox `provider_submitted` ; retirer settlement synchrone si flag ON |
| `lifi_swap_settlement.py` | Exposer `settle_transaction_intent_idempotently` (wrapper) |
| Nouveau `intent_worker/` ou `transaction_outbox/` | Handlers par event_type |
| Nouveau `reconciliation_controller/` | `run_final_reconciliation` version LI.FI |
| `lifi_intent_sync.py` | Bypass si orchestrateur ON (éviter double sync) |

### Tests obligatoires POC (CI)

| # | Test | Fichier cible |
| --- | --- | --- |
| 1 | Double submit même intent → 1 settlement | `test_lifi_intent_orchestrator_idempotency.py` |
| 2 | Crash worker après tx_hash → reprise → COMPLETED | `test_lifi_intent_worker_recovery.py` |
| 3 | Tx confirmée, ledger fail → retry settle → COMPLETED | `test_lifi_intent_settle_retry.py` |
| 4 | settle idempotent (2e appel noop) | Réutilise `test_lifi_swap_ledger_idempotency.py` |
| 5 | Outbox dead-letter après max_attempts | `test_transaction_outbox_dead_letter.py` |
| 6 | Intent + outbox même TX (rollback si outbox fail) | `test_transaction_outbox_atomicity.py` |
| 7 | Controller KO → RECONCILIATION_REQUIRED | `test_lifi_reconciliation_controller.py` |
| 8 | Flag OFF → flux legacy inchangé | `test_lifi_legacy_path_regression.py` |
| 9 | Webhook crédit seul → auto-repair → COMPLETED | Extension `test_lifi_swap_reconciliation.py` |

### Critères de sortie Phase 2

- [ ] 9 tests CI verts
- [ ] Staging : 10 swaps manuels orchestrateur ON sans régression ledger
- [ ] Staging : rollback flag OFF validé
- [ ] Aucun swap bundle interne affecté
- [ ] Métriques outbox (pending, dead_letter) visibles dans tick summary
- [ ] Revue ops : timeline intent consultable (SQL ou endpoint debug minimal)

### Roadmap plateforme (priorité validée)

| # | Milestone | Livrable |
| --- | --- | --- |
| S1 | Outbox | Migrations + atomicité |
| S2 | Intent + Worker | LI.FI orchestrateur + handlers outbox |
| S3 | Controller | Reconciliation gate COMPLETED |
| **S4** | **Product Locks + balance snapshot** | Lock pessimiste + `balance_snapshot_hash` (concurrence USDC) |
| S5 | Staging | Dual-run + rollback |
| S6 | Webhooks | Privy `observed_external_deposit` (après S5) |
| 7+ | Post-POC | Bundle → Vault → Lombard |

**Risque #1 à l’échelle** : concurrence sur le même solde — pas les dépôts externes. S4 avant S6.

### Garde-fous exécution

| Phase | Piège | Gate |
| --- | --- | --- |
| **S1** | Intent + swap + outbox dans **3 TX** | Test atomicité ROLLBACK/COMMIT — **priorité #1**, gate avant S2 |
| **S4** | Locks seuls insuffisants sur le montant | `available_balance_version` + `BALANCE_VERSION_MISMATCH` |
| Court terme | Dispersion sur custody / réco legacy | Gel : effort 100 % sur S1→S4→S5 |

---

## Architecture visuelle

### Cible (Image 1)

```
User action
  → Transaction Intent (orchestrateur)
  → PostgreSQL Outbox (même TX)
  → Worker ECS (SKIP LOCKED)
  → Execution on-chain / LI.FI
  → settle_transaction_intent_idempotently
  → Final Reconciliation Controller
  → COMPLETED (ou RECONCILIATION_REQUIRED)
```

### Actuelle (Image 2)

```
User action
  → API synchrone
  → Écriture directe ledger / PE (best-effort)
  → Intent miroir (sync optionnel)
  → Réconciliation cron (après coup)
  → Statut produit ≠ UI ≠ ledger possible
```

---

## Prochaine action

1. ~~Valider les 3 ADR~~ — fait
2. ~~Réviser `TRANSACTION_INTENTS_DEFI.md`~~ — fait (warning + liens ADR)
3. ~~Ouvrir ticket Phase 2 POC~~ — fait : [PHASE2_POC_LIFI_STANDALONE_SWAP.md](../PHASE2_POC_LIFI_STANDALONE_SWAP.md)
4. **Coder** uniquement après feu vert [Issue #25](https://github.com/geniusga-vancelian/vancelian-app/issues/25) (Phase 2 POC)
