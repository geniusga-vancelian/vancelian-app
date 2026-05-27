# Transaction intents DeFi (Phase 7 — 7D)

## Pourquoi intents ≠ ledger

| Couche | Rôle |
| --- | --- |
| **transaction_intents** | Trace l’**opération produit** (swap, vault, bundle) — cycle de vie métier |
| **person_wallet_deposits / balances** | Ledger comptable — mis à jour uniquement par settlement existant |
| **raw_onchain_events** | Preuve on-chain indexée |
| **reconciliation_discrepancies** | Écarts détectés — jamais corrigés automatiquement |

Les intents **ne remplacent pas** le ledger et **ne déclenchent pas** d’apply correction.

## Produits branchés

| Produit | Phase | Modèle |
| --- | --- | --- |
| LI.FI swap | 7 | 1 intent / swap |
| Morpho Earn | 7B | 1 intent / vault tx |
| Lombard Borrow | 7C | parent + steps |
| Bundle invest | 7D | parent + legs |

---

## LI.FI swap

`linked_table=person_wallet_swaps`, `linked_id=<swap_uuid>`  
Idempotence : `lifi_swap:<swap_id>`

---

## Morpho Earn

`integration_mode=direct_morpho`, deposit/withdraw uniquement.  
`linked_reference_id=<cuid>` · `morpho_earn:…`

---

## Lombard Borrow

Parent `lombard_borrow` + `metadata_json.steps` (approve, authorize, open_loan).  
`linked_table=onchain_vault_transactions_group`, `linked_reference_id=<groupKey>`

---

## Bundle invest (Phase 7D)

Périmètre : investissement crypto bundle via **LI.FI Base** (`BundleOrchestrator._invest_via_lifi`).  
**Un intent parent** + **legs** dans `metadata_json` — aucun changement settlement / PE atoms / locks.

### Statuts parent

| Situation orchestrateur / legs | Statut intent |
| --- | --- |
| début invest (lock acquis) | `awaiting_signature` |
| au moins un leg `submitted` + tx_hash | `submitted` |
| tous legs `confirmed` | `confirmed` |
| mix confirmed / pending / failed | `partial` |
| aucun leg confirmed | `failed` |
| incohérence / partial stale | `reconciliation_required` (réconciliation) |

### Legs (`metadata_json.legs`)

```json
{
  "leg_id": "bundle-alloc-<batch_id>-ETH",
  "swap_id": "<person_wallet_swaps.id>",
  "asset": "ETH",
  "target_weight": 0.5,
  "tx_hash": "0x…",
  "status": "pending|submitted|confirmed|failed",
  "linked_table": "person_wallet_swaps",
  "linked_id": "<swap_id>",
  "raw_onchain_event_id": null
}
```

### Mapping

| Champ | Valeur |
| --- | --- |
| `product_type` | `bundle_invest` |
| `operation_type` | `invest` |
| `linked_table` | `bundle_invest_lock` |
| `linked_reference_id` | `batch_id` (UUID string) |
| `bundle_id` (metadata) | `portfolio_id` PE |
| `idempotency_key` | `bundle_invest:<person_id>:<portfolio_id>:<batch_id>` |

Pas de table `bundle_batch` : le batch est l’UUID propagé dans le lock `pe_portfolios.metadata_.bundle_invest_lock` et l’audit swap `bundle_leg_context`.

### Hooks (Python, observabilité)

| Moment | Fichier |
| --- | --- |
| lock acquis | `orchestrator._invest_via_lifi` → `ensure_bundle_parent_intent` |
| quote leg / swap créé | `BundleLifiLegService.execute_leg` → `register_bundle_leg` |
| submit tx | `submit_leg_tx` → `mark_bundle_leg_submitted` |
| swap CONFIRMED + PE atoms | `_apply_post_confirmation` → `mark_bundle_leg_confirmed` |
| swap FAILED | `refresh_and_settle` → `mark_bundle_leg_failed` |
| fin invest / finalize | `sync_bundle_parent_from_batch_status` / `recompute_bundle_parent_intent` |

Échec sync : log warning, **flux bundle inchangé**.

Les intents `lifi_swap` per-leg (via `LifiExecuteService`) coexistent ; le parent bundle les référence par `swap_id`.

---

## Réconciliation intents

Layer `intent`, pas d’apply auto.

**Bundle (7D)** :

- `bundle_batch_without_parent_intent`
- `bundle_parent_confirmed_leg_not_confirmed`
- `bundle_parent_partial_stale`
- `bundle_leg_swap_confirmed_intent_leg_not_confirmed`
- `bundle_leg_failed_with_pe_atoms`
- `bundle_parent_failed_with_pe_atoms`
- `intent_tx_without_raw_link`

---

## Admin

- `/admin/onchain-reconciliation/intents` — filtre `bundle_invest`
- Détail discrepancy : table **legs** (asset, weight, swap_id, status, tx_hash)

---

## Phase 8 — Santé & TTL stale (branché)

### Politique TTL (minutes, défaut)

| Statut intent | TTL | Severity stale (produit) |
| --- | --- | --- |
| `awaiting_signature` | 60 | P2 (P1 Lombard/Bundle) |
| `submitted` | 45 | idem |
| `partial` | 120 | idem |
| `reconciliation_required` | 360 | idem |
| `confirming` / `created` | 45 / 60 | idem |

Surcharge env : `INTENT_TTL_<STATUS>_MINUTES`.

### Service `transaction_intent_health.py`

- Agrégats par `product_type` : total, by_status, stale, taux succès / partial
- `without_raw_onchain_event`, `submitted_too_old`, `confirmed_without_ledger` (LI.FI)
- `list_stale_intents` / `reconcile_stale_intents(dry_run=…)`
- **Ne modifie pas** les intents ni le ledger — crée uniquement `reconciliation_discrepancies` layer=`intent`, status=`open`

Types discrepancy stale : `intent_<status>_stale` (ex. `intent_submitted_stale`).

### CLI

```bash
cd services/arquantix/api
python3 -m scripts.transaction_intent_health --dry-run
python3 -m scripts.transaction_intent_health --no-dry-run
python3 -m scripts.transaction_intent_health --no-dry-run --person-id <UUID>
```

### Admin

- Dashboard : `/admin/onchain-reconciliation/health`
- API : `GET /api/admin/onchain-reconciliation/health`
- Reconcile stale : `POST /api/admin/onchain-reconciliation/health/reconcile-stale?dry_run=true`

---

## Tests

```bash
cd services/arquantix/api
python3 -m pytest tests/test_phase7_transaction_intents.py \
  tests/test_phase7b_morpho_transaction_intents.py \
  tests/test_phase7c_lombard_transaction_intents.py \
  tests/test_phase7d_bundle_transaction_intents.py \
  tests/test_phase8_transaction_intent_health.py -q
```

---

## Limites (Phase 8)

- Pas de daemon / cron intégré (script manuel ou cron externe).
- Pas d’apply auto sur intents stale.
- Pas de mutation des flux LI.FI / Morpho / Lombard / Bundle.
- `confirmed_without_ledger` : échantillon LI.FI (300 derniers).

---

## Phase 9 — Tick observabilité (branché)

Script unique : `python3 -m scripts.defi_observability_tick`  
Runbook : `docs/arquantix/DEFI_OBSERVABILITY_RUNBOOK.md`  
Admin jobs : `/admin/onchain-reconciliation/jobs`

## Phase 10 — Prod readiness (branché)

- Verrou `pg_try_advisory_lock` : second tick `--no-dry-run` → `skipped_locked`, exit `0`
- `--max-duration-seconds` : arrêt entre étapes → `timeout_degraded`
- Runbook prod : `docs/arquantix/DEFI_OBSERVABILITY_PROD_RUNBOOK.md`

## Phase 11 proposée

Alerting Slack/email optionnel (feature-flag), sans apply auto.
