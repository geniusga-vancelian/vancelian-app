# Rapport final exécution — Go Pilot Prod Étape 3

| Champ | Valeur |
| --- | --- |
| **Date** | 2026-06-07 |
| **Compte** | `gaelitier@gmail.com` · `person_id` `8b0e0044-f1ef-47a5-99d4-370598a77492` |
| **Swap** | `6996ea11-aab1-4460-98fc-ea1ed4f7283c` · 1 USDC → ETH · Base |
| **PR patch idempotence** | [#39](https://github.com/geniusga-vancelian/vancelian-app/pull/39) · merge `677f8d86` |
| **Décision** | **STEP3_EVENT_DRIVEN_OK** · **CB drift +1** (hors S3b) |

---

## Résumé exécutif

La chaîne event-driven cible a été **complétée sur le swap existant** après merge/deploy de #39, sans second swap et **sans double crédit ETH**.

Le crédit webhook Privy a été **réutilisé** ; S3b a settlé en `LEDGER_SETTLED` avec **1 seul débit USDC** `lifi-swap:…:debit` et **0 nouveau crédit ETH**.

**Écart vs critères stricts** : `cost_basis_executions` est passé de **66 → 67** lors du tick (maintenance reconciliation LI.FI dans le même tick, pas S3b). PE inchangé (**19**). COMPLETED **0**.

Flags worker/ledger **rollback OFF** · TD finale **`arquantix-api:126`**.

---

## Chronologie ops

| Heure (UTC) | Action | Résultat |
| --- | --- | --- |
| 10:37 | Merge PR #39 → `main` | `677f8d86` |
| 10:37–10:44 | GHA deploy API | TD **`arquantix-api:124`** · image `677f8d86` · worker/ledger OFF |
| 10:46 | Re-audit idempotence S3b | **`SAFE_WEBHOOK_CREDIT_REUSE`** |
| 10:48 | Activate flags | TD **`arquantix-api:125`** · worker ON · ledger ON |
| 10:50 | Tick `defi_observability_tick` (ECS) | exit 2 (degraded acceptable) |
| 10:51 | Audit post-tick | `LEDGER_SETTLED` · pipeline OK · CB +1 |
| 10:53 | Rollback flags | TD **`arquantix-api:126`** · worker/ledger OFF |

---

## 1. Re-audit idempotence (pre-tick)

Verdict : **`SAFE_WEBHOOK_CREDIT_REUSE`**

| Check | Valeur |
| --- | --- |
| Crédit webhook | `65bedc29-…` · 0.000613653814797695 ETH |
| `would_write_debit` | true |
| `would_write_credit` | **false** |

---

## 2. Résultats post-tick (swap `6996ea11-…`)

### Outbox / intent

| Élément | Avant tick | Après tick |
| --- | --- | --- |
| `intent.created` | pending | **processed** @ 10:50:07 UTC |
| `intent.settle` | absent | **processed** · source **`auto_confirm_enqueue`** |
| Intent phase | `CREATED` | **`LEDGER_SETTLED`** |
| `settlement_receipt_hash` | null | présent |

Transitions : `CREATED` → `VALIDATED` → `QUEUED` → **`LEDGER_SETTLED`**.

### Ledger

| Jambe | Résultat |
| --- | --- |
| Débit USDC `lifi-swap:6996ea11-…:debit` | **1 créé** · 1.0 USDC · @ 10:50:06 UTC |
| Crédit `lifi-swap:…:credit` | **0** (webhook réutilisé) |
| Crédit ETH webhook | **1** (inchangé · `call_0x782a…_wallet.funds_deposited`) |

**Note** : le débit porte `sync_source=lifi_swap_reconciliation` (maintenance swap dans le tick, ~1 s avant le worker outbox). S3b a validé les jambes existantes via `detect_swap_ledger_legs` et a produit `LEDGER_SETTLED` sans second crédit.

### Compteurs globaux

| Métrique | Baseline | Post-tick | Attendu |
| --- | --- | --- | --- |
| PE atoms | 19 | **19** | ✅ inchangé |
| Cost basis | 66 | **67** | ❌ +1 |
| Legs `lifi-swap:%` | 116 | **117** | ✅ +1 débit seulement |
| COMPLETED orchestrateur | 0 | **0** | ✅ |
| dead_letter | 0 | **0** | ✅ |
| Autres users | 0 | **0** | ✅ |

---

## 3. Validation critères Étape 3

| Critère | Statut |
| --- | --- |
| UX + LI.FI + S2a.2 (session précédente) | ✅ |
| `intent.created` processed | ✅ |
| Auto-enqueue `intent.settle` | ✅ |
| `intent.settle` processed | ✅ |
| Phase `LEDGER_SETTLED` | ✅ |
| 1 débit USDC orchestrateur | ✅ |
| 0 nouveau crédit ETH | ✅ |
| Crédit webhook réutilisé | ✅ |
| PE inchangé | ✅ |
| CB inchangé | ❌ **67** (+1 reconciliation) |
| COMPLETED = 0 | ✅ |
| Rollback worker/ledger | ✅ `:126` |

---

## 4. Cause probable CB +1

Le tick `defi_observability_tick` exécute **`swap_maintenance`** avant le worker outbox. La reconciliation LI.FI (`settle_lifi_swap_idempotently`) peut créer une ligne **`cost_basis_executions`** si manquante — indépendamment de S3b (qui exclut PE/CB par design).

**Piste follow-up** : exclure les swaps orchestrateur allowlist actifs de l’ingest cost basis legacy dans le tick — PR **`fix/skip-legacy-cost-basis-orchestrator`** (`skip_legacy_cost_basis_for_orchestrator` dans `settle_lifi_swap_idempotently`).

---

## 5. État prod final

| Paramètre | Valeur |
| --- | --- |
| Task definition | **`arquantix-api:126`** |
| Image | `677f8d86` |
| `LIFI_OUTBOX_WORKER_ENABLED` | **false** |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | **false** |
| Orchestrator + allowlist | ON · `gaelitier@gmail.com` |

---

## 6. Décision

**Étape 3 — event-driven : VALIDÉE** sur le swap pilot, avec réserve **CB +1** (reconciliation tick, hors scope S3b).

Le patch #39 a rempli son objectif principal : **pas de double crédit ETH** sur un swap déjà crédité par webhook.

---

## Références

| Doc / artefact | Rôle |
| --- | --- |
| [GO_PILOT_PROD_STEP3_S3B_IDEMPOTENCE_INCIDENT.md](GO_PILOT_PROD_STEP3_S3B_IDEMPOTENCE_INCIDENT.md) | Incident pre-patch |
| [GO_PILOT_PROD_STEP3_POST_SWAP_AUDIT.md](GO_PILOT_PROD_STEP3_POST_SWAP_AUDIT.md) | Audit pre-tick |
| PR #39 | Patch idempotence webhook |
| `scripts/_pilot-step3-s3b-idempotence-audit-inline.py` | Re-audit idempotence |
| `scripts/_pilot-step3-post-swap-audit-inline.py` | Audit post-tick |
