# S3 Controller v1 — LI.FI standalone reconciliation

Document de référence pour la première couche **Controller** post-settlement sur les swaps LI.FI standalone.

## Objectif

Après `LEDGER_SETTLED`, le Controller **relit la réalité** (tx_hash, webhooks Privy, jambes ledger S3b, montants DB) et **compare** sans écrire d’état économique. Il marque l’intent `RECONCILED` ou un échec de réconciliation — **pas `COMPLETED` en v1**.

```
Intent → Outbox → Worker → Product Lock → Settlement → Ledger → Controller → RECONCILED
```

## Périmètre v1 (strict)

| Inclus | Exclu |
|--------|--------|
| `product_type = lifi_swap` | Bundle, Vault, Lombard |
| LI.FI standalone | `bundle_internal_swap` |
| Phase entrante `LEDGER_SETTLED` | Cron / activation prod auto |
| Lecture + transitions phase | Auto-repair, écriture ledger/PE/CB |

## Interface

```python
from services.controller.lifi_swap_controller import reconcile_lifi_swap_intent

result = reconcile_lifi_swap_intent(db, intent_id)
# result.outcome ∈ RECONCILED | RECONCILIATION_RETRYABLE_FAILURE | RECONCILIATION_TERMINAL_FAILURE | NOOP_ALREADY_RECONCILED
```

Fichiers :

- `services/controller/lifi_swap_controller.py` — logique principale
- `services/controller/result.py` — `ReconciliationResult`, `ReconciliationOutcome`
- `services/transaction_outbox/intent_phases.py` — phases `RECONCILED`, `RECONCILIATION_*`

## Entrée

1. Intent avec `current_phase = LEDGER_SETTLED`
2. `settlement_receipt_hash` présent dans `metadata_json`
3. Swap lié avec `tx_hash`
4. `balance_snapshot` dans `metadata_json` si Product Locks actif — sinon warning, pas de check balance stricte

## Vérifications

### Jambes ledger

- Exactement **1 débit** source (`from_asset`, `amount_in`)
- Exactement **1 crédit** destination (`to_asset`, `amount_out` / `estimated_receive` avec tolérance 2 %)
- Crédit webhook réutilisé accepté (même tx_hash, pas de double écriture settlement)
- Pas de double débit / double crédit
- `tx_hash` cohérent entre swap et jambes

### Balance (si snapshot présent)

Ne **pas** utiliser seulement `balance_before - balance_after`.

Le Controller explique la variation :

```
expected_end = snapshot.available - swap_debit + external_net
```

où `external_net` = crédits externes − débits externes sur la fenêtre `[swap.created_at, swap.confirmed_at]`, **hors** jambes swap.

Un dépôt externe pendant le swap ne doit pas produire un faux « débit absent ».

### Hors scope écriture

Autorisé :

- `transaction_intents.current_phase`
- `transaction_intent_transitions`
- `metadata_json.reconciliation_report_hash` (succès)

Interdit :

- Ledger, PE, cost basis, mutation balance wallet (lecture stricte `query().first()`, pas de `get_or_create`)
- `COMPLETED`

## Outcomes

| Outcome | Phase | Cas typiques |
|---------|-------|--------------|
| `RECONCILED` | `RECONCILED` | 1 débit + 1 crédit, montants/assets OK |
| `RECONCILIATION_RETRYABLE_FAILURE` | `RECONCILIATION_RETRYABLE_FAILURE` | `tx_hash` manquant, débit/crédit absent |
| `RECONCILIATION_TERMINAL_FAILURE` | `RECONCILIATION_TERMINAL_FAILURE` | double crédit, mauvais asset/montant, balance inexpliquée |
| `NOOP_ALREADY_RECONCILED` | (inchangé) | 2ᵉ appel sur intent déjà `RECONCILED` |

## Idempotence

- Intent déjà `RECONCILED` → `NOOP_ALREADY_RECONCILED`, même hash, pas de nouvelle transition
- Aucune duplication ledger

## Projection (debug / audit)

Le rapport canonique inclut :

```json
{
  "expected_debit": {"asset": "USDC", "amount": "10"},
  "expected_credit": {"asset": "ETH", "amount": "0.00475"},
  "observed_debit": { "...": "..." },
  "observed_credit": { "...": "..." },
  "external_movements": [],
  "warnings": []
}
```

Hash SHA-256 → `metadata_json.reconciliation_report_hash`.

## Tests

Suite : `tests/test_controller_lifi_swap_v1.py`

- Nominal → `RECONCILED`
- Crédit webhook réutilisé → `RECONCILED`
- Dépôt externe + snapshot → `RECONCILED`
- Débit/crédit absent → retryable
- Double crédit / mauvais asset / mauvais montant → terminal
- `tx_hash` manquant → retryable
- Idempotence `RECONCILED`
- PE / CB / deposits / balances inchangés
- Pas de `COMPLETED`

## Évolutions futures (hors v1)

- `RECONCILED` → `COMPLETED`
- Bundle (n outputs, n tx_hash)
- Lombard (collateral, borrow, repay)
- Worker / cron Controller
- Réparation automatique
