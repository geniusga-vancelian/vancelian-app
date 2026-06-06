# S1 Review Report — Transaction Outbox Foundation

| Champ | Valeur |
| --- | --- |
| **Branche** | `feat/s1-transaction-outbox-foundation` |
| **Issue** | [#25 — Phase 2 LI.FI Intent Orchestrator POC](https://github.com/geniusga-vancelian/vancelian-app/issues/25) |
| **Milestone** | S1 — Migrations & Atomicity |
| **Statut** | Prêt pour review — **non mergé** |
| **Date** | 2026-06-07 |

---

## Objectif S1

Chantier de **fondation** uniquement — pas de chantier produit.

Poser les tables et le bundle atomique `intent + person_wallet_swap + transaction_outbox` avec tests gate #1, sans modifier le runtime LI.FI, ledger, PE, webhooks, worker ou feature flags prod.

---

## Livrables

| Livrable | Fichier / artefact | Statut |
| --- | --- | --- |
| Migration additive 173 | `alembic/versions/173_transaction_outbox_phase2_s1.py` | ✅ |
| Table `transaction_outbox` | migration + `services/transaction_outbox/models.py` | ✅ |
| Table `transaction_intent_transitions` | migration + models | ✅ |
| Extensions `transaction_intents` | migration + `onchain_indexer/models.py` | ✅ |
| Repository outbox | `services/transaction_outbox/repository.py` | ✅ |
| Bundle atomique (non branché runtime) | `services/transaction_outbox/atomic.py` | ✅ |
| Tests A1/A2 | `tests/test_transaction_outbox_atomicity.py` | ✅ (si migration 173 appliquée) |
| Downgrade migration | `downgrade()` dans 173 | ✅ documenté |

---

## Interdictions respectées

| Interdiction | Respect |
| --- | --- |
| Modifier flow LI.FI runtime | ✅ Aucun changement `lifi_quote_service` / `lifi_execute_service` |
| Activer worker outbox | ✅ Pas de step tick |
| Toucher settlement / ledger / PE | ✅ |
| Toucher webhooks | ✅ |
| Toucher bundle / vault / Lombard | ✅ |
| Feature flags ON | ✅ Aucun flag ajouté au runtime |

---

## Migration 173 — contenu

### `transaction_intents` (colonnes ajoutées)

- `correlation_id` (UUID, `gen_random_uuid()`)
- `current_phase` (default `created`)
- `requested_action`, `assets_json`, `expires_at`
- `reconciliation_report_json`, `blocked_assets_json`

### Nouvelles tables

- `transaction_intent_transitions` — append-only
- `transaction_outbox` — index poll partiel `(status, next_retry_at) WHERE pending|processing`

### Rollback

```bash
cd services/arquantix/api
alembic downgrade 172
```

Vérifie : tables outbox/transitions supprimées, colonnes intent retirées.

---

## Tests gate #1

```bash
cd services/arquantix/api
alembic upgrade head   # si pas déjà à 173
pytest tests/test_transaction_outbox_atomicity.py -v
```

| Test | Scénario |
| --- | --- |
| `test_a1_rollback_no_intent_swap_outbox_or_transition` | FAIL volontaire → nested rollback → 0 row |
| `test_a2_commit_intent_swap_outbox_present` | flush → intent + swap + outbox présents |
| `test_a2_correlation_linked_id_and_idempotency_coherent` | clés cohérentes |
| `test_outbox_repository_insert_standalone` | repository isolé |

**Gate S2** : A1 + A2 doivent être verts avant tout branchement orchestrateur LI.FI.

---

## Points de review

1. **Atomicité** : `persist_intent_swap_outbox_atomic` ne fait pas `commit()` — la TX est celle de l'appelant (API S2+ ou test).
2. **`atomic.py`** : module fondation explicitement non importé par `lifi_*` en S1.
3. **Extensions intent** : nullable / defaults compatibles rows Phase 7 existantes.
4. **Pas de worker** : `TransactionOutboxRepository` expose `insert_event` et `find_by_intent` seulement — poll `SKIP LOCKED` en S3.

---

## Prochaine étape (S2 — hors ce PR)

- Brancher `lifi_quote_service` sur `persist_intent_swap_outbox_atomic` derrière `LIFI_INTENT_ORCHESTRATOR_ENABLED=false` par défaut
- Worker `intent.created` dans tick DeFi

---

## Checklist reviewer

- [ ] Migration 173 upgrade/downgrade testée sur staging local
- [ ] Tests A1/A2 verts
- [ ] Aucun import `transaction_outbox` depuis `lifi_*`
- [ ] ADR 001/002 alignés avec schéma
- [ ] PR non mergée avant validation explicite CTO / #25
