# Bundle Ledger — Phase 4A (shadow mode)

**Date :** 2026-05-29  
**Statut :** implémenté — écriture miroir, lecture shadow, sans remplacement UI

---

## Objectif

Introduire un journal comptable append-only `bundle_ledger_entries` comme **audit trail structuré** des événements bundle, en **shadow mode** :

- Les **atoms PE** restent la source de vérité comptable court terme.
- Mon Trading, wallet history et bundle history **existants** ne changent pas.
- Le ledger s’alimente en **miroir** à chaque mutation métier confirmée.

---

## Modèle comptable cible

Chaque entrée décrit un mouvement ou un événement info sur un `bundle_portfolio_id` :

| Champ | Rôle |
|-------|------|
| `event_type` | Type métier (dépôt, retrait, allocation, rebalance, recovery…) |
| `asset_symbol` / `asset_instrument_id` | Actif concerné |
| `quantity` | Montant en unités native |
| `direction` | `debit` / `credit` / `info` (perspective bundle) |
| `source_system` | `pe_transfer`, `lifi`, `exchange`, `manual_recovery` |
| `source_id` | Clé source (batch, swap, leg…) |
| `batch_id` / `leg_id` | Corrélation opération |
| `status` | `pending`, `confirmed`, `failed`, `reversed` |
| `metadata` | Contexte debug (cost basis, swap_id, shadow_mode…) |

### Types d’événements

| Event | Déclencheur |
|-------|-------------|
| `BUNDLE_DEPOSIT` | `fund_bundle_cash_leg_from_self_trading` — crédit cash leg |
| `BUNDLE_WITHDRAWAL` | `release_bundle_cash_leg_to_self_trading` — débit cash leg vers self-trading |
| `BUNDLE_ALLOCATION_BUY` | `apply_allocation_leg_atoms` — crédit spot |
| `BUNDLE_CASH_RELEASED` | `apply_allocation_leg_atoms` — débit cash leg (consommation allocation) |
| `BUNDLE_ALLOCATION_SELL` | `apply_withdraw_sell_atoms` — vente spot (retrait) |
| `BUNDLE_REBALANCE_BUY` / `BUNDLE_REBALANCE_SELL` | rebalance Li.FI confirmé |
| `BUNDLE_RECOVERY_ADJUSTMENT` | expiration lock, finalize partiel, reversal manuel |

---

## Idempotence

Contrainte unique sur `idempotency_key` :

```
{source_system}:{source_id}:{event_type}:{direction}
```

Exemples :

- Dépôt : `pe_transfer:{batch_id}:fund:BUNDLE_DEPOSIT:credit`
- Allocation buy : `lifi:{swap_id}:BUNDLE_ALLOCATION_BUY:credit`

Un retry métier **ne duplique pas** l’entrée — le service retourne l’entrée existante.

---

## Corrections — jamais d’update destructif

Si une correction comptable est nécessaire :

1. **Ne pas** modifier une entrée existante.
2. Créer une entrée `BUNDLE_RECOVERY_ADJUSTMENT` avec direction inverse via `record_reversal_event()`.
3. L’entrée originale conserve `status=confirmed`.

---

## Exemples de flux

### Dépôt (invest fund-first)

```
self-trading USDC  ──fund──►  bundle cash leg USDC
```

Ledger (shadow) :

1. `BUNDLE_DEPOSIT` — credit USDC — `source_id={batch_id}:fund`

### Allocation Li.FI confirmée

```
bundle cash USDC  ──Li.FI──►  bundle spot CBBTC
```

Ledger :

1. `BUNDLE_ALLOCATION_BUY` — credit CBBTC — `source_id={swap_id}`
2. `BUNDLE_CASH_RELEASED` — debit USDC — `source_id={swap_id}:cash`

### Retrait

```
bundle spot  ──sell──►  bundle cash  ──release──►  self-trading
```

Ledger :

1. `BUNDLE_ALLOCATION_SELL` + crédit cash interne (metadata `withdraw_sell=true`)
2. `BUNDLE_WITHDRAWAL` — debit USDC — `source_id={batch_id}:release`
3. Optionnel : `BUNDLE_RECOVERY_ADJUSTMENT` info si finalize partiel

---

## Écritures miroir (hooks)

| Fichier | Hook |
|---------|------|
| `bundle_funding.py` | fund → deposit ; release → withdrawal |
| `pe_settlement.py` | allocation / withdraw sell / rebalance (via `ledger` context) |
| `bundle_lifi_leg_service.py` | passe `person_id`, `swap_id`, `batch_id`, assets au settlement |
| `bundle_invest_lock.py` | expiration → recovery event |
| `bundle_withdraw_lock.py` | expiration → recovery event |
| `withdraw.py` | finalize partiel → recovery info |

---

## Endpoint lecture shadow

```
GET /api/app/bundle/{portfolio_id}/ledger
  ?batch_id=...   (optionnel)
  &limit=200
```

Réponse :

- `entries` — journal complet
- `cash_movements` — dépôts, retraits, cash released
- `allocation_movements` — buys/sells/rebalance
- `recovery_events` — locks, finalize, reversals
- `source_links` — corrélation source_system / source_id
- `shadow_mode: true`

**Ne remplace pas** `GET /api/app/bundle/{portfolio_id}/transactions`.

---

## Script ops / inspection

Le script existant `scripts/inspect_bundle_state.py` reste la référence ops temps réel (locks, cash leg, swaps).

Le ledger complète l’**historique comptable** ; l’inspect reste l’**état courant**.

---

## Migration

```bash
cd services/arquantix/api
alembic upgrade head   # révision 169 — bundle_ledger_entries
```

Table : `public.bundle_ledger_entries`

---

## Tests

```bash
pytest tests/test_bundle_ledger_phase4a.py -q
```

Couverture :

- deposit / withdrawal mirror writes
- allocation buy / withdraw sell ledger only
- idempotence retry
- reversal sans update destructif
- ledger absent de Mon Trading
- lecture shadow `list_bundle_ledger_entries`

---

## Stratégie Phase 4B (future)

1. **Backfill** — rejouer audit events + swaps confirmés → ledger (script one-shot read-only puis insert idempotent).
2. **Projection** — `list_bundle_portfolio_transactions` lit d’abord le ledger, fallback audit/intents pour legacy.
3. **Source unique UI** — bundle history basculé sur ledger ; Mon Trading **inchangé** (filtres PE transfers only).
4. **Réconciliation** — job compare somme ledger cash vs cash leg PE ; alerte si écart.

Phase 4A ne fait **aucune** de ces étapes — uniquement shadow write + read endpoint.

---

## Shadow reconciliation before Phase 4B (Phase 4A.5)

Avant tout backfill ou bascule UI, exécuter la réconciliation shadow :

```bash
python3 -m scripts.reconcile_bundle_ledger_shadow \
  --person-id <UUID> --portfolio-id <UUID> [--fail-on-diff]
```

**Verdict attendu pour un bundle post-4A :** `MATCH`  
**Legacy pre-4A :** `INCOMPLETE` acceptable si balances PE internes cohérentes — backfill 4B requis.

| Verdict | Signification | Bascule 4B ? |
|---------|---------------|--------------|
| MATCH | Ledger = PE | Oui (après panel ops) |
| INCOMPLETE | Entrées legacy manquantes | Non — backfill d’abord |
| DIFF | Écart balance ou anomalie | Non — investiguer |

Documentation complète : [BUNDLE_LEDGER_RECONCILIATION.md](./BUNDLE_LEDGER_RECONCILIATION.md)

Admin : `GET /api/admin/bundles/{portfolio_id}/ledger/reconciliation`

Tests : `tests/test_bundle_ledger_reconciliation.py`

---

## Fichiers livrés

| Fichier |
|---------|
| `alembic/versions/169_bundle_ledger_entries.py` |
| `services/portfolio_engine/bundle_ledger/enums.py` |
| `services/portfolio_engine/bundle_ledger/models.py` |
| `services/portfolio_engine/bundle_ledger/service.py` |
| `services/portfolio_engine/bundle_ledger/reconciliation.py` |
| `scripts/reconcile_bundle_ledger_shadow.py` |
| `tests/test_bundle_ledger_phase4a.py` |
| `tests/test_bundle_ledger_reconciliation.py` |

---

*Phase 4A — shadow mode. Atoms PE = vérité court terme. Ledger = audit trail structuré.*
