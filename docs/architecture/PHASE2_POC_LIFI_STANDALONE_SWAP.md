# Ticket — Phase 2 POC LI.FI standalone swap

| Champ | Valeur |
| --- | --- |
| **Type** | Epic / chantier architecture transactionnelle |
| **GitHub** | [Issue #25 — Phase 2 LI.FI Intent Orchestrator POC](https://github.com/geniusga-vancelian/vancelian-app/issues/25) |
| **Statut** | S1–S2.5 ✅ (#27–#33) · S3a en cours · S3b/S3 ⏸ |
| **Branche S2** | `feat/s2-lifi-intent-orchestrator` (vide, prête) |
| **Date** | 2026-06-07 |
| **Prérequis** | ADR 001–004 · [Gouvernance](../TRANSACTION_ENGINE_GOVERNANCE.md) · [Settlement Contract v1](../SETTLEMENT_LAYER_CONTRACT_v1.md) avant Go S2b |
| **Doctrine** | Intent orchestrateur · Outbox Postgres · Settlement Layer · Reconciliation Controller gate · **5 règles non négociables** |

**Aucun code métier avant validation explicite de ce ticket.**

---

## Gel court terme (focus plateforme S1→S5)

**Ne pas toucher** en parallèle du chantier orchestrateur :

- Custody / doctrine Base-only
- Ledger existant (écritures directes legacy — jusqu’à flags ON)
- Swaps / réconciliations ops (maintenance, audits)
- Portfolio Breakdown (PR C — stabilisé)

**100 % effort plateforme** sur **S1 → S4 → S5** : c’est le passage de quelques centaines à plusieurs milliers d’utilisateurs sans dette comptable nouvelle.

### Avant → Après (pourquoi ce chantier)

| Avant | Après (cible) |
| --- | --- |
| API écrit ledger, PE, swap, vault, bundle en parallèle | Settlement Layer seul writer (ADR 004) |
| Webhook écrit ledger directement | Intent technique + outbox (S6) |
| Cron répare après coup | Controller gate COMPLETED (S3) |
| Swap confirmé, ledger incomplet | Pipeline intent → outbox → worker → settle → reconcile |
| Crédit webhook sans débit swap | Matching swap + settlement unifié (S6) |

La théorie (ADR 001–004 + #25) est complète **avant** d’écrire la plateforme — aligné pratique fintech sérieuse.

---

## Objectif

Prouver en **staging** que le pipeline transactionnel orchestré fonctionne de bout en bout pour les **swaps LI.FI standalone** (`person_wallet_swaps`, hors `is_bundle_internal_swap`), avec **dual-run** : le flux legacy Phase 7 reste actif quand les feature flags sont OFF.

---

## Périmètre

### In scope

- Swap LI.FI standalone uniquement
- Flow : `quote` → `confirm-execute` → `approval` → `submit` → poll → settle → reconcile → `COMPLETED`
- Migrations additives : `transaction_outbox`, `transaction_intent_transitions`, extensions `transaction_intents`
- Worker outbox via extension du **tick DeFi** (`defi_observability_tick`)
- 3 feature flags (défaut `false`)
- 9 tests CI obligatoires
- Staging dual-run + procédure rollback (flags OFF)

### Out of scope (explicitement reporté)

- Bundle legs (`is_bundle_internal_swap`)
- Vault Morpho / Ledgity
- Lombard borrow / repay
- Exchange custodial
- Product locks (reportés en **S4** du planning révisé — avant staging S5)
- SQS, Redis Streams, Temporal, Celery
- Blocage UI effectif en prod (log-only en POC ; flag séparé)
- Endpoint admin timeline complet (debug SQL acceptable en POC)
- **Webhook Privy deposit orchestrator** (voir **Phase 2b** ci-dessous — doctrine ADR 004 §6)

---

## Références

| Document | Lien |
| --- | --- |
| ADR 001 — Intent Orchestrator | [001-intent-as-orchestrator.md](adr/001-intent-as-orchestrator.md) |
| ADR 002 — Outbox Postgres | [002-postgresql-outbox-canonical-queue.md](adr/002-postgresql-outbox-canonical-queue.md) |
| ADR 003 — Reconciliation Controller | [003-final-reconciliation-controller.md](adr/003-final-reconciliation-controller.md) |
| ADR 004 — Ledger Authority | [004-ledger-authority.md](adr/004-ledger-authority.md) |
| Index + spec détaillée | [adr/README.md](adr/README.md) |
| Historique Phase 7 (legacy) | [../arquantix/TRANSACTION_INTENTS_DEFI.md](../arquantix/TRANSACTION_INTENTS_DEFI.md) |

---

## Checklist livrables

### 1. Migrations Alembic (additives only)

- [ ] **M1** — Table `transaction_outbox` (schéma ADR 002)
  - Colonnes : `id`, `intent_id`, `event_type`, `payload_json`, `status`, `attempt_count`, `max_attempts`, `next_retry_at`, `locked_by`, `locked_at`, `last_error`, `processed_at`, `created_at`, `correlation_id`
  - Index poll : `(status, next_retry_at)` WHERE `status IN ('pending', 'processing')`
  - Index : `(intent_id, created_at)`
- [ ] **M2** — Table `transaction_intent_transitions` (schéma ADR 001)
  - Colonnes : `id`, `intent_id`, `from_status`, `to_status`, `phase`, `actor`, `metadata_json`, `created_at`
  - Index : `(intent_id, created_at)`
- [ ] **M3** — Extensions `transaction_intents` (non-breaking)
  - `correlation_id`, `current_phase`, `requested_action`, `assets_json`, `expires_at`, `reconciliation_report_json`, `blocked_assets_json`
- [ ] **M4** — Migration réversible documentée ; pas de suppression de colonnes Phase 7

### 2. Feature flags

| Variable | Défaut | Description |
| --- | --- | --- |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `false` | Pipeline intent → outbox → worker sur quote/submit |
| `LIFI_OUTBOX_WORKER_ENABLED` | `false` | Step `process_transaction_outbox` dans tick DeFi |
| `LIFI_RECONCILIATION_BLOCK_ENABLED` | `false` | Blocage API si `RECONCILIATION_REQUIRED` ; `false` = log-only |

- [ ] **F1** — Variables documentées dans runbook / `.env.example` (sans modifier `.env` prod)
- [ ] **F2** — Rollback validé : les 3 flags à `false` → comportement Phase 7 inchangé
- [ ] **F3** — Tests couvrant flag OFF (régression legacy)

### 3. Couche outbox (repository + handlers)

- [ ] **O1** — `TransactionOutboxRepository` : insert, poll (`FOR UPDATE SKIP LOCKED`), mark processed / retry / dead-letter
- [ ] **O2** — Écriture atomique **`transaction_intents` + `person_wallet_swaps` + `transaction_outbox`** dans **une seule** transaction DB (quote) — **pas trois TX séparées**

### S1 — Test d’atomicité (fondation — priorité #1)

> **Piège classique** : intent, swap et outbox créés dans trois transactions différentes. Si ce test échoue, tout le reste est fragile.

**Test critique** (`test_transaction_outbox_atomicity.py`) — quasi plus important que tous les autres en S1 :

```text
# Scénario ROLLBACK
BEGIN
  create intent
  create person_wallet_swap (linked_id)
  create outbox (intent.created)
  FAIL volontaire (ex. contrainte, raise)
ROLLBACK
=> intent, swap, outbox : AUCUN n'existe

# Scénario COMMIT
BEGIN
  create intent
  create person_wallet_swap
  create outbox
COMMIT
=> les 3 existent, linked_id cohérent, correlation_id propagé
```

- [ ] **A1** — Test ROLLBACK : zéro row résiduelle sur les 3 tables
- [ ] **A2** — Test COMMIT : les 3 rows + FK / linked_id / idempotency_key cohérents
- [ ] **A3** — Même exigence sur `POST /swaps/{id}/submit` (swap update + outbox `provider_submitted`)
- [ ] **A4** — **Gate S1** : A1–A2 verts avant tout code S2

**Si ça marche, les fondations sont posées.**

> **Implémentation S1** : branche `feat/s1-transaction-outbox-foundation` — voir [`S1_REVIEW_REPORT.md`](S1_REVIEW_REPORT.md).
- [ ] **O3** — Catalogue events Phase 2 : `intent.created`, `intent.provider_submitted`, `intent.settle`, `intent.reconcile`
- [ ] **O4** — Backoff exponentiel : 5s → 30s → 2m → 10m → 30m → 1h (cap)
- [ ] **O5** — Dead-letter après `max_attempts=10` + log structuré alerte ops

### 4. Intent orchestrateur (API)

- [ ] **I1** — `POST /swaps/quote` : créer intent orchestrateur (`CREATED`) + `person_wallet_swap` + outbox `intent.created` (même TX) si flag ON
- [ ] **I2** — `POST /swaps/{id}/submit` : outbox `intent.provider_submitted` (même TX que `tx_hash`) si flag ON
- [ ] **I3** — `transaction_intent_transitions` : INSERT à chaque transition
- [ ] **I4** — `lifi_intent_sync.py` : bypass si `LIFI_INTENT_ORCHESTRATOR_ENABLED=true` (éviter double sync miroir)
- [ ] **I5** — Swaps bundle interne : toujours hors orchestrateur (comportement actuel)

### 5. Worker outbox (tick DeFi)

- [ ] **W1** — Nouvelle step `process_transaction_outbox` dans `tick_service.py`
- [ ] **W2** — Handler `intent.created` → `VALIDATED` → `QUEUED`
- [ ] **W3** — Handler `intent.provider_submitted` → poll LI.FI → `ONCHAIN_CONFIRMED` (sans settlement synchrone)
- [ ] **W4** — Handler `intent.settle` → `settle_transaction_intent_idempotently(intent_id)`
- [ ] **W5** — Handler `intent.reconcile` → `run_final_reconciliation(intent_id)`
- [ ] **W6** — Métriques outbox dans summary tick (`pending`, `processed`, `dead_letter`)
- [ ] **W7** — (Optionnel Phase 2b) Script ECS dédié si latence tick insuffisante

### 6. Settlement Layer (ADR 004 — seul writer ledger)

- [ ] **S1** — `settle_transaction_intent_idempotently(intent_id)` : **seul point d’entrée** d’écriture ledger pour le POC
- [ ] **S2** — Appelé uniquement par worker en phase `ONCHAIN_CONFIRMED → LEDGER_SETTLED` — pas par API HTTP si flag ON
- [ ] **S3** — Idempotence : clés ledger existantes (`lifi-swap:{id}:debit`, `:credit`) inchangées
- [ ] **S4** — Cost basis + trace events dans le même chemin (erreurs cost basis loggées, non bloquantes en POC)
- [ ] **S5** — Test CI : `lifi_execute_service` n’appelle pas `apply_swap_settlement` quand orchestrateur ON
- [ ] **S6** — Registre exceptions dual-run (chemins legacy flag OFF) documenté

### 7. Reconciliation Controller (version LI.FI)

- [ ] **R1** — `run_final_reconciliation(intent_id)` : checks provider/on-chain (LI.FI, RPC)
- [ ] **R2** — Checks ledger : débit + crédit présents, pas de doublon, montants cohérents
- [ ] **R3** — Checks UI projection : `available`, `swappable_balance`, `pending_settlement=0` si COMPLETED
- [ ] **R4** — Auto-repair : 1 tentative `settle_lifi_swap_idempotently` si jambes incomplètes
- [ ] **R5** — `passed=true` → `COMPLETED` ; sinon → `RECONCILIATION_REQUIRED` + `reconciliation_report_json`
- [ ] **R6** — `LIFI_RECONCILIATION_BLOCK_ENABLED=false` : log warning seulement (pas de blocage API en POC)

### 8. Tests CI obligatoires (9)

| # | Test | Fichier cible | Statut |
| --- | --- | --- | --- |
| 1 | Double submit même intent → 1 seul settlement | `test_lifi_intent_orchestrator_idempotency.py` | [ ] |
| 2 | Crash worker après `tx_hash` → reprise → COMPLETED | `test_lifi_intent_worker_recovery.py` | [ ] |
| 3 | Tx confirmée, ledger fail → retry settle → COMPLETED | `test_lifi_intent_settle_retry.py` | [ ] |
| 4 | Settlement idempotent (2e appel noop) | Réutilise `test_lifi_swap_ledger_idempotency.py` | [ ] |
| 5 | Outbox dead-letter après max attempts | `test_transaction_outbox_dead_letter.py` | [ ] |
| 6 | Intent + outbox même TX (rollback si outbox fail) | `test_transaction_outbox_atomicity.py` | [ ] |
| 7 | Controller KO → `RECONCILIATION_REQUIRED` | `test_lifi_reconciliation_controller.py` | [ ] |
| 8 | Flag OFF → flux legacy inchangé | `test_lifi_legacy_path_regression.py` | [ ] |
| 9 | Webhook crédit seul → auto-repair → COMPLETED | Extension `test_lifi_swap_reconciliation.py` | [ ] |

- [ ] **T0** — Suite exécutable : `pytest tests/test_lifi_intent_* tests/test_transaction_outbox_* -q`

### 9. Staging dual-run

- [ ] **ST1** — Déployer migrations en staging (additive)
- [ ] **ST2** — Activer flags ON sur env staging dédié
- [ ] **ST3** — 10 swaps manuels standalone : vérifier timeline SQL (intent → outbox → transitions → ledger)
- [ ] **ST4** — Vérifier qu’aucun swap bundle interne n’est affecté
- [ ] **ST5** — Simuler échec settlement → vérifier retry → COMPLETED ou RECONCILIATION_REQUIRED
- [ ] **ST6** — Rollback : flags OFF → swap legacy fonctionne comme avant

### 10. Rollback & runbook

- [ ] **RB1** — Procédure rollback documentée : 3 flags → `false`, redémarrage API si nécessaire
- [ ] **RB2** — Outbox `pending` en prod avec flags OFF : ignorée, pas d’effet de bord
- [ ] **RB3** — Runbook ops : consulter outbox dead-letter, requeue manuel (SQL documenté en POC)

---

## Flux cible (rappel)

```
POST /swaps/quote
  TX: intent (CREATED) + person_wallet_swap + outbox(intent.created)

Worker intent.created → VALIDATED → QUEUED

POST /swaps/{id}/submit
  TX: swap.tx_hash + outbox(intent.provider_submitted)

Worker intent.provider_submitted → ONCHAIN_CONFIRMED → outbox(intent.settle)
Worker intent.settle → LEDGER_SETTLED → outbox(intent.reconcile)
Worker intent.reconcile → COMPLETED | RECONCILIATION_REQUIRED
```

---

## Fichiers impactés (estimation)

| Fichier / module | Nature du changement |
| --- | --- |
| `alembic/versions/173_transaction_outbox.py` | Nouveau |
| `alembic/versions/174_transaction_intent_transitions.py` | Nouveau |
| `services/transaction_outbox/` | Nouveau package |
| `services/reconciliation_controller/` | Nouveau package (version LI.FI) |
| `services/lifi/lifi_quote_service.py` | Intent + outbox si flag ON |
| `services/lifi/lifi_execute_service.py` | Submit → outbox ; retirer settlement sync si flag ON |
| `services/lifi/lifi_swap_settlement.py` | Wrapper `settle_transaction_intent_idempotently` |
| `services/transaction_intents/lifi_intent_sync.py` | Bypass orchestrateur |
| `services/defi_observability/tick_service.py` | Step outbox worker |
| `tests/test_lifi_intent_*.py`, `tests/test_transaction_outbox_*.py` | Nouveaux |

---

## Critères de sortie (Definition of Done)

- [ ] Les 9 tests CI sont verts
- [ ] Staging : 10 swaps orchestrateur ON sans régression ledger
- [ ] Rollback flags OFF validé en staging
- [ ] Aucune régression sur bundle interne, vault, Lombard
- [ ] Métriques outbox visibles dans le summary du tick DeFi
- [ ] Revue code + revue ops validées
- [ ] Pas de déploiement prod flags ON sans validation staging explicite

---

## Roadmap plateforme (priorité validée)

Ordre d’exécution officiel — [Issue #25](https://github.com/geniusga-vancelian/vancelian-app/issues/25) :

| # | Milestone | Focus |
| --- | --- | --- |
| 1 | **S1** | Outbox — migrations + atomicité |
| 2 | **S2** | Intent orchestrateur LI.FI + worker handlers |
| 3 | **S3** | Reconciliation Controller (gate COMPLETED) |
| 4 | **S4** | **Product Locks** — concurrence swap + vault + bundle sur même asset |
| 5 | **S5** | Staging dual-run |
| 6 | **S6** | Webhook Privy deposits (Phase 2b) |
| 7+ | Post-POC | Bundle intents → Vault intents → Lombard intents |

### Risque principal à l’échelle

Ce n’est plus le webhook entrant. Le scénario le plus coûteux à des milliers d’utilisateurs :

```
Swap USDC  +  Vault Deposit USDC  +  Bundle Invest USDC
(lancés quasi simultanément sur le même solde)
```

**S4 Product Locks** est donc prioritaire **avant** S6 webhooks et **avant** généralisation bundle/vault. Les locks transactionnels valent plus que la migration des dépôts externes à court terme pour une trajectoire « mini Revolut ».

---

## Planning indicatif

| Semaine | Milestone | Focus |
| --- | --- | --- |
| S1 | Outbox | Migrations M1–M4 + repository outbox + test atomicité (T6) |
| S2 | Intent + Worker | Orchestrateur quote/submit (I1–I5) + handlers outbox (W1–W5) + settle (S1–S4) + tests recovery (T2, T3) |
| S3 | Controller | Reconciliation controller (R1–R6) + dead-letter (T5, T7, T9) |
| S4 | **Product Locks** | Table `transaction_product_locks`, middleware blocage, tests concurrence (T5 swap same asset) |
| S5 | Staging | Dual-run (ST1–ST6) + rollback (RB1–RB3) + revue |
| S6 | Webhooks | Phase 2b Privy deposit — **après** validation staging S5 |

### S4 — Product Locks (checklist)

**Granularité de base** : `person` · `wallet` · `asset` · `scope`

- [ ] **L1** — Table `transaction_product_locks` (ADR 001) — clé `person:{id}:wallet:{id}:asset:{symbol}`
- [ ] **L2** — Acquisition lock à `VALIDATED` ; release à terminal ou TTL
- [ ] **L3** — Règle LI.FI : lock `from_asset` sur swap pending
- [ ] **L4** — Règle cross-produit : refuse vault deposit / bundle invest si lock asset actif
- [ ] **L5** — Middleware API : 409 si action sensible sur asset locké par intent non-terminal
- [ ] **L6** — Tests : concurrent swap même asset ; vault deposit pendant swap pending

#### S4 — Optimistic balance version (recommandation forte)

En plus des locks exclusifs, capturer **`available_balance_version`** sur l’intent à `VALIDATED` :

| Champ | Exemple |
| --- | --- |
| `metadata.available_balance_version` | `42` (monotone par `person + wallet + asset`) |
| `metadata.available_balance_at_validation` | `100.00 USDC` |

**Scénario** :

```text
USDC disponible = 100, version = 42

Swap demande 100 USDC     → capture version 42 → VALIDATED
Vault demande 100 USDC    → capture version 42 → VALIDATED (quasi simultané)

Premier à acquérir lock / passer PROCESSING → gagne
Second à settlement/VALIDATED → BALANCE_VERSION_MISMATCH
  → intent FAILED ou retour VALIDATED avec retry (balance recalculée)
```

- [ ] **L7** — Source `available_balance_version` : snapshot PE / ledger à validation (même lecture que Portfolio Breakdown)
- [ ] **L8** — Re-vérification version avant `PROCESSING` et avant settlement
- [ ] **L9** — Réponse API : `BALANCE_VERSION_MISMATCH` (409) — pas de mutation ledger
- [ ] **L10** — Test : deux intents même version, même montant, un seul gagne
- [ ] **L11** — `balance_snapshot_hash` capturé à `VALIDATED` ; re-check avant `PROCESSING` → `BALANCE_CHANGED` si drift

**Pourquoi** : à 5k users / 50k intents/jour, **lock pessimiste + version/hash optimiste** protège plus que les webhooks (S6). Modèle courtage / banque.

---

## Risques & mitigations

| Risque | Mitigation |
| --- | --- |
| Régression prod | Flags défaut `false` ; dual-run |
| Bundle interne affecté | Exclusion explicite `is_bundle_internal_swap` |
| **Concurrence même asset** | **S4 Product Locks avant staging S5** |
| Latence tick (30s+) | Acceptable POC ; ECS worker dédié post-S5 |
| Controller trop strict | Log-only blocage ; tolérances BPS |
| Dette dual-run | Durée limitée ; suppression chemin legacy après validation prod |
| Webhook dépôt externe | Documenté ADR 004 §6 ; S6 après S5 — pas urgent vs locks |

---

## Phase 2b — Webhook Privy deposit (`observed_external_deposit`)

> **Hors POC LI.FI initial (S1–S5)** — livré après validation staging du swap orchestrateur, ou en parallèle si capacité équipe.
>
> Doctrine : [ADR 004 §6 — Dépôt crypto entrant](adr/004-ledger-authority.md#6-cas-particulier--dépôt-crypto-entrant-webhook-privy)

### Problème

Un dépôt crypto arrive **sans intent utilisateur préalable**. Aujourd’hui `webhook_service.py` écrit directement `person_wallet_deposits` + `increment_balance`, ce qui contourne intent → outbox → settlement → reconciliation et cause des conflits avec les swaps LI.FI (crédit destination sans débit source).

### Classification

| Type | `product_type` | Initiateur |
| --- | --- | --- |
| Action portail (futur) | `privy_deposit` | Utilisateur webapp |
| **Dépôt externe observé** | `observed_external_deposit` | Webhook Privy (intent **technique**) |

Les webhooks sont des **producteurs d’events**, pas des **écrivains ledger** (ADR 004).

### Flux cible

```
Privy webhook
  → verify signature (Svix)
  → dedupe chain_id + tx_hash + log_index + asset + wallet_address
  → upsert intent observed_external_deposit (même TX)
  → insert outbox deposit.observed (même TX)
  → worker
  → [si swap LI.FI SUBMITTED même tx_hash] lier intent swap — pas crédit standalone
  → [sinon] settlement layer → crédit ledger idempotent
  → reconciliation controller
  → COMPLETED | OUT_OF_SCOPE | RECONCILIATION_REQUIRED
```

### Feature flag

| Variable | Défaut | Effet |
| --- | --- | --- |
| `PRIVY_DEPOSIT_ORCHESTRATOR_ENABLED` | `false` | Webhook crée intent + outbox ; pas d’écriture ledger directe |

Rollback : flag `false` → comportement actuel `webhook_service.py` inchangé.

### Règles métier (résumé)

1. Webhook **ne crédite plus** ledger à terme — seulement `privy_webhook_events` + intent + outbox
2. Idempotence : `observed_deposit:{chain_id}:{tx_hash}:{log_index}:{asset}:{wallet}`
3. Dépôt = destination swap LI.FI `SUBMITTED` → lier au swap ; settlement swap gère la jambe crédit
4. Dépôt externe réel → settlement crédit via Settlement Layer
5. Chain hors scope (ex. Ethereum si custody = Base) → `OUT_OF_SCOPE` / informational ; pas d’impact custody Base ; pas de blocage compte
6. Wallet inconnu → dead-letter / `manual_review` ; pas de crédit auto

### Checklist Phase 2b

- [ ] **D1** — Refactor `webhook_service.py` : intent + outbox en TX ; retirer `create(deposit)` + `increment_balance` si flag ON
- [ ] **D2** — Handler worker `deposit.observed`
- [ ] **D3** — Settlement `settle_observed_external_deposit(intent_id)` dans Settlement Layer
- [ ] **D4** — Matching swap LI.FI par `tx_hash` + `to_asset` + wallet (règle 3 — anti double crédit)
- [ ] **D5** — Branch `OUT_OF_SCOPE` pour chains hors custody
- [ ] **D6** — Branch wallet inconnu → dead-letter + alerte ops
- [ ] **D7** — Controller checks dépôt (ADR 003 + ADR 004 §6)
- [ ] **D8** — Réutiliser `privy_deposit_intent_sync.py` / unifier `product_type=observed_external_deposit`

### Tests CI obligatoires Phase 2b

| # | Scénario | Résultat attendu |
| --- | --- | --- |
| D-T1 | Webhook reçu deux fois (même tx) | Un seul crédit ledger |
| D-T2 | Webhook pendant swap LI.FI `SUBMITTED` (même `tx_hash`) | Lié au swap ; pas de crédit standalone ; pas double crédit |
| D-T3 | Webhook chain hors scope (Ethereum) | Intent `OUT_OF_SCOPE` ; pas d’écriture ledger Base ; compte non bloqué |
| D-T4 | Webhook wallet inconnu | Dead-letter ou `manual_review` ; pas de crédit |
| D-T5 | Worker crash après intent + outbox créés | Reprise outbox → settlement → COMPLETED |
| D-T6 | Flag OFF | `webhook_service` legacy inchangé |

### Milestone GitHub

**S6 — Privy Deposit Orchestrator (Phase 2b)** — créé ; démarrer uniquement après validation staging **S5**. Voir commentaire architecture sur [#25](https://github.com/geniusga-vancelian/vancelian-app/issues/25#issuecomment-4640425224).

### Code existant (référence)

| Fichier | Rôle actuel |
| --- | --- |
| `privy_wallet/webhook_service.py` | Écriture ledger directe — **à refactorer** |
| `privy_wallet/webhook_verifier.py` | Svix — **conservé** |
| `transaction_intents/privy_deposit_intent_sync.py` | Classification `observed_external_deposit` — **à promouvoir orchestrateur** |

---

## S1 — clos ✅

| Livrable | Statut |
| --- | --- |
| Migration 173 | ✅ staging `arquantix_fresh` |
| `transaction_outbox` + `transaction_intent_transitions` | ✅ |
| Extensions `transaction_intents` | ✅ |
| Tests A1/A2 | ✅ |
| Phase 7 non régressée | ✅ |
| PR #27 | ✅ mergée |
| Milestone S1 | ✅ fermé |
| Runtime / flags | ✅ inchangés |

---

## S2 — verrou (pas de démarrage implicite)

**Feu vert requis** : mot explicite **« Go S2 »** — pas de code S2 sans cela.

### Interdictions S2 (jusqu’à feu vert ultérieur par milestone)

- Pas de flag ON en prod/staging
- Pas de settlement (`apply_swap_settlement`)
- Pas de reconciliation controller
- Pas de product locks
- Pas de submit / poll / worker `provider_submitted`

### Premier objectif S2 (scope ultra strict)

Prouver uniquement :

```
POST /swaps/quote (LI.FI)
  ↓
intent orchestrateur (même TX)
  ↓
outbox event intent.created
```

| # | Livrable S2a | Détail |
| --- | --- | --- |
| 1 | Flag | `LIFI_INTENT_ORCHESTRATOR_ENABLED=false` (défaut) |
| 2 | Quote | `lifi_quote_service` → `persist_intent_swap_outbox_atomic` si flag ON |
| 3 | Sync legacy | `lifi_intent_sync` bypass **seulement** si flag ON |
| 4 | Worker minimal | `intent.created` (flag `LIFI_OUTBOX_WORKER_ENABLED=false` par défaut) |
| 5 | Rollback | flag OFF → comportement Phase 7 **identique** |

**Gate S2a** : quote + intent + outbox en une TX ; legacy intact si flag OFF ; pas encore de traitement swap bout-en-bout.

### Anti-patterns S2 — interdits (risque disciplinaire, pas technique)

| Tentation | Pourquoi refuser |
| --- | --- |
| « Un petit `apply_swap_settlement` pour tester » | Contourne ADR 004 ; invalide la coexistence legacy |
| « Déjà appeler settlement si flag ON » | S2 ≠ S3 ; settlement = milestone suivant |
| « Worker `provider_submitted` tant qu’on y est » | Élargit le scope ; masque l’échec de coexistence |
| « Flag ON en staging pour voir » | S5 = staging dual-run ; pas avant |

**Seul succès S2a** : Legacy + Orchestrateur **coexistent** — flag OFF = comportement identique à aujourd’hui.

### S2a.1 — follow-up post-merge (#29)

| # | Livrable | Détail |
| --- | --- | --- |
| 1 | Test échec LI.FI flag ON | intent + swap FAILED + outbox `intent.created` ; pas ledger/PE |
| 2 | Assertions | `slippage_bps` / `expires_at` alignés swap ↔ intent |
| 3 | Note technique | Bypass `lifi_intent_sync` **global** si flag ON → traiter avant S5 dual-run |

**Verrou** : pas de S2b tant que S2a.1 non mergé. ✅

### S2b — worker `intent.created` (scope strict)

```
outbox intent.created
      ↓
worker (LIFI_OUTBOX_WORKER_ENABLED=false par défaut)
      ↓
current_phase: CREATED → VALIDATED → QUEUED
      ↓
outbox status: processed
```

**Tables touchées** : `transaction_intents`, `transaction_intent_transitions`, `transaction_outbox` uniquement.

**Hors scope** : settlement · controller · locks · `provider_submitted` · tables économiques · flag ON prod.

**Test review** : le worker peut être supprimé sans affecter une seule écriture économique.

### S2.5 — Settlement Skeleton NOOP (frontière Worker → Settlement) ✅

**PR #33** ✅ mergée.

**Objectif** : `settle_transaction_intent_idempotently(intent_id)` exécutable — **aucune écriture économique**.

```
Worker (futur intent.settle)
      ↓
services/settlement/settle.py  (S2.5 skeleton)
      ↓
SettlementResult { SUCCESS | RETRYABLE_FAILURE | TERMINAL_FAILURE | NOOP_ALREADY_SETTLED }
```

| Règle S2.5 | Détail |
| --- | --- |
| Pré-conditions | P1–P6 Contract v1 (lecture seule) |
| Écritures | **Aucune** ledger / PE / cost basis / legacy `apply_swap_settlement` |
| Persistance marker | **Aucune** en S2.5 (idempotence marker = S3a) |
| Review | Module `services/settlement/` supprimable sans impact économique |

**Test review S2.5** : *Le module settlement peut-il être supprimé sans modifier une seule réalité économique ?* → **Oui**

### S3a — Worker → Settlement NOOP branché (en cours)

**Objectif** : brancher le câble `intent.settle` → `settle_transaction_intent_idempotently()` — **aucune écriture économique**.

```
outbox intent.settle
      ↓
settlement_worker (LIFI_OUTBOX_WORKER_ENABLED=false par défaut)
      ↓
settle_transaction_intent_idempotently()  (module S2.5 inchangé)
      ↓
SettlementResult → metadata settlement_receipt_hash + phase SETTLED_NOOP
```

| Règle S3a | Détail |
| --- | --- |
| Handler | `intent.settle` uniquement |
| Settlement | `services/settlement/settle.py` — pas de remplacement |
| Écritures autorisées | `transaction_intents`, `transaction_intent_transitions`, `transaction_outbox` |
| Écritures interdites | ledger · PE · cost basis · legacy `apply_swap_settlement` |
| Outcomes | SUCCESS → hash persisté ; NOOP_ALREADY_SETTLED → processed ; RETRYABLE → retry ; TERMINAL → failed |
| Review | Supprimer handler `intent.settle` = réalité économique inchangée |

**Test review S3a** : *Si on supprime le handler intent.settle, la réalité économique reste-t-elle identique ?* → **Oui**

### Découpage S3 (officiel — après S2.5)

| Phase | Contenu | Écriture économique |
| --- | --- | --- |
| **S3a** | Worker → Settlement NOOP branché · retry · idempotence · checksum persisté | ❌ |
| **S3b** | Premier settlement réel LI.FI standalone · `person_wallet_balances` + `person_wallet_deposits` | ✅ minimal |
| **S3** (complet) | Controller gate COMPLETED · reconciliation | Selon milestone |

**Verrou** : pas de **Go S3** / S3b sans **S2.5** mergé · pas de settlement réel sans **Go S3b** explicite.

### Verrou gouvernance

```
Pas de « Go S2 » explicite = Pas de code S2
```

Le risque principal n’est plus de ne pas avancer assez vite — c’est d’**aller plus vite que l’architecture** définie.

---

## Prochaine action

1. ~~S1 fondation~~ — ✅ fait
2. ~~S2a quote orchestrateur~~ — ✅ mergé (#29)
3. ~~S2a.1~~ — ✅ mergé (#30)
4. ~~Settlement Layer Contract v1~~ — ✅ mergé (#31)
5. ~~**S2b** worker `intent.created`~~ — ✅ mergé (#32)
6. ~~**S2.5** Settlement Skeleton NOOP~~ — ✅ mergé (#33)
7. **S3a** Worker → Settlement NOOP branché — feu vert explicite requis
8. **S3b** Premier settlement réel LI.FI — feu vert explicite
9. **S3** Controller + reconciliation — zone dangereuse ADR 004
10. **S4** Product Locks avant staging final
11. **S5** Staging dual-run
12. **S6** webhooks Privy
