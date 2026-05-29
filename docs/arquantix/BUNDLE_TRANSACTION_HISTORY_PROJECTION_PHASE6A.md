# Phase 6A — Bundle transaction history projection

**Date :** 2026-05-29  
**Type :** projection UX pure — aucune modification comptable

---

## Problème observé

Après investissement 80 USDC dans « Crypto Majors » :


| Vue              | Avant                             | Après Phase 6A                             |
| ---------------- | --------------------------------- | ------------------------------------------ |
| Mon Trading USDC | Transfer −80 ✅ + swap USDC→LINK ❌ | Transfer −80 uniquement                    |
| Détail bundle    | Transfer −80 ❌                    | Dépôt +80 ✅                                |
| Détail bundle    | Pas d’allocation agrégée          | Allocation · Crypto Majors (agrégat batch) |


Référence audit : `[BUNDLE_TRANSACTION_HISTORY_UX_AUDIT.md](./BUNDLE_TRANSACTION_HISTORY_UX_AUDIT.md)`

---

## Modèle cible

Deux projections explicites entre sources de vérité (PE, ledger, swaps) et l’API/UI :

### A. `self_trading_transaction_projection`

**Fichier :** `services/portfolio_engine/bundle_execution/self_trading_projection.py`

- Inclut : `bundle_pe_transfer` debit (fund), credit (release)
- Exclut : swaps internes, `bundle_internal_swap`, `portfolio_scope=bundle` swaps, dépôts Privy liés, signaux batch forts sans tag complet

**Intégration :** sortie de `TestClientService.get_crypto_transactions()`

### B. `bundle_transaction_projection`

**Fichier :** `services/portfolio_engine/bundle_execution/bundle_projection.py`

- `bundle_deposit` → credit, titre « Dépôt · {name} », +amount
- `bundle_withdrawal` → debit, titre « Retrait · {name} », −amount
- Legs `bundle_internal_swap` / ledger allocation → agrégat par `batch_id`
- Legs brutes **non exposées** dans la liste principale (présentes dans `expandable_legs`)

**Intégration :** sortie de `list_bundle_portfolio_transactions()`

---

## Flag rollback

```bash
BUNDLE_TRANSACTION_PROJECTION_V2_ENABLED=false
```

Default : `**true**`

Désactive les deux projections — comportement legacy (signes négatifs côté bundle, pas d’agrégat).

Aucune migration DB. Endpoints inchangés.

---

## Exemple payload allocation agrégée

```json
{
  "transaction_kind": "bundle_allocation_aggregate",
  "direction": "info",
  "title": "Allocation · Crypto Majors",
  "amount_crypto": "64",
  "asset": "USDC",
  "status": "completed",
  "bundle_batch_id": "…",
  "legs_count": 4,
  "successful_legs_count": 4,
  "failed_legs_count": 0,
  "expandable_legs": [
    {
      "from_asset": "USDC",
      "to_asset": "LINK",
      "amount_in": "16",
      "amount_out": "0.5",
      "status": "confirmed"
    }
  ]
}
```

---

## Frontend

- `TransactionProjectionContext` : `self_trading` | `bundle`
- `mapCryptoTransactionToHistoryItem(tx, currency, { projectionContext })`
- Bundle route : **pas** de `consolidateSwapTransactions` (backend agrège déjà)
- `PortalCryptoWalletDetailScreen` → `self_trading`
- `PortalCryptoWalletBundleDetailScreen` → `bundle`
- Variant UI `allocation` pour agrégats

---

## Swaps mal taggés

- `swap_has_strong_bundle_batch_context()` : batch_id + portfolio_id dans audit → exclu self-trading, visible bundle
- `detect_suspected_bundle_internal_swap_without_context()` : log warning + exclusion défensive sur signaux forts (source bundle, titre allocation, etc.)

---

## Tests

### Backend (`tests/test_bundle_transaction_projection_phase6a.py`)

- `test_usdc_history_excludes_bundle_allocation_swap`
- `test_usdc_history_shows_transfer_to_bundle_negative`
- `test_bundle_history_shows_deposit_positive`
- `test_bundle_history_aggregates_allocation_by_batch`
- `test_bundle_history_does_not_show_raw_lifi_legs_by_default`
- `test_bundle_history_with_ledger_flag_off_still_correct_sign`
- `test_bundle_history_with_ledger_flag_on_shows_allocation`
- `test_bundle_internal_swap_missing_context_is_detected`

### Frontend (`cryptoTransactionHistoryFormat.test.ts`)

- Bundle deposit positive (contexte bundle)
- Transfer to bundle negative (self-trading)
- Allocation aggregate visible
- Raw USDC→LINK absent self-trading
- `bundle_internal_swap` jamais formaté en échange

---

## Fichiers modifiés


| Fichier                                          | Changement                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------ |
| `projection_config.py`                           | Flag V2                                                            |
| `self_trading_projection.py`                     | **Nouveau**                                                        |
| `bundle_projection.py`                           | **Nouveau**                                                        |
| `bundle_transaction_scope.py`                    | `swap_has_strong_bundle_batch_context`, `is_bundle_portfolio_swap` |
| `self_trading_transactions.py`                   | Exclusion batch fort                                               |
| `bundle_portfolio_transactions.py`               | Projection bundle en sortie                                        |
| `bundle_ledger/history.py`                       | Deposit/withdrawal mapping bundle-friendly                         |
| `test_clients/service.py`                        | Projection self-trading en sortie                                  |
| `cryptoTransactionHistoryFormat.ts`              | Contexte projection + variant allocation                           |
| `cryptoWalletTypes.ts` / `cryptoWalletFormat.ts` | Champs agrégat                                                     |
| `PortalCryptoWallet*Screen.tsx`                  | projectionContext                                                  |
| `bundle/[portfolioId]/route.ts`                  | Pas de consolidation aveugle                                       |


**Non modifiés :** écritures PE, `bundle_ledger_entries`, moteur allocation, balances.

---

## Rollback procédure

1. `BUNDLE_TRANSACTION_PROJECTION_V2_ENABLED=false` → redémarrer API
2. Si problème frontend seul : revert formatter / screens (backend reste compatible)
3. Pas de rollback DB requis

---

## Preuve comportementale (tests automatisés)

1. USDC page : seulement transfer −80, pas de LINK
2. Bundle page : deposit +80 (`bundle_deposit`, direction credit)
3. Bundle page : `bundle_allocation_aggregate` avec legs en metadata
4. Mon Trading : aucun `bundle_internal_swap` / swap batch bundle

```bash
cd services/arquantix/api
python3 -m pytest tests/test_bundle_transaction_projection_phase6a.py -q

cd services/arquantix/web
node --import tsx --test src/lib/portal/cryptoTransactionHistoryFormat.test.ts
```

