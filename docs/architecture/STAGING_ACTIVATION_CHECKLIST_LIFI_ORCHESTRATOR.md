# Checklist d’activation staging — LI.FI Intent Orchestrator (Phase 2)

| Champ | Valeur |
| --- | --- |
| **Statut** | **Actif — pré-requis staging dual-run (S5)** |
| **Date** | 2026-06-07 |
| **Prérequis code** | S1–S3b ✅ mergés (#27–#35) sur `main` |
| **Epic** | [Issue #25](https://github.com/geniusga-vancelian/vancelian-app/issues/25) |
| **Références** | [PHASE2_POC_LIFI_STANDALONE_SWAP.md](PHASE2_POC_LIFI_STANDALONE_SWAP.md) · [SETTLEMENT_LAYER_CONTRACT_v1.md](SETTLEMENT_LAYER_CONTRACT_v1.md) · [TRANSACTION_ENGINE_GOVERNANCE.md](TRANSACTION_ENGINE_GOVERNANCE.md) |

---

## Ordre officiel (ne pas inverser)

```
S3b merged ✅
      ↓
Activation checklist staging  ← ce document
      ↓
S4 Product Locks
      ↓
S5 Staging dual-run
      ↓
S3 Controller / reconciliation  (Go explicite — pas avant S4 + S5)
```

**Interdit** : activer le controller (S3 complet), `COMPLETED`, ou flags **prod** avant validation staging.

---

## Principe

S3b a ouvert le **ledger custody minimal** derrière des flags **OFF** par défaut. Le code économique est **dormant** en prod.

Avant d’aller plus loin, staging doit prouver :

| Propriété | Critère |
| --- | --- |
| Flags OFF | Legacy inchangé (`apply_swap_settlement` actif, pas d’orchestrateur) |
| Flags ON (staging) | Settlement Layer écrit **exactement 1 débit + 1 crédit** par swap standalone |
| Rollback flags OFF | Retour legacy **immédiat** sans dette orpheline |

---

## Flags Phase 2 — orchestrateur LI.FI

| Variable | Défaut `main` | Rôle | Activer en staging ? |
| --- | --- | --- | --- |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `false` | Quote → intent + outbox `intent.created` | **Étape 2** (après smoke OFF) |
| `LIFI_OUTBOX_WORKER_ENABLED` | `false` | Tick : handlers `intent.created` + `intent.settle` | **Étape 3** (avec orchestrateur) |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | `false` | Settlement réel : 1 débit + 1 crédit via `services/settlement/` | **Étape 4** (dernier — ledger réel) |

### Flags hors périmètre activation (ne pas toucher pour ce chantier)

| Variable | Note |
| --- | --- |
| `LIFI_SWAPS_ENABLED` | Déjà actif swap produit — ne pas confondre avec orchestrateur |
| `LIFI_SWAPS_MOCK` | Mock local uniquement — pas pour validation staging réel |
| Controller / `COMPLETED` | **S3 complet verrouillé** — pas de flag dans cette checklist |

### Interdiction absolue

```
❌ LIFI_*_ENABLED=true en PRODUCTION
❌ Activation sans feu vert explicite documenté (ticket + date + opérateur)
❌ Activation S3 Controller avant S4 + S5 validés
```

---

## Ordre d’activation staging (séquentiel)

### Étape 0 — Baseline flags OFF

- [ ] Confirmer les 3 flags à `false` sur l’env staging cible
- [ ] Redémarrer API si variables lues au boot
- [ ] Exécuter smoke tests OFF (§ Smoke tests)
- [ ] **Go Étape 0** : legacy régression OK

### Étape 1 — Orchestrateur quote seul

```bash
LIFI_INTENT_ORCHESTRATOR_ENABLED=true
LIFI_OUTBOX_WORKER_ENABLED=false
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=false
```

- [ ] Quote crée intent + swap + outbox `intent.created`
- [ ] **Aucune** écriture ledger (`person_wallet_deposits` count inchangé sur personne test)
- [ ] `lifi_intent_sync` bypass actif (pas de double intent miroir)
- [ ] **Go Étape 1** : intent/outbox créés, ledger = 0

### Étape 2 — Worker phase (sans settlement réel)

```bash
LIFI_INTENT_ORCHESTRATOR_ENABLED=true
LIFI_OUTBOX_WORKER_ENABLED=true
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=false
```

- [ ] Tick / worker : `intent.created` → phases `VALIDATED` → `QUEUED`
- [ ] Enqueue manuel ou futur auto : outbox `intent.settle` traité en **NOOP** (`SETTLED_NOOP`)
- [ ] Marker `settlement_receipt_hash` présent, **pas** de jambe `lifi-swap:*:debit|credit`
- [ ] **Go Étape 2** : pipeline jusqu’à settlement NOOP OK

### Étape 3 — Settlement ledger réel (S3b)

```bash
LIFI_INTENT_ORCHESTRATOR_ENABLED=true
LIFI_OUTBOX_WORKER_ENABLED=true
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=true
```

- [ ] Swap standalone **CONFIRMED** + `tx_hash` + montants sur intent
- [ ] `intent.settle` → phase `LEDGER_SETTLED`
- [ ] Exactement **1 débit** + **1 crédit** (`lifi-swap:{swap_id}:debit|credit`)
- [ ] `apply_swap_settlement` = no-op (pas de double writer)
- [ ] 2ᵉ passage `intent.settle` → `NOOP_ALREADY_SETTLED`
- [ ] **Go Étape 3** : 10 swaps manuels OK (§ Campagne 10 swaps)

### Rollback immédiat (à tout moment)

```bash
LIFI_INTENT_ORCHESTRATOR_ENABLED=false
LIFI_OUTBOX_WORKER_ENABLED=false
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=false
```

- [ ] Redémarrer API
- [ ] Nouveau swap legacy : `apply_swap_settlement` produit 1 débit + 1 crédit
- [ ] Outbox `pending` existante : ignorée (pas d’effet de bord)
- [ ] **Go Rollback** : legacy identique à baseline Étape 0

---

## Smoke tests (automatisés)

Exécuter depuis `services/arquantix/api` :

```bash
cd services/arquantix/api
PYTHONPATH=. pytest tests/test_settlement_lifi_s3b.py -q
PYTHONPATH=. pytest tests/test_transaction_outbox_settlement_s3a.py -q
PYTHONPATH=. pytest tests/test_settlement_contract_s2_5.py -q
PYTHONPATH=. pytest tests/test_transaction_outbox_worker_s2b.py -q
PYTHONPATH=. pytest tests/test_lifi_orchestrator_quote_s2a.py -q
```

**Critère** : **tous verts** avant toute activation staging (26+ tests Phase 2 settlement/worker).

Tests gate S3b (référence) :

| # | Invariant |
| --- | --- |
| 1 | SUCCESS → 1 débit + 1 crédit |
| 2 | 2ᵉ passage → NOOP_ALREADY_SETTLED |
| 3 | Crédit webhook → pas double crédit |
| 4 | Débit existant → pas double débit |
| 5 | Échec débit/crédit → rollback (worker-path inclus) |
| 6 | Pas de PE |
| 7 | Pas de COMPLETED |
| 8 | Flag OFF → legacy inchangé |

---

## Campagne — 10 swaps manuels standalone (staging)

**Périmètre** : LI.FI standalone same-chain (ex. Base USDC→ETH), **pas** bundle interne.

| # | Swap | Quote OK | Intent créé | Outbox `intent.created` processed | Swap CONFIRMED | `intent.settle` processed | 1 débit + 1 crédit | Phase `LEDGER_SETTLED` | 2ᵉ settle NOOP | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 2 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 3 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 4 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 5 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 6 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 7 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 8 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 9 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| 10 | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

**Contrôles obligatoires par swap** :

- `product_type = lifi_swap`
- Pas de `bundle_execution` dans `audit_log`
- Idempotency keys : `lifi-swap:{swap_id}:debit` et `:credit`
- `metadata_json.settlement_receipt_hash` présent après succès
- `status` intent **≠** `completed` (pas de controller)

---

## Requêtes SQL de contrôle

Remplacer `:swap_id`, `:person_id`, `:intent_id` par les UUID réels.

### Intent + phase + marker

```sql
SELECT id, status, current_phase, idempotency_key,
       metadata_json->>'settlement_receipt_hash' AS receipt_hash,
       linked_table, linked_id, product_type
FROM transaction_intents
WHERE id = :intent_id;
```

### Outbox timeline

```sql
SELECT id, event_type, status, attempt_count, last_error, processed_at, created_at
FROM transaction_outbox
WHERE intent_id = :intent_id
ORDER BY created_at;
```

### Transitions orchestrateur

```sql
SELECT phase, from_status, to_status, actor, created_at
FROM transaction_intent_transitions
WHERE intent_id = :intent_id
ORDER BY created_at;
```

### Jambes ledger swap (exactement 1 + 1)

```sql
SELECT direction, asset, amount, idempotency_key, status, metadata_json->>'source' AS source
FROM person_wallet_deposits
WHERE idempotency_key IN (
  'lifi-swap:' || :swap_id::text || ':debit',
  'lifi-swap:' || :swap_id::text || ':credit'
)
ORDER BY direction;
```

### Détection double écriture (doit retourner 0 ligne)

```sql
SELECT idempotency_key, COUNT(*) AS n
FROM person_wallet_deposits
WHERE idempotency_key LIKE 'lifi-swap:' || :swap_id::text || ':%'
GROUP BY idempotency_key
HAVING COUNT(*) > 1;
```

### Balances personne (avant / après swap)

```sql
SELECT asset, available_balance, pending_balance, updated_at
FROM person_wallet_balances
WHERE person_id = :person_id
ORDER BY asset;
```

### Exclusion bundle interne (audit)

```sql
SELECT id, audit_log
FROM person_wallet_swaps
WHERE id = :swap_id;
-- Vérifier : pas de bundle_leg_context avec bundle_execution=true
```

### Outbox pending / dead-letter (surveillance ops)

```sql
SELECT event_type, status, COUNT(*) AS n
FROM transaction_outbox
GROUP BY event_type, status
ORDER BY event_type, status;
```

### PE / cost basis — doivent rester inchangés (contrôle S3b)

```sql
-- Aucune nouvelle ligne liée au swap via settlement S3b
SELECT COUNT(*) FROM pe_position_atoms;  -- baseline vs post-campagne
SELECT COUNT(*) FROM cost_basis_executions WHERE created_at > :campaign_start;
```

---

## Critères Stop / Go

### STOP immédiat (rollback flags OFF)

| Signal | Action |
| --- | --- |
| Double débit ou double crédit sur même `idempotency_key` | STOP · rollback · incident |
| Jambe orpheline (débit sans crédit ou inverse) | STOP · rollback · incident |
| Bundle interne passé par settlement S3b | STOP · rollback |
| Écriture `pe_position_atoms` / `cost_basis_executions` via orchestrateur | STOP · rollback |
| `COMPLETED` produit sans Go S3 controller | STOP · rollback |
| `apply_swap_settlement` + settlement layer sur même swap (double writer) | STOP · rollback |

### GO staging Étape 3 (ledger réel)

| Critère | Requis |
| --- | --- |
| 10/10 swaps : 1 débit + 1 crédit | ✅ |
| 10/10 : 2ᵉ `intent.settle` = NOOP | ✅ |
| 0 bundle interne affecté | ✅ |
| Rollback flags OFF validé sur au moins 1 swap legacy | ✅ |
| Smoke tests CI verts sur commit déployé | ✅ |
| Pas d’incident STOP pendant campagne | ✅ |

### GO S5 dual-run (après cette checklist + S4)

- S4 Product Locks mergé
- Cette checklist **100 % cochée**
- Feu vert explicite CTO (« Go S5 staging dual-run »)

### Pas de GO (verrouillé)

| Milestone | Condition |
| --- | --- |
| **S3 Controller** | Pas avant S4 + S5 + feu vert « Go S3 » |
| **Prod flags ON** | Pas avant staging dual-run validé + runbook ops |
| **PE / cost basis dans settlement** | Milestone post-S3b explicite |

---

## Runbook rollback (résumé)

1. Mettre les 3 flags à `false`
2. Redémarrer instances API staging
3. Vérifier 1 swap legacy end-to-end
4. Consulter `transaction_outbox` pending (attendu : sans effet tant que worker OFF)
5. Documenter incident si STOP déclenché

---

## Sign-off

| Rôle | Nom | Date | Étape validée |
| --- | --- | --- | --- |
| Dev / Cursor | | | Smoke tests |
| Ops staging | | | Étape 0–3 |
| CTO | | | Go S5 dual-run |

---

## Prochaine action documentée

1. **Exécuter cette checklist** sur env staging dédié (flags séquentiels)
2. **S4 Product Locks** — avant staging final
3. **S5 Staging dual-run** — après S4 + sign-off checklist
4. **S3 Controller** — uniquement sur « Go S3 » explicite post-S5
