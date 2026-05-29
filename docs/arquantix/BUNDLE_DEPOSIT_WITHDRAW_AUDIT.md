# Bundle Deposit / Withdraw / Allocation Audit

**Date :** 2026-05-29  
**Périmètre :** READ-ONLY — `services/arquantix/api`, `services/arquantix/web` (mobile consulté en passant)  
**Aucune modification fonctionnelle effectuée.**

---

## Executive summary

Le modèle **fund-first** Vancelian est **implémenté et documenté dans le code** : le dépôt USDC passe d’abord par un transfert comptable **self-trading → cash leg bundle** (`fund_bundle_cash_leg_from_self_trading`), puis les legs Li.FI d’allocation ne touchent que le ledger bundle (débit cash leg + crédit spot après confirmation on-chain). Le retrait suit l’inverse : **désallocation interne** (ventes Li.FI bundle) puis **release comptable** cash leg → self-trading (`release_bundle_cash_leg_to_self_trading`), sans mouvement Privy supplémentaire.

**Point central (confirmé) :** un swap Li.FI technique du bundle **ne doit pas** apparaître comme trade self-trading. Le backend filtre explicitement les swaps bundle dans l’historique Mon Trading via `is_bundle_internal_swap` et les dépôts Privy liés via `privy_deposit_is_bundle_internal`. **Cependant**, le pipeline Li.FI générique crée **toujours** un `transaction_intent` de type `lifi_swap` en parallèle de l’intent `bundle_invest` / `bundle_withdraw` — risque de double traçabilité et de fuite si un consommateur API omet le filtre.

**Principaux risques identifiés :**

1. **Absence de timeout automatique** sur les locks invest/withdraw — un batch `partial_pending` ou `pending_signature` peut bloquer indéfiniment nouvel invest / retrait.
2. **Pas de retry automatique** des legs failed — recovery manuelle (Resume, finalize, scripts ops).
3. **Double intent Li.FI** pour chaque leg bundle (`lifi_swap` + parent bundle) sans garde-fou dans `lifi_intent_sync.py`.
4. **Fund non rollbacké** si tous les legs d’allocation échouent — USDC reste en cash leg (comportement cohérent métier, mais état `partial` / lock mal libéré possible).
5. **Même wallet Privy on-chain** pour self-trading et bundle — correct techniquement, mais la séparation repose entièrement sur les atoms PE + filtres UI (pas de sous-wallets).
6. **Chemin legacy exchange** (`BUNDLE_EXECUTION_PROVIDER=exchange`) — synchrone, tagging `portfolio_scope=bundle` requis pour éviter fuite Mon Trading.
7. **Reconcile lock** basée sur l’absence de travail pending, pas sur un TTL — lock « zombie » si état swap/intent incohérent.

**Verdict :** l’architecture cible (A→E) est **partiellement en place**. La séparation comptable PE est solide ; les gaps sont surtout **observabilité, recovery, anti-blocage et garde-fous anti-fuite** sur les consommateurs non filtrés.

---

## Expected accounting model

### Deux comptabilités distinctes


| Comptabilité        | Représentation                                                                                 | Contenu                           |
| ------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------- |
| **Self-trading**    | `pe_portfolios` type `direct_portfolio` + `pe_position_atoms` `position_type=spot`             | USDC et actifs trading classiques |
| **Bundle envelope** | `pe_portfolios` type `bundle_portfolio` + atoms `cash` (USDC) et `spot` (BTC/CBBTC, ETH, SOL…) | Patrimoine bundle isolé           |


**Ledger Privy on-chain** (`person_wallet_balances`, `person_wallet_deposits`) : reflet du wallet réel ; **inchangé** lors des transferts comptables fund/release PE.

### Flux attendu — dépôt (100 USDC)

```
Self-trading USDC     -100
Bundle cash leg USDC  +100     ← fund_bundle_cash_leg_from_self_trading (Privy inchangé)
[allocation interne]
Bundle cash leg USDC  -X_i par leg
Bundle spot assets    +reçu   ← apply_allocation_leg_atoms après Li.FI CONFIRMED
```

Mon Trading ne voit que : **transfert USDC vers bundle** (`bundle_pe_transfer` / audit `bundle.fund_cash_leg`).

### Flux attendu — retrait

```
[Phase 1 — désallocation interne, scope bundle uniquement]
Bundle spot → Li.FI → Bundle cash leg USDC

[Phase 2 — release comptable]
Bundle cash leg USDC  -montant
Self-trading USDC     +montant     ← release_bundle_cash_leg_to_self_trading
```

Mon Trading ne voit que : **transfert USDC depuis bundle** (`bundle.release_cash_leg`).

### Règle impérative

> **Un swap Li.FI exécuté pour le bundle est une opération interne d’enveloppe, jamais un trade self-trading du client.**

Garde-fou principal : audit `bundle_leg_context` avec `bundle_execution: true` sur `person_wallet_swaps.audit_log`, puis filtrage via `is_bundle_internal_swap()`.

---

## Current implementation map

### 1. Modèle de données — mapping


| Table / modèle                                | Fichier                                 | Rôle                         | Scope attendu      | Scope actuel                                         | Risque                    |
| --------------------------------------------- | --------------------------------------- | ---------------------------- | ------------------ | ---------------------------------------------------- | ------------------------- |
| `pe_portfolios`                               | `portfolio_engine/portfolios/models.py` | Enveloppes direct + bundle   | Séparés            | OK — `portfolio_type` discrimine                     | Faible                    |
| `pe_portfolios.metadata.bundle_invest_lock`   | `bundles/bundle_invest_lock.py`         | Lock invest batch            | Bundle             | OK — JSON metadata                                   | **Moyen** — pas de TTL    |
| `pe_portfolios.metadata.bundle_withdraw_lock` | `bundles/bundle_withdraw_lock.py`       | Lock retrait batch           | Bundle             | OK                                                   | **Moyen** — pas de TTL    |
| `pe_position_atoms` (cash)                    | `positions/models.py`                   | Cash leg USDC bundle         | Bundle             | OK — `position_type=cash` sur `bundle_portfolio`     | Faible                    |
| `pe_position_atoms` (spot)                    | idem                                    | Allocations bundle           | Bundle             | OK — `position_type=spot` sur `bundle_portfolio`     | Faible                    |
| `pe_position_atoms` (direct spot)             | idem                                    | Self-trading                 | Direct             | OK — fund/release seulement                          | Faible                    |
| `pe_target_allocations`                       | `allocations/models.py`                 | Poids cibles                 | Bundle             | OK                                                   | Faible                    |
| `person_wallet_swaps`                         | `lifi/models.py`                        | Sessions Li.FI (legs)        | Mixte on-chain     | **Global Privy** + tag audit bundle                  | **Élevé** si filtre omis  |
| `person_wallet_deposits`                      | `privy_wallet/models.py`                | Ledger Privy post-settlement | Wallet réel        | Tous swaps confirmés                                 | Filtré Mon Trading        |
| `transaction_intents`                         | `onchain_indexer/models.py`             | Observabilité                | Typé par product   | `**lifi_swap` + `bundle_invest/withdraw`** en double | **Élevé**                 |
| `exchange_orders`                             | `exchange/models.py`                    | Legacy provider              | Direct ou bundle   | Tag `portfolio_scope=bundle`                         | **Moyen** si tag manquant |
| `pe_audit_events`                             | `hardening/audit_models.py`             | Fund/release audit           | Bundle PE          | OK                                                   | Faible                    |
| `crypto_positions`                            | `exchange/models.py`                    | Bootstrap solde direct       | Direct             | Overlay PE, pas bundle                               | Faible                    |
| `custody_transactions`                        | custody                                 | Fiat custody                 | Hors bundle crypto | Non utilisé flux USDC bundle                         | N/A                       |
| `bundles` / `bundle_components`               | `database.py`                           | Catalog admin/backtest       | Admin              | Distinct runtime PE                                  | Confusion doc only        |


**Note :** pas de table `trading_position` — le self-trading = atoms sur `direct_portfolio`.

### 2. Couches logicielles


| Couche                   | Fichiers clés                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------- |
| API routes               | `test_clients/router.py` — `/bundle/invest`, `/withdraw`, `/leg/`*, `/batch/finalize`, locks      |
| Orchestration invest     | `bundles/orchestrator.py` — `_invest_via_lifi`, `finalize_lifi_batch`, `resume_lifi_invest_batch` |
| Orchestration retrait    | `bundles/withdraw.py` — `BundleWithdrawOrchestrator`                                              |
| Funding comptable        | `bundle_execution/bundle_funding.py`                                                              |
| Legs Li.FI               | `bundle_execution/bundle_lifi_leg_service.py`, `bundle_lifi_quote_service.py`                     |
| Settlement PE            | `bundle_execution/pe_settlement.py`                                                               |
| Périmètre transactions   | `bundle_execution/bundle_transaction_scope.py`                                                    |
| Historique bundle        | `bundle_execution/bundle_portfolio_transactions.py`, `bundle_pe_transactions.py`                  |
| Historique Mon Trading   | `test_clients/service.py` → `get_crypto_transactions`                                             |
| Intents bundle           | `transaction_intents/bundle_intent_sync.py`, `bundle_withdraw_intent_sync.py`                     |
| Intents Li.FI génériques | `transaction_intents/lifi_intent_sync.py`                                                         |
| Frontend                 | `web/src/components/portal/bundles/`*, `bundleClient.ts`                                          |
| BFF                      | `web/src/app/api/portal/bundles/`**                                                               |


### 3. Provider d’exécution

- **Par défaut Li.FI Base** : `BUNDLE_EXECUTION_PROVIDER` ou auto `lifi_base` si Li.FI activé.
- **Legacy exchange** : path synchrone dans `orchestrator.invest_into_bundle` — atoms immédiats, orders exchange taggés.

---

## Deposit flow audit

### Tracé complet

```
Frontend PortalBundleInvestDialog
  → useBundleLifiInvest.runInvest()
  → POST /api/portal/bundles/invest/preview
  → POST /api/portal/bundles/invest
BFF → POST /api/app/bundle/invest
  → BundleOrchestrator.invest_into_bundle()
  → _invest_via_lifi()
      1. reconcile_idle_invest_lock_for_invest()
      2. acquire_invest_lock (status: pending_signature)
      3. ensure_bundle_parent_intent()
      4. fund_bundle_cash_leg_from_self_trading()  ← PE transfer
      5. boucle TargetAllocation → _run_allocation_leg()
           → BundleLifiLegService.execute_leg()
           → create_bundle_quote → _attach_bundle_context()
           → status pending (signature client)
  → pour chaque leg: prepare-sign → submit-tx → poll swap → CONFIRMED
  → _apply_post_confirmation: apply_swap_settlement + apply_allocation_leg_atoms
  → POST /bundle/batch/finalize → finalize_lifi_batch → clear_invest_lock
```

### Vérifications


| Question                                              | Résultat                                                                                                                           |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Dépôt USDC comptabilisé self-trading → bundle ?       | **Oui** — `fund_bundle_cash_leg_from_self_trading` débite `direct_portfolio` spot, crédite cash leg (`bundle_funding.py` L291–382) |
| Cash leg créditée avant allocation ?                  | **Oui** — fund avant boucle legs (`orchestrator.py` L379–412)                                                                      |
| Allocation démarre après compta correcte ?            | **Oui** — sauf échec fund → release lock failed                                                                                    |
| Transactions allocation circonscrites au bundle ?     | **Oui côté PE** — `apply_allocation_leg_atoms` débite cash leg bundle, crédit spot bundle                                          |
| Positions self-trading modifiées pendant allocation ? | **Non** — `sync_direct_atom` uniquement au fund/release                                                                            |
| Swaps visibles Mon Trading ?                          | **Non** — filtrés par `is_bundle_internal_swap` dans `get_crypto_transactions`                                                     |
| Transfert fund visible Mon Trading ?                  | **Oui (attendu)** — `bundle_pe_transfer` via `list_bundle_pe_asset_transactions`                                                   |


### Écarts / risques dépôt

- Si **tous les legs échouent** après fund : USDC reste en cash leg ; lock passé en `failed` mais **pas de rollback du fund** (cohérent : l’utilisateur peut réallouer).
- **Double intent** : chaque leg déclenche aussi `on_swap_`* → intent `lifi_swap` (`lifi_execute_service.py`).
- **Double clic** : lock `409 already_pending` + `inFlightRef` frontend — OK partiel.
- **Refresh** : `sessionStorage` + `fetchActiveBundleInvestLock` + `resumeBundleInvest` — OK.

---

## Allocation flow audit

### Création des legs

1. Chargement `TargetAllocation` par `portfolio_id`, tri `rebalance_priority`.
2. Montant leg = `entry_qty_received * target_weight` (ROUND_DOWN).
3. `ExecutionLeg` : `action=allocation`, `bundle_action=allocation`, `batch_id`, metadata instrument IDs.
4. Quote via `BundleLifiQuoteService.create_bundle_quote` (whitelist Base/CBBTC).
5. `_attach_bundle_context` écrit `bundle_leg_context` dans audit swap.
6. Retour `pending` — **aucun atom PE** avant CONFIRMED.

### Li.FI — quote, exécution, états


| Étape     | Comportement                                                    |
| --------- | --------------------------------------------------------------- |
| Quote     | `BundleLifiQuoteService` — validation isolée du portail swap V1 |
| Signature | `prepare_signing` → `LifiExecuteService.prepare_execute`        |
| Submit    | `submit_leg_tx` → settlement Privy + PE atoms si CONFIRMED      |
| Polling   | `refresh_and_settle` — partagé avec swap self-trading           |
| Mock dev  | `BUNDLE_LIFI_SYNC_MOCK` auto-complete                           |


### Échecs partiels


| Scénario                  | Comportement actuel                                                                       |
| ------------------------- | ----------------------------------------------------------------------------------------- |
| 1 leg OK, 1 leg fail      | Batch `partial` ou `partial_pending` ; cash leg = fund − legs confirmés                   |
| Li.FI quote fail          | Leg `failed` dans `allocation_details`, boucle continue                                   |
| Li.FI execution fail      | Swap `FAILED`, leg intent `failed`, pas d’atoms PE                                        |
| Polling ne revient jamais | Lock reste actif ; `reconcile_idle_invest_lock` ne clear que si **plus** de swaps pending |
| User refresh              | Resume via lock + sessionStorage + `/bundle/invest/resume`                                |
| Backend restart           | État en DB (lock metadata + swaps) — reprise possible si client reprend                   |


### États — comparaison


| État attendu (spec) | Présent dans le code                | Notes                                           |
| ------------------- | ----------------------------------- | ----------------------------------------------- |
| NOT_STARTED         | Implicite (pas de lock)             | —                                               |
| PENDING             | `pending_signature`, lock statuses  | —                                               |
| ALLOCATING          | **Non nommé**                       | Couvert par `submitted`, `pending_confirmation` |
| PARTIALLY_ALLOCATED | `partial`, `partial_pending`        | Lock + batch status                             |
| ALLOCATED           | `completed`                         | Lock cleared                                    |
| FAILED              | `failed`                            | Terminal lock                                   |
| CANCELLED           | **Absent**                          | —                                               |
| NEEDS_REVIEW        | `reconciliation_required` (intents) | Pas sur lock portfolio                          |
| RECOVERABLE         | **Implicite**                       | Resume/finalize manuels                         |
| STUCK               | **Non modélisé**                    | Détectable via reconciliation stale             |


**Statuts swap Li.FI :** `PENDING` → `QUOTE_RECEIVED` → `AWAITING_SIGNATURE` → `SUBMITTED` → `CONFIRMED` | `FAILED` | `EXPIRED`

**Statuts batch orchestrator invest :** `completed`, `partial`, `failed`, `pending_signature`, `partial_pending`

---

## Withdraw flow audit

### Tracé complet

```
PortalBundleWithdrawDialog → useBundleLifiWithdraw
  → POST /api/portal/bundles/withdraw
  → BundleWithdrawOrchestrator.withdraw_from_bundle()
      1. reconcile_idle_invest_lock_for_withdraw (bloque si invest actif)
      2. acquire_withdraw_lock (WITHDRAW_REQUESTED)
      3. Calcul needed_from_sells = requested − cash_leg
      4. Phase UNWIND: legs withdraw_sell via Li.FI (pending/completed)
      5. try_release_if_ready() si sells terminés
      6. release_bundle_cash_leg_to_self_trading()
  → finalize: POST /bundle/withdraw/finalize
```

### Vérifications


| Question                                                 | Résultat                                                                                       |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Ventes internes scope bundle ?                           | **Oui** — `withdraw_sell` + atoms via `apply_withdraw_sell_atoms`                              |
| Self-trading reçoit uniquement USDC final ?              | **Oui** — release PE uniquement ; pas de crédit spot trading sur ventes                        |
| Transactions Mon Trading = transferts bundle → trading ? | **Oui pour release** — `bundle_pe_transfer` credit ; swaps internes filtrés                    |
| Échecs partiels gérés ?                                  | **Partiellement** — `failed_partial`, `partially_unwound`, release partiel si cash insuffisant |
| Retrait bloqué éternellement ?                           | **Possible** — lock actif sans TTL ; pending sells bloquent release                            |


### Phases withdraw lock

`WITHDRAW_REQUESTED` → `UNWINDING` → `PARTIALLY_UNWOUND` | `READY_TO_RELEASE` → `RELEASED` | `FAILED_PARTIAL`

---

## Ledger separation issues

Violations ou risques de confusion comptable / affichage :


| Fichier                                    | Fonction                                    | Ligne ~  | Problème                                                          | Impact                                                | Correction recommandée                          |
| ------------------------------------------ | ------------------------------------------- | -------- | ----------------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------- |
| `lifi_intent_sync.py`                      | `sync_lifi_swap_intent`                     | 54–89    | Crée intent `lifi_swap` pour **tous** les swaps, sans skip bundle | Double traçabilité ; fuite si consommateur non filtré | Early return si `bundle_context_for_swap(swap)` |
| `lifi_execute_service.py`                  | `prepare_execute`, `submit_signed_tx`, poll | 69–322   | Appelle `on_swap_*` systématiquement                              | Idem                                                  | Guard bundle dans callbacks ou skip sync        |
| `lifi_quote_service.py`                    | quote path portail                          | 86–147   | Crée swap + intent pour self-trading                              | N/A bundle si quote via `BundleLifiQuoteService`      | OK si séparation stricte maintenue              |
| `privy_wallet/transaction_merge.py`        | `person_wallet_swap_to_crypto_tx`           | 73–117   | Titre générique « Échange X → Y », `source_system=lifi_swap`      | Fuite Mon Trading si appelé sans filtre               | Param optionnel bundle ou filtre interne        |
| `test_clients/service.py`                  | `get_crypto_transactions`                   | 607–675  | Filtre bundle — **correct**                                       | Référence pattern à généraliser                       | Extraire helper partagé pour tous endpoints     |
| `wallet_history/service.py`                | historique wallet                           | ~280     | Filtre exchange bundle only, **pas Li.FI**                        | Swaps bundle possibles si route utilisée              | Appliquer `is_bundle_internal_swap`             |
| `bundle_lifi_quote_service.py`             | `create_bundle_quote`                       | ~90+     | Audit quote avant `_attach_bundle_context`                        | Fenêtre sans `portfolio_id`                           | Attacher contexte dès création swap             |
| `bundle_transaction_scope.py`              | `is_bundle_internal_swap`                   | 34–42    | Fallback `batch_id` seul si action inconnue                       | Faux positif rare                                     | Exiger `bundle_execution: true` strict          |
| `orchestrator.py`                          | legacy exchange invest                      | ~161–314 | Orders exchange synchrones                                        | Apparition Mon Trading si tag manquant                | Assert tag dans tests + migration backfill      |
| `lifi_swap_settlement.py`                  | `apply_swap_settlement`                     | —        | Met à jour ledger Privy global                                    | Correct on-chain ; même wallet                        | Documenter : séparation = PE + filtres          |
| `bundle_lifi_api.py`                       | `leg_from_swap_audit`                       | ~34      | Metadata instrument IDs incomplets                                | `missing_instrument_ids_in_leg_metadata`              | Copier metadata leg depuis ctx audit            |
| `web/cryptoTransactionHistoryFormat.ts`    | `mapCryptoTransactionToHistoryItem`         | —        | Pas de badge bundle distinct                                      | UX confuse transfert vs swap                          | Utiliser `transaction_kind` / `source_system`   |
| `web/PortalCryptoWalletBundleDetailScreen` | FAB Déposer                                 | —        | Pointe dépôt Privy, pas invest bundle                             | Confusion UX dépôt vs invest                          | Clarifier libellé ou rediriger invest           |


**Constat positif :** le fund-first et le filtrage Mon Trading dans `get_crypto_transactions` implémentent correctement la règle centrale pour le chemin Li.FI principal.

---

## Blocking states and lock risks

### Locks inventoriés


| Lock               | Stockage                                    | Création                           | Relâchement                                                                     | Timeout                  | Retry        | Unlock manuel                                 |
| ------------------ | ------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------- | ------------------------ | ------------ | --------------------------------------------- |
| Invest lock        | `pe_portfolios.metadata.bundle_invest_lock` | `acquire_invest_lock` début invest | `clear_invest_lock` (completed), `release_invest_lock` (failed), reconcile idle | **Non**                  | **Non auto** | Reconcile via API active-lock ; scripts ops   |
| Withdraw lock      | `bundle_withdraw_lock`                      | `acquire_withdraw_lock`            | `clear_withdraw_lock` après RELEASED                                            | **Non**                  | **Non auto** | `/withdraw/finalize`, callback sell confirmed |
| Session frontend   | `sessionStorage`                            | pendant exécution                  | fin dialog / succès                                                             | TTL navigateur           | Resume       | Clear manuel                                  |
| Transaction intent | DB                                          | upsert par sync                    | statuts terminaux                                                               | Reconciliation stale 24h | —            | Admin reconciliation                          |


### Statuts actifs invest lock

`pending_signature`, `signature_requested`, `submitted`, `pending_confirmation`, `finalizing`, `partial_pending`

### Statuts terminaux invest lock

`completed`, `failed`, `expired` — **mais** `expired` n’est pas assigné automatiquement par un job ; seulement via `release_invest_lock`.

### Interactions bloquantes

- Invest lock actif → **409** nouvel invest ; bloque withdraw (`invest_lock_active`).
- Withdraw lock actif → **409** nouveau retrait.
- `partial_pending` + legs non signés → utilisateur bloqué sans Resume.

### Risque STUCK

Scénario : fund OK, legs pending, client abandonne → lock actif indéfiniment.  
`reconcile_idle_invest_lock` clear **uniquement** si `_batch_has_blocking_invest_work` retourne false (plus de swaps/intents pending). Un swap `AWAITING_SIGNATURE` bloque donc le lock **correctement** mais sans expiration.

---

## Partial failure scenarios

### Matrice dépôt


| Cas                                   | État attendu                     | Ledger attendu                    | UI attendue               | Action recovery             | Test à ajouter                                        |
| ------------------------------------- | -------------------------------- | --------------------------------- | ------------------------- | --------------------------- | ----------------------------------------------------- |
| USDC insuffisant                      | failed, pas de lock persistant   | Aucun mouvement                   | Erreur solde              | Réessayer après dépôt Privy | `test_invest_fails_insufficient_self_trading_no_fund` |
| Transfert interne échoue              | failed                           | Aucun                             | Erreur                    | —                           | Couvert partiellement funding tests                   |
| Transfert OK, allocation non démarrée | partial_pending / lock           | Cash leg +100                     | Panel allocation + Resume | `resumeBundleInvest`        | `test_fund_ok_zero_legs_started`                      |
| Allocation partielle                  | partial / partial_pending        | Cash leg restant + spots partiels | Progress legs             | Finalize partiel            | `test_partial_allocation_cash_leg_remaining`          |
| Allocation échouée (tous legs)        | failed                           | Cash leg = fund intégral          | Erreur + cash non alloué  | Rebalance / réinvest        | `test_all_legs_fail_cash_leg_intact`                  |
| Li.FI quote échoue                    | leg failed, batch partial/failed | Fund intact                       | Leg en erreur             | Retry leg manuel            | `test_quote_failure_continues_batch`                  |
| Li.FI execution échoue                | leg failed                       | Pas d’atoms leg                   | Erreur swap               | Resume / retry              | partiel phase2                                        |
| Provider timeout                      | pending_confirmation             | Fund + swap SUBMITTED             | Spinner                   | Poll / refresh              | `test_poll_timeout_lock_persists`                     |
| App refresh                           | lock + session                   | Inchangé                          | Resume                    | sessionStorage + API        | frontend inFlight tests                               |
| Double click invest                   | 409 already_pending              | Idempotent fund?                  | blocked                   | —                           | `bundleClient.lock.test`                              |
| Backend restart                       | lock + swaps DB                  | Inchangé                          | Resume                    | `/invest/resume`            | `test_resume_after_restart`                           |


### Matrice retrait


| Cas                      | État attendu      | Ledger attendu                  | UI attendue     | Action recovery      | Test à ajouter                    |
| ------------------------ | ----------------- | ------------------------------- | --------------- | -------------------- | --------------------------------- |
| Actifs insuffisants      | error             | Inchangé                        | Message         | —                    | withdraw tests                    |
| Quote sell échoue        | failed_partial    | Spots intacts                   | Erreur          | Retry sells          | `test_withdraw_sell_quote_fail`   |
| Sell partiel             | partially_unwound | Cash leg partiel                | Progress        | Finalize partiel     | `test_partial_unwind_release_min` |
| Sell OK, release échoue  | ready_to_release  | Cash leg plein, direct inchangé | Pending release | `/withdraw/finalize` | `test_release_after_sells`        |
| USDC dispo < demandé     | partially_unwound | Release min(cash, requested)    | Montant partiel | Accepter partiel     | withdraw tests partiels           |
| Retrait partiel possible | partially_unwound | Release partiel                 | OK              | Finalize             | couvert                           |
| Retrait bloqué           | lock actif        | Mixte                           | blocked         | Resume / admin       | `test_withdraw_stuck_lock`        |
| User refresh             | session + lock    | Inchangé                        | Resume          | sessionStorage       | —                                 |
| Backend restart          | lock DB           | Inchangé                        | Resume          | finalize API         | e2e mock scripts                  |


---

## Recovery strategy

### Existant


| Mécanisme                                                  | Fichier                                                                                  |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `resume_lifi_invest_batch`                                 | `orchestrator.py`                                                                        |
| `reconcile_idle_invest_lock`                               | `bundle_invest_lock.py`                                                                  |
| `_reconcile_stale_intent_legs_for_batch`                   | `bundle_invest_lock.py`                                                                  |
| `finalize_lifi_batch`                                      | `orchestrator.py`                                                                        |
| `finalize_withdraw_batch`                                  | `withdraw.py`                                                                            |
| `refresh_and_settle`                                       | `bundle_lifi_leg_service.py`                                                             |
| `scan_intent_gaps_for_person` / `_scan_bundle_invest_gaps` | `transaction_intent_reconciliation.py`                                                   |
| Scripts ops                                                | `complete_bundle_lifi_legs_mock.py`, `e2e_bundle_*`, `verify_bundle_fund_first_local.py` |
| UI Resume                                                  | `PortalBundleInvestDialog`, `PortalBundleAllocationPanel`, withdraw dialog               |


### Stratégie anti-blocage recommandée

1. **Timeout automatique lock** — après N heures en `pending_signature` / `partial_pending`, passer lock → `expired`, laisser cash leg intact.
2. **États explicites** `PARTIALLY_ALLOCATED` / `PARTIALLY_WITHDRAWN` alignés UI ↔ API.
3. **Bouton « Resume »** — déjà présent invest ; généraliser withdraw.
4. **« Retry failed legs »** — endpoint idempotent recréant uniquement legs `failed` d’un batch.
5. **Admin « Force reconcile »** — exposer `scan_intent_gaps_for_person` + actions correctives PE.
6. **Admin « Release lock »** — avec garde-fous (audit, confirmation).
7. **Job réconciliation périodique** — cron `_scan_bundle_invest_gaps` + auto-expire locks stale.
8. **Idempotency keys** — fund/release déjà batch-scoped ; renforcer legs (`ext_ref`).
9. **Journal immutable bundle** — table append-only `bundle_ledger_entries` (au lieu de dériver audit + intents).

### Priorité correction anti-fuite

**Dans `lifi_intent_sync.sync_lifi_swap_intent` :** si `bundle_context_from_swap_audit(swap)` → **ne pas** créer intent `lifi_swap`. Centralise la règle « swap bundle ≠ trade client ».

---

## Test coverage audit

### Tests backend bundle (runtime)


| Fichier                                      | Couverture                                    |
| -------------------------------------------- | --------------------------------------------- |
| `test_bundle_orchestrator.py`                | Orchestrator, fund-first Li.FI                |
| `test_bundle_lifi_funding.py`                | Fund self-trading → cash leg, invariant Privy |
| `test_bundle_lifi_phase2.py`                 | Validation Base, provider, mock               |
| `test_bundle_lifi_wallet.py`                 | Wallet signing                                |
| `test_bundle_withdraw.py`                    | Release, sell atoms, locks, partial/full      |
| `test_bundle_invest_lock.py`                 | Acquire/reconcile lock                        |
| `test_bundle_pe_transactions.py`             | Historique transferts PE                      |
| `test_bundle_transaction_scope.py`           | `is_bundle_internal_swap`, dédup              |
| `test_bundle_execution_adapter_phase1.py`    | Provider exchange/lifi, tagging               |
| `test_bundle_invest_preview.py`              | Preview Li.FI                                 |
| `test_phase7d_bundle_transaction_intents.py` | Intents parent/legs                           |
| `test_portfolio_engine_crypto_bundle.py`     | Intégration PE                                |
| `test_future_lending_compatibility.py`       | spot+cash bundle                              |


### Tests frontend


| Fichier                                  | Couverture                         |
| ---------------------------------------- | ---------------------------------- |
| `bundleClient.routes.test.ts`            | Routes BFF, séparation swap/bundle |
| `bundleClient.lock.test.ts`              | 409 already_pending                |
| `bundleInvestInFlight.test.ts`           | Double-clic                        |
| `bundleWithdrawFormat.test.ts`           | Phases, crédit self-trading        |
| `cryptoWalletFormat.test.ts`             | Séparation positions, hub total    |
| `cryptoTransactionHistoryFormat.test.ts` | `bundle_pe_transfer`               |


### Lacunes


| Domaine                                      | Couvert ?                                  |
| -------------------------------------------- | ------------------------------------------ |
| Dépôt cash leg                               | **Oui** (`test_bundle_lifi_funding`)       |
| Allocation                                   | **Partiel** (mock, pas e2e multi-leg fail) |
| Retrait                                      | **Oui** (withdraw tests)                   |
| Désallocation                                | **Partiel**                                |
| Échec partiel multi-leg                      | **Faible**                                 |
| Reprise lock / stale                         | **Partiel** (`test_bundle_invest_lock`)    |
| **Absence impact self-trading swaps**        | **Non explicite** — **gap critique**       |
| Idempotence fund                             | **Partiel**                                |
| Recovery timeout                             | **Absent**                                 |
| **Bundle swap ne crée pas intent lifi_swap** | **Absent**                                 |
| Rebalance Li.FI pending e2e                  | **Faible**                                 |
| Composants React dialogs                     | **Absent**                                 |


### Tests prioritaires proposés

1. `test_bundle_lifi_swap_not_in_self_trading_history.py`
2. `test_bundle_lifi_swap_skips_lifi_swap_intent.py`
3. `test_partial_allocation_lock_and_cash_leg.py`
4. `test_invest_lock_expires_after_stale_timeout.py`
5. `test_withdraw_partial_unwind_release.py`
6. `test_resume_invest_after_refresh.py`
7. `test_fund_idempotent_same_batch.py`
8. `test_exchange_legacy_orders_tagged_bundle.py`
9. `test_bundle_internal_swap_not_in_wallet_history.py`
10. `PortalBundleInvestDialog.integration.test.tsx` (optionnel)

---

## Recommended implementation plan

### Architecture cible (alignement)


| Couche                            | Statut actuel                               | Action                            |
| --------------------------------- | ------------------------------------------- | --------------------------------- |
| **A. Bundle Cash Transfer Layer** | **Implémenté** (`bundle_funding.py`)        | Tests idempotence + journal dédié |
| **B. Bundle Allocation Engine**   | **Implémenté** (Li.FI legs + PE settlement) | Retry failed legs, timeout lock   |
| **C. Bundle Deallocation Engine** | **Implémenté** (`withdraw.py`)              | Finalize auto post-sells          |
| **D. Bundle Ledger**              | **Partiel** (audit + intents + atoms)       | Table journal typée immutable     |
| **E. Trading Ledger**             | **Partiel** (direct atoms + filtres)        | Garde-fou global anti-fuite swap  |


### Types journal bundle recommandés

`BUNDLE_DEPOSIT`, `BUNDLE_WITHDRAWAL`, `BUNDLE_ALLOCATION_BUY`, `BUNDLE_ALLOCATION_SELL`, `BUNDLE_REBALANCE`, `BUNDLE_FEE`, `BUNDLE_RECOVERY_ADJUSTMENT`

### Plan par phases

**Phase 1 — Anti-fuite (1–2 j)**  

- Skip `lifi_swap` intent pour swaps bundle.  
- Helper `list_self_trading_crypto_transactions()` centralisant tous filtres.  
- Appliquer filtre Li.FI dans `wallet_history/service.py`.

**Phase 2 — Anti-blocage (2–3 j)**  

- TTL lock + job expire.  
- Endpoint `retry-failed-legs`.  
- Améliorer `reconcile_idle_*` avec seuil temporal.

**Phase 3 — Observabilité (2 j)**  

- Exposer gaps reconciliation admin.  
- Aligner statuts UI ↔ API (`PARTIALLY_ALLOCATED`).

**Phase 4 — Ledger durable (3–5 j)**  

- Table `bundle_ledger_entries` append-only.  
- Migration écriture depuis fund/allocation/release.

**Phase 5 — Tests (2 j)**  

- Suite anti-fuite + partial failure + recovery.

---

## Files to change later

*(Liste pour implémentation future — non modifiés dans cet audit)*


| Priorité | Fichier                                                                  |
| -------- | ------------------------------------------------------------------------ |
| P0       | `services/transaction_intents/lifi_intent_sync.py`                       |
| P0       | `services/test_clients/service.py` (extract filtres)                     |
| P0       | `services/portfolio_engine/bundle_execution/bundle_transaction_scope.py` |
| P1       | `services/portfolio_engine/bundles/bundle_invest_lock.py`                |
| P1       | `services/portfolio_engine/bundles/bundle_withdraw_lock.py`              |
| P1       | `services/portfolio_engine/bundles/orchestrator.py`                      |
| P1       | `services/portfolio_engine/bundles/withdraw.py`                          |
| P1       | `services/lifi/lifi_execute_service.py`                                  |
| P2       | `services/wallet_history/service.py`                                     |
| P2       | `services/portfolio_engine/bundle_execution/bundle_lifi_leg_service.py`  |
| P2       | `services/transaction_intents/transaction_intent_reconciliation.py`      |
| P2       | `web/src/lib/portal/cryptoTransactionHistoryFormat.ts`                   |
| P2       | `web/src/components/portal/bundles/PortalBundleInvestDialog.tsx`         |
| P3       | Nouveau : `bundle_ledger/models.py`, `bundle_ledger/service.py`          |
| P3       | Nouveau : tests listés section précédente                                |


---

## Risk ranking


| Rang | Risque                                                                 | Sévérité     | Probabilité |
| ---- | ---------------------------------------------------------------------- | ------------ | ----------- |
| 1    | Swap bundle exposé comme trade self-trading (consommateur sans filtre) | **Critique** | Moyenne     |
| 2    | Lock permanent bloquant invest/retrait                                 | **Élevée**   | Moyenne     |
| 3    | Double intent Li.FI / confusion reconciliation                         | **Élevée**   | Élevée      |
| 4    | Fund sans allocation (cash leg dormante) sans UX recovery claire       | **Moyenne**  | Élevée      |
| 5    | Retrait partiel mal finalisé (cash leg bloqué)                         | **Moyenne**  | Moyenne     |
| 6    | Legacy exchange orders non taggés                                      | **Élevée**   | Faible      |
| 7    | Metadata leg incomplète → settlement PE fail                           | **Moyenne**  | Faible      |
| 8    | Même wallet Privy — confusion utilisateur patrimoine                   | **Moyenne**  | Élevée      |
| 9    | Absence tests anti-fuite regression                                    | **Élevée**   | Élevée      |
| 10   | UX « Déposer » bundle vs invest bundle                                 | **Faible**   | Élevée      |


---

## Annexe — 10 fichiers les plus critiques

1. `services/arquantix/api/services/portfolio_engine/bundle_execution/bundle_funding.py`
2. `services/arquantix/api/services/portfolio_engine/bundles/orchestrator.py`
3. `services/arquantix/api/services/portfolio_engine/bundle_execution/bundle_lifi_leg_service.py`
4. `services/arquantix/api/services/portfolio_engine/bundle_execution/bundle_transaction_scope.py`
5. `services/arquantix/api/services/test_clients/service.py`
6. `services/arquantix/api/services/transaction_intents/lifi_intent_sync.py`
7. `services/arquantix/api/services/portfolio_engine/bundles/withdraw.py`
8. `services/arquantix/api/services/portfolio_engine/bundles/bundle_invest_lock.py`
9. `services/arquantix/api/services/portfolio_engine/bundle_execution/pe_settlement.py`
10. `services/arquantix/web/src/lib/portal/bundleClient.ts`

---

## Annexe — 10 risques les plus graves

1. **Swap bundle classé `lifi_swap`** et affiché comme échange self-trading si filtre omis.
2. **Lock invest/withdraw sans expiration** — paralysie opérations bundle.
3. **Pas de retry automatique** legs failed — états `partial` persistants.
4. **Double comptabilité intents** (`lifi_swap` + `bundle_invest`) — reconciliation incohérente.
5. **Fund non rollbacké** + échec total allocation — USDC « gelé » en cash leg sans guidage.
6. **Polling Li.FI interrompu** — swap SUBMITTED + lock actif indéfiniment.
7. `**wallet_history`** et autres endpoints sans filtre Li.FI bundle.
8. **Chemin legacy exchange** — fuite Mon Trading si `portfolio_scope` absent.
9. **Release withdraw** non déclenchée si finalize oublié après sells confirmés.
10. **Absence de tests regression** sur la règle centrale anti-fuite self-trading.

---

## Annexe — 10 tests prioritaires à écrire

1. `test_bundle_internal_swap_excluded_from_get_crypto_transactions`
2. `test_bundle_leg_does_not_create_lifi_swap_intent`
3. `test_fund_first_then_allocation_only_touches_bundle_atoms`
4. `test_withdraw_release_only_credits_direct_usdc`
5. `test_partial_allocation_preserves_cash_leg_and_lock_status`
6. `test_invest_lock_cleared_by_reconcile_when_swaps_terminal`
7. `test_invest_lock_persists_while_awaiting_signature`
8. `test_withdraw_failed_partial_does_not_release_to_self_trading`
9. `test_resume_invest_rebuilds_pending_legs_from_lock`
10. `test_bundle_pe_transfer_visible_in_self_trading_but_swap_not`

---

## Corrections implemented (2026-05-29)

### Phase 1 — Anti-fuite bundle / self-trading


| Changement                                           | Fichier                                  |
| ---------------------------------------------------- | ---------------------------------------- |
| Skip intent `lifi_swap` si swap bundle interne       | `lifi_intent_sync.py`                    |
| Helper centralisé filtrage Mon Trading               | `self_trading_transactions.py` (nouveau) |
| Refactor `get_crypto_transactions`                   | `test_clients/service.py`                |
| Filtre ordres exchange bundle en scope direct/global | `wallet_history/service.py`              |
| Durcissement `is_bundle_internal_swap`               | `bundle_transaction_scope.py`            |


### Phase 2 — Anti-blocage / recovery


| Changement                                | Fichier                   |
| ----------------------------------------- | ------------------------- |
| TTL invest lock + expire/reconcile        | `bundle_invest_lock.py`   |
| TTL withdraw lock + expire                | `bundle_withdraw_lock.py` |
| États withdraw récupérables non bloquants | `bundle_withdraw_lock.py` |
| Finalize withdraw renforcé                | `withdraw.py`             |
| Invest partial/failed libère le lock      | `orchestrator.py`         |


### Phase 3 — UX minimale

- `bundleStateFormat.ts`, `bundleInvestLabels.ts`, `bundleClient.ts`

### Tests ajoutés

- `tests/test_bundle_self_trading_isolation.py` (13 scénarios)
- `bundleStateFormat.test.ts` (5 tests)

### Risques restants

- Endpoint `retry-failed-legs`, job cron, legacy exchange tagging, journal immutable

*Fin du rapport d’audit READ-ONLY.*