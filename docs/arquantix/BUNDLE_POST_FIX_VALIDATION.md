# Bundle Post-Fix Validation Report

**Date :** 2026-05-29  
**Périmètre :** validation post-corrections Phase 1/2 + Phase 3.5 légère  
**Type :** audit read-only + correctifs ciblés prod limitée

---

## Executive summary

Les corrections Phase 1/2 **tiennent la route** : 35+ tests passent, la règle centrale (swap bundle ≠ trade self-trading) est appliquée sur le chemin principal Mon Trading et renforcée sur privy deposits + wallet statistics (Phase 3.5).

**Verdict prod limitée :** GO avec réserves documentées (admin portfolio, PDF détail, pas de retry-failed-legs API).

---

## 1. Endpoints transactions crypto — matrice de validation

| Surface | Route / service | Swaps bundle exclus ? | PE transfers visibles ? | Historique bundle OK ? | Statut post-fix |
|---------|-----------------|----------------------|-------------------------|------------------------|-----------------|
| **Mon Trading** | `GET /api/app/crypto-positions/{asset}/transactions` | **Oui** | **Oui** (volontaire) | N/A | ✅ Validé + tests |
| **Wallet history** (NAV) | `GET /api/app/wallet/history` | N/A (ordres PE) | N/A | N/A | ✅ Ordres bundle filtrés scope direct/global |
| **Wallet statistics** | `GET /api/app/wallet/statistics/{asset}` | N/A | N/A | N/A | ✅ Phase 3.5 — filtre ordres bundle si scope ≠ bundle |
| **Privy deposits list** | `GET /api/app/privy-wallet/deposits` | N/A | N/A | N/A | ✅ Phase 3.5 — dépôts liés swap bundle exclus |
| **Bundle transactions** | `GET /api/app/bundle/{id}/transactions` | **Inclus** (interne) | **Inclus** | ✅ allocation/désallocation/PE | ✅ Validé |
| **Bundle history** | `GET /api/app/bundle/{id}/history` | N/A | N/A | ✅ scope bundle | ✅ OK |
| **Admin portfolio** | `GET /api/admin/customers/{person_id}/portfolio` | **Non** | **Non** | N/A | ⚠️ Gap connu — hors scope prod client |
| **Export PDF opération** | `GET /api/app/transactions/{id}/operation-statement.pdf` | N/A | PE non résolu | N/A | ⚠️ Gap détail/PDF |
| **Portal BFF** | `/api/portal/crypto-wallet/[asset]` | Via backend | Via backend | Via backend | ✅ |
| **Mobile Flutter BFF** | `/api/mobile/flutter/crypto-positions/...` | Via backend | Via backend | Via bundle routes | ✅ |

### Règle centrale — confirmée

> Un swap Li.FI `bundle_execution=true` **n'apparaît pas** dans Mon Trading ; seuls `bundle_pe_transfer` (TRANSFER_TO/FROM_BUNDLE) y sont visibles.

Tests : `test_bundle_internal_swap_excluded_from_get_crypto_transactions`, `test_bundle_pe_transfer_visible_in_self_trading_but_swap_not`, `test_bundle_leg_does_not_create_lifi_swap_intent`.

---

## 2. Locks — matrice de validation

| Mécanisme | Comportement attendu | Validé ? | Tests |
|-----------|---------------------|----------|-------|
| Invest lock TTL 120 min | Expire si pas de swap live | ✅ | `test_invest_lock_expires_after_stale_pending_signature` |
| Swap SUBMITTED vivant | Empêche expiration | ✅ | `test_invest_lock_not_expired_while_submitted_swap_alive` |
| Reconcile idle | Clear lock sans travail pending | ✅ | `test_invest_lock_cleared_by_reconcile_when_swaps_terminal` |
| Failed/partial invest | Non bloquant, cash leg intacte | ✅ | `test_partial_allocation_preserves_cash_leg_and_lock_status` |
| Withdraw failed_partial | Pas de release self-trading | ✅ | `test_withdraw_failed_partial_does_not_release_to_self_trading` |
| Withdraw finalize | Release cash confirmé only | ✅ | `test_withdraw_finalize_releases_only_confirmed_cash` |
| Withdraw lock TTL | Expire sans sell live | ✅ | `test_withdraw_lock_expires_when_no_live_sell` |
| Resume invest | Rebuild pending legs | ✅ | `test_resume_invest_rebuilds_pending_legs_from_lock` |
| active-lock API | reconcile_or_expire | ✅ | Code router mis à jour |

### Endpoints lock

| Endpoint | Rôle | Statut |
|----------|------|--------|
| `GET /bundle/invest/active-lock` | Reconcile + expire stale | ✅ |
| `POST /bundle/invest/resume` | Reprise legs pending | ✅ |
| `POST /bundle/batch/finalize` | Clear lock + recoverable cash | ✅ |
| `GET /bundle/withdraw/active-lock` | État withdraw | ✅ |
| `POST /bundle/withdraw/finalize` | Release PE | ✅ |
| `POST /bundle/{id}/rebalance` | Reconcile invest lock avant | ✅ |

---

## 3. Phase 3.5 — correctifs appliqués

| Fichier | Changement |
|---------|------------|
| `privy_wallet/service.py` | `filter_self_trading_privy_deposits` sur liste dépôts |
| `wallet_statistics/service.py` | `filter_self_trading_exchange_orders` si scope global/direct |
| `scripts/inspect_bundle_state.py` | **Nouveau** — inspection read-only ops |
| `tests/test_bundle_post_fix_filters.py` | **Nouveau** — non-régression Phase 3.5 |

---

## 4. Régressions recherchées — résultat

| Zone | Régression ? | Notes |
|------|--------------|-------|
| Self-trading swap Li.FI normal | **Non** | `test_self_trading_lifi_swap_still_creates_intent` |
| Transferts PE Mon Trading | **Non** | Toujours visibles |
| Bundle history swaps internes | **Non** | `list_bundle_portfolio_transactions` inchangé |
| Withdraw fund-first | **Non** | `test_bundle_withdraw.py` 11 tests passent |
| Invest lock acquire | **Non** | `test_bundle_invest_lock.py` passent |

---

## 5. Gaps restants (prod limitée acceptable)

| Priorité | Gap | Mitigation ops |
|----------|-----|----------------|
| P2 | Admin `_list_transactions` mélange bundle/direct | Utiliser inspect script + intents admin |
| P2 | PDF / détail transaction sans PE transfer | Export manuel via audit events |
| P3 | Pas d'API `retry-failed-legs` | Resume + rebalance + finalize |
| P3 | Pas de job cron expire locks | GET active-lock déclenche reconcile |
| P4 | Journal `bundle_ledger_entries` absent | **Phase 4A livrée** — shadow write + `GET .../ledger` ; Phase 4B = bascule UI |

---

## 6. Livrables ops

| Document / outil | Chemin |
|------------------|--------|
| Runbook recovery | [BUNDLE_RECOVERY_RUNBOOK.md](./BUNDLE_RECOVERY_RUNBOOK.md) |
| Script inspection | `services/arquantix/api/scripts/inspect_bundle_state.py` |
| Audit initial | [BUNDLE_DEPOSIT_WITHDRAW_AUDIT.md](./BUNDLE_DEPOSIT_WITHDRAW_AUDIT.md) |

---

## 7. Checklist prod limitée

- [ ] Lancer `pytest tests/test_bundle_self_trading_isolation.py` en CI
- [ ] Documenter `BUNDLE_INVEST_LOCK_TTL_MINUTES=120` en env
- [ ] Former ops sur `inspect_bundle_state` + runbook
- [ ] Vérifier un invest E2E mock : Mon Trading = 1 transfert PE, bundle history = swaps internes
- [ ] Planifier Phase 4 `bundle_ledger_entries`

---

## 8. Prochaine étape recommandée (Phase 4)

Introduire `bundle_ledger_entries` (journal append-only) comme **source unique** historique bundle, alimenté depuis :
- `bundle.fund_cash_leg` / `bundle.release_cash_leg`
- confirmation legs Li.FI (allocation / withdraw_sell)
- rebalance

Mon Trading et bundle history deviendront des **projections** de ce journal + filtres scope.

---

*Validation read-only complétée — aucune mutation DB effectuée pendant cet audit.*
