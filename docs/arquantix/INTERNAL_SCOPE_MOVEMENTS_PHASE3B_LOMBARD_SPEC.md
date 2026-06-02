# Internal Scope Movements — Phase 3B Lombard Only

**Date :** 2026-06-02  
**Statut :** **implémenté (local validé)** — writer PE + hook + tests ; push/deploy en attente validation finale  
**Prérequis :** Phase 2 attempts/traces OK · Phase 3A Vault OK · Alembic 172 cohérent  
**Spec parente :** [INTERNAL_SCOPE_MOVEMENTS_ACCOUNTING_SPEC.md](./INTERNAL_SCOPE_MOVEMENTS_ACCOUNTING_SPEC.md) §3  
**Référence Vault :** [INTERNAL_SCOPE_MOVEMENTS_PHASE3A_VAULT.md](./INTERNAL_SCOPE_MOVEMENTS_PHASE3A_VAULT.md)

---

## Executive summary

Le Lombard V1 est **exécuté et observable** (OVT multi-step, intents Phase 7C, attempts Phase 2) et **écrit désormais en PE** via Phase 3B : lock collateral + borrow USDC, idempotent par `ovt_id` open_loan.

La **doctrine métier** (spec parente §3) — **invariants conservés** :

```
collateral lock :  trading_available(asset) −  →  trading_locked_collateral(asset) +
borrow USDC     :  trading_available USDC +   +  liability USDC +
```

**UX cible :** collateral **dans Trading** en deux lignes (disponible 🔓 / en garantie 🔒) ; dette USDC **déduite du net worth** (Phase 4 — pas encore branché sur `patrimony_merge`).

Phase 3B writer calqué Phase 3A Vault : `lombard_funding.py` + `lombard_ovt_bridge.py` + hook `dual_write.py` post-`open_loan` success. **Aucune migration Alembic.** Pas de backfill prod.

---

## Contrainte DB et représentation PE retenue (implémentée)

### Spike pré-implémentation

Migration **045** crée l’index partiel :

```sql
CREATE UNIQUE INDEX ix_pe_position_atoms_unique_open
ON public.pe_position_atoms (portfolio_id, instrument_id)
WHERE status = 'open';
```

**Conséquence :** impossible d’avoir sur le même `direct_portfolio` deux atoms open sur le même instrument — ex. CBBTC `spot` + CBBTC `collateral`. Test : `tests/test_lombard_spike_dual_atom.py`.

### Alternative retenue (Phase 3B — sans migration)

| Mouvement | Représentation PE | Lecture scopes (`pe_reader`) |
|-----------|-------------------|------------------------------|
| **Lock collateral** | Même atom **SPOT** : `available_quantity −` / `locked_quantity +` ; `quantity` et cost basis **inchangés** | `trading_available` ← `available_quantity` ; `trading_locked_collateral` ← `locked_quantity` |
| **Borrow USDC** | Même atom **SPOT USDC** : `quantity +` / `available_quantity +` ; dette dans `metadata.lombard_liability_usdc` (cumulatif) | `trading_available` ← `available_quantity` ; `liability` ← metadata |

**Invariant atom Lombard lock :**

```
quantity ≈ available_quantity + locked_quantity
```

**Audit PE :** `representation: spot_available_to_locked_quantity` (lock) ; `spot_metadata_liability_and_available_credit` (borrow).

### Repoussé — Phase 4 optionnelle

- Atom **`COLLATERAL`** séparé (`position_type=collateral`) — nécessite assouplissement index unique (migration Alembic dédiée).
- Atom **`BORROWING`** séparé pour dette USDC — même contrainte.

### Repoussé — phases suivantes

| Phase | Contenu |
|-------|---------|
| **3C** | Repay Lombard + unlock collateral (mouvements inverses, idempotents par `ovt_id`) |
| **4** | Net worth / `patrimony_merge` − liability ; Cost Basis V2 ; refactor atoms COLLATERAL/BORROWING optionnel |
| **4+** | `resolve_trading_available_for_vault` → lire `available_quantity` (aujourd’hui `quantity` — OK USDC borrow, sur-estimation théorique collateral locked pour vault invest) |

---

## Current Lombard model

### Couches aujourd’hui

| Couche | Implémentation | PE impact |
|--------|----------------|-----------|
| **Prepare / ledger** | `lombardLedger.ts` → `onchain_vault_transactions` (`integration_mode=lombard_v1`) | Aucun |
| **Confirm receipt** | `updateLedgerAfterReceipt` + `syncLombardIntentAfterConfirm` | Aucun |
| **Intents** | `lombard_intent_sync.py` — parent `lombard_borrow` + steps `approve` / `authorize` / `open_loan` | Observabilité |
| **Attempts** | `dual_write_lombard_step_from_receipt` | Observabilité |
| **Scope PE hook** | `_maybe_apply_vault_scope_movement_after_success` **exclut** `lombard_v1` | Aucun |
| **Collateral lock affiché** | Morpho SDK → `lombardPositionService` → `lombardWalletBalanceOverlay.ts` | Proxy UI |
| **Dette USDC affichée** | Morpho `borrowAmount` + credit line dashboard | Produit parallèle, pas net worth |
| **PE atoms** | Aucun Lombard | — |

### OVT Lombard — structure

Table partagée : `onchain_vault_transactions` (Prisma `OnchainVaultTransaction`).

| Champ | Lombard open_loan |
|-------|-------------------|
| `integration_mode` | `lombard_v1` |
| `operation` (step approve/authorize) | `approve`, `amount_raw=0` |
| `operation` (step open_loan) | `deposit`, `amount_raw=borrowAmountRaw`, `asset_symbol=USDC` |
| `group_key` | = `idempotencyKey` client (prepare) |
| `metadata_json.lombard_operation` | `open_loan` |
| `metadata_json.collateral` | Symbole garantie (ex. `cbBTC`, `cbETH`) |
| `metadata_json.guarantee_amount_raw` | Collateral en unités base token |
| `metadata_json.guarantee_amount` | Collateral human-readable (quote) |
| `metadata_json.borrow_amount_raw` | Emprunt USDC (6 decimals) |
| `metadata_json.borrow_amount` | Emprunt USDC human-readable |

**Point critique :** la ligne OVT `deposit` porte **l’emprunt USDC** en `amount_raw` ; le **collateral n’est que dans metadata** (pas de step OVT `collateral_supply` dédié).

### Chaîne confirm (observabilité)

```
Portal confirm receipt
  → OVT status=success (open_loan deposit row)
  → sync_lombard_step_from_ledger_receipt
       → mark_lombard_step_confirmed
       → dual_write_lombard_step_from_receipt
       → _maybe_apply_lombard_scope_movement_after_success (Phase 3B)
            → open_lombard_loan (lock + borrow, idempotent ovt_id)
```

Test de garde Vault : `test_lombard_receipt_does_not_create_vault_scope_movement` — un receipt Lombard ne doit **pas** déclencher `vault.fund_from_self_trading`.

### Dry-run existant

`compute_expected_lombard_scope_movements` (`lombard.py`) :

- Filtre : `integration_mode=lombard_v1`, `status=success`, `lombard_operation=open_loan` (ou `deposit` sans `repay`)
- Dédup : **une paire lock+borrow par `group_key`** (fallback `ovt id`)
- `reference_id` : **OVT id** de la ligne `deposit` open_loan
- Lock : `trading_available` → `trading_locked_collateral`, qty depuis metadata collateral
- Borrow : `liability` → `trading_available` USDC, qty depuis metadata borrow

Audit compare : risque `lombard_lock_legacy_without_pe_scope` si legacy attend locked > 0 et PE = 0.

---

## Legacy sources

### Tableau des sources par donnée

| Donnée | Source primaire (writer Phase 3B) | Source secondaire (réconciliation / UX transition) | Source à **ne pas** utiliser comme SoT writer |
|--------|-----------------------------------|-----------------------------------------------------|-----------------------------------------------|
| **Collateral symbol** | OVT `metadata_json.collateral` (+ aliases `collateral_symbol`, `guarantee_asset`) | Morpho market config / `LombardActivePosition.collateralSymbol` | Overlay calculé |
| **Collateral quantity** | OVT `guarantee_amount` (prioritaire) ou `guarantee_amount_raw` + decimals résolus | Morpho `collateralAmount` (gap report) | Privy wallet balance delta |
| **Borrow USDC quantity** | OVT `borrow_amount_raw` (prioritaire) ou `borrow_amount` | Morpho `borrowAmount` ; OVT `amount_raw` sur deposit (doit matcher) | Mock Privy credit ledger |
| **Moment comptable** | OVT `open_loan` row `status=success` | Intent step `open_loan` confirmed | Steps approve/authorize seuls |
| **Corrélation multi-step** | `group_key` | Intent parent `linked_reference_id=group_key` | — |
| **Idempotence replay** | `pe_audit_events` + `linked_reference_id=ovt_id` | — | `group_key` seul (plusieurs steps) |

### Priorité parsing collateral (alignée dry-run)

Implémentée dans `utils.collateral_quantity_from_metadata` :

1. `guarantee_amount` (Decimal human) — **SoT préférée** si présente au prepare
2. `guarantee_amount_raw` + decimals résolus (`collateral_decimals` metadata → registres assets → alias documentés)
3. **Jamais** de default silencieux à 8 decimals — gap `missing_decimals_gap` si inconnu

### Priorité parsing borrow USDC

`borrow_usdc_from_metadata` :

1. `borrow_amount_raw` + `asset_decimals` row (6 pour USDC)
2. `borrow_amount` human

---

## Accounting target model

### Mouvements atomiques (open_loan confirm)

Restent **intra-`direct_portfolio`** — pas de `vault_portfolio`, pas de section UI séparée.

| # | Type | Source scope | Dest scope | Asset | Représentation PE (implémentée) | Privy on-chain |
|---|------|--------------|------------|-------|--------------------------------|----------------|
| 1 | `LOCK` | `trading_available` | `trading_locked_collateral` | collateral (cbBTC, cbETH…) | Atom SPOT : `available_quantity −` / `locked_quantity +` | **Inchangé** |
| 2 | `BORROW` | `liability` (crédit) | `trading_available` | USDC | Atom SPOT USDC `quantity/available +` ; dette `metadata.lombard_liability_usdc` | **+USDC** on-chain |

### Invariants patrimoniaux

```
Possession collateral totale = trading_available(collateral) + trading_locked_collateral(collateral)
Net worth USDC impact      = trading_available USDC (actif) − liability USDC (dette)
Privy collateral             ≈ trading_available + trading_locked  (lock = reclassement scope, pas sortie wallet)
Privy USDC                   ≈ trading_available − bundle_cash − vault_position + emprunt net si non dépensé
```

### Cost basis (hors scope Phase 3B writer)

Doctrine parente : lock collateral = **transfert de scope**, PRU inchangé (comme vault fund). **Ne pas implémenter** de mutation cost basis dans Phase 3B initiale — documenter seulement le transfert proportionnel futur (aligné `vault_funding._cost_basis_for_trading_debit`).

---

## Collateral lock rules

### Déclencheur

- OVT : `integration_mode=lombard_v1`, `status=success`, `operation=deposit`, `metadata.lombard_operation=open_loan`
- **Pas** sur steps `approve` / `authorize` seuls

### Quantité

- Parser dry-run (`collateral_quantity_from_metadata`) — **même code path** writer/dry-run
- Refuser le lock si `missing_decimals_gap` ou qty ≤ 0 (log + skip lock, borrow peut rester soumis à règle séparée — **recommandation : transaction atomique tout-ou-rien**)

### Préconditions PE

- Atom SPOT `trading_available` collateral ≥ qty (sinon `lombard.lock.insufficient_trading_available`)
- Client PE lié (`resolve_client_id`)

### Représentation atom (implémentée)

- Portfolio : `direct_portfolio`
- **Lock :** atom SPOT existant — `available_quantity -= qty`, `locked_quantity += qty`, `quantity` inchangé
- **Borrow :** atom SPOT USDC — `quantity/available_quantity += qty` ; `metadata.lombard_liability_usdc` cumulatif
- Trace audit : `metadata.lombard_locks[]` / `metadata.lombard_borrows[]` avec `linked_reference_id=ovt_id`

### Metadata atom (lock trace)

```json
{
  "lombard_locks": [
    {
      "linked_reference_id": "<ovt_cuid>",
      "amount": "0.000125",
      "group_key": "<client idempotency>"
    }
  ]
}
```

---

## Borrow liability rules

### Déclencheur

Même OVT row `open_loan` deposit success que le lock (jambes couplées).

### Quantité

- `borrow_usdc_from_metadata(meta, fallback_decimals=row.asset_decimals)`
- Vérifier cohérence : `parse_raw_amount(row.amount_raw) ≈ borrow_qty` (warning si écart > tolerance)

### Écriture double (implémentée)

1. **Liability +** : `metadata.lombard_liability_usdc` sur atom SPOT USDC (lu par `pe_reader` → scope `liability`)
2. **Trading available USDC +** : `quantity` et `available_quantity` sur le même atom SPOT USDC

Les deux reflètent le crédit USDC côté patrimoine ; la dette est lue via scope `liability` pour net worth (**Phase 4** : brancher `patrimony_merge`).

### Privy

Le crédit USDC on-chain est **réel** — le writer PE **ne touche pas** `person_wallet_balances` (même doctrine que vault fund : scope only, Privy = exécution).

---

## Repay / unlock future model (Phase 3C)

**Hors scope Phase 3B** — spec forward ; implémentation symétrique sur la même représentation (`locked_quantity` / `lombard_liability_usdc`).

| Événement futur | OVT / signal | Mouvement PE | Idempotence |
|-----------------|--------------|--------------|-------------|
| **Repay partiel/total** | OVT `lombard_operation=repay` (à définir) ou step withdraw USDC | `REPAY` : `trading_available USDC −`, `liability USDC −` | `linked_reference_id=ovt_repay_id`, action `lombard.repay_borrow` |
| **Unlock collateral** | Position Morpho collateral → 0 ou OVT close | `UNLOCK` : `trading_locked_collateral −`, `trading_available +` | `linked_reference_id=ovt_unlock_id`, action `lombard.unlock_collateral` |
| **Close loan** | Repay + unlock atomique on-chain | Deux mouvements même transaction ou orchestrateur `close_lombard_loan` | `group_key` repay session + audit par leg |

### Règles

- Repay **sans** unlock si collateral reste engagé (LTV partiel)
- Unlock **sans** repay si dette soldée ailleurs (liquidation — cas edge, reconciliation)
- Dry-run : étendre `lombard.py` pour `lombard_operation=repay` (aujourd’hui **exclu** du open_loan filter)
- Ne jamais supprimer historique audit — mouvements inverses append-only

### Source future repay/unlock

- **Primaire :** OVT metadata + operation (symétrie open_loan)
- **Fallback réconciliation :** delta Morpho position vs PE scopes (`compare.py` gaps)

---

## UX projection rules

### Doctrine (non négociable)

Collateral Lombard **reste dans Mon Trading** :

```
cbBTC disponible      0.50   🔓 tradable   ← scope trading_available
cbBTC en garantie     0.20   🔒 locked      ← scope trading_locked_collateral
```

USDC emprunté : visible en Trading **mais** dette soustraite au **net worth** global.

### État actuel vs cible

| Surface | Aujourd’hui | Cible Phase 3B+ |
|---------|-------------|-----------------|
| Hub wallet positions | `lombardWalletBalanceOverlay.ts` recalcule `availableBalance`, `balance` depuis Morpho | Lire **PE scopes** ; overlay = fallback si PE=0 |
| Sous-titres liste | `balance` total, pas locked/available | Deux lignes ou subtitle `formatLombardPositionSubtitle` branché |
| `tradingAvailableUsdc` (vault cap) | Direct PE payload **sans overlay** (`crypto-wallet/route.ts`) | Inchangé — PE `trading_available` SoT |
| Dashboard crypto | **Sans** overlay Lombard | Inclure locked dans valorisation, liability hors actifs |
| Credit line | Dette à part, **non** déduite header | Dette = `liability` PE, déduite patrimoine merge |
| Détail asset | `lockedVolume` / `availableVolume` API non affichés hero | Afficher depuis scopes |

### Règle anti double comptage overlay ↔ PE

| Phase | Règle |
|-------|-------|
| **Transition** | Si `PE.trading_locked_collateral > 0` pour asset → overlay **ne soustrait pas** Morpho locked (Morpho = sanity check only) |
| **Steady state** | Overlay Morpho **désactivé** pour soldes ; Morpho reste SoT **exécution** / LTV live |
| **Mock** | `simulatePrivyBalances` : ne pas additionner emprunt USDC mock **et** PE liability |

Référence risque audit : `lombard_lock_legacy_without_pe_scope` — inverse après writer : `lombard_overlay_and_pe_double_lock` si les deux soustraient.

---

## Net worth rules

```
Net worth = Σ valorisation(actifs par scope) − Σ valorisation(liabilities)
```

| Composant | Compté comme actif | Compté comme dette |
|-----------|-------------------|-------------------|
| `trading_available` | Oui | — |
| `trading_locked_collateral` | Oui (possession) | — |
| `bundle_*`, `vault_position` | Oui (scopes disjoints) | — |
| `liability` USDC Lombard | — | Oui |
| USDC emprunté en `trading_available` | Oui | — |

**Impact net equity** sur open_loan : neutre si double-entry correct (+USDC actif, +USDC dette).

**Patrimoine merge** (`privy_wallet/patrimony_merge.py` — futur) : inclure `liability` Lombard en soustraction ; ne pas compter collateral locked deux fois avec available.

---

## Idempotency strategy

### Réponses aux questions ouvertes

#### 1. SoT collateral amount ?

**OVT metadata au prepare** (`guarantee_amount` > `guarantee_amount_raw`+decimals). C’est la trace signée client au moment du quote. Morpho on-chain sert à **réconciliation**, pas au premier write.

#### 2. SoT borrow amount ?

**OVT metadata** `borrow_amount_raw` / `borrow_amount` sur la row `deposit` open_loan. Cohérence check avec `amount_raw` OVT.

#### 3. Clé d’idempotence ?

**Recommandation (alignée Phase 3A Vault) :**

| Élément | Valeur |
|---------|--------|
| **`linked_reference_id`** | **`onchain_vault_transactions.id`** de la row **`deposit` / open_loan** (pas approve, pas group_key seul) |
| **`entity_type` audit** | `onchain_vault_transactions` |
| **Actions audit** | `lombard.lock_collateral` et `lombard.open_borrow` (deux actions, **même** `entity_id=ovt_id`) |
| **`group_key`** | Corrélation multi-step + dédup dry-run uniquement |
| **Step id / ledger_entry_id** | Réservé intents/attempts — **pas** clé scope PE |

Rejeu : second appel → `{ skipped: true, reason: "already_applied" }` par action.

**Pourquoi pas group_key seul :** un group contient plusieurs OVT rows (approve + deposit) ; seul deposit porte les montants métier.

**Pourquoi pas step id :** les steps approve n’ont pas de mouvement scope ; couplage open_loan = une unité métier.

#### 4. Lock et liability au même moment ?

**Oui.** Une transaction DB atomique au confirm `open_loan` success :

1. `lock_lombard_collateral(...)`
2. `credit_lombard_borrow(...)`

Si lock échoue (insufficient trading_available collateral), **ne pas** créditer borrow (fail closed). Aligné dry-run qui émet les deux pour la même `reference_id`.

#### 5. Repay / unlock futur ?

Mouvements inverses **séparés**, chacun idempotent par **OVT id** de l’événement repay/unlock. Orchestration possible en service `close_lombard_loan` sans fusionner les clés d’audit.

#### 6. Éviter double comptage overlay vs PE atoms ?

1. Writer PE = **SoT patrimoine** une fois activé
2. Overlay : feature flag `LOMBARD_PE_SCOPES_ENABLED` — si true, read PE only
3. Tests : gap audit `lombard_lock_legacy_without_pe_scope` → 0 après backfill
4. Vault invest : continuer à lire `trading_available` PE **direct** (déjà corrigé `f8e4362`)

---

## Impacted files / services

### Backend — implémenté (Phase 3B)

| Fichier | Rôle |
|---------|------|
| `portfolio_engine/lombard_execution/lombard_funding.py` | `lock_lombard_collateral_from_trading`, `credit_lombard_borrow_to_trading`, `open_lombard_loan` |
| `portfolio_engine/lombard_execution/lombard_ovt_bridge.py` | `apply_lombard_scope_movement_for_ovt`, `plan_lombard_scope_backfill_for_person` |
| `scripts/lombard_scope_backfill.py` | CLI dry-run / `--apply` (local only) |
| `transaction_attempts/dual_write.py` | `_maybe_apply_lombard_scope_movement_after_success` (hook unique) |
| `internal_scope_movements/pe_reader.py` | Lit `available_quantity`, `locked_quantity`, `lombard_liability_usdc` |
| `internal_scope_movements/compare.py` | Gap lock via `trading_locked_collateral` (delta vs solde absolu) |

### Backend — Phase 4 optionnel

| Fichier | Modification future |
|---------|---------------------|
| `portfolio_engine/positions/enums.py` | `COLLATERAL` dans `ALLOWED_POSITION_TYPES` + migration index unique |
| `privy_wallet/patrimony_merge.py` | Net worth − `liability` PE |

### Backend — existant (lecture / dry-run)

| Fichier | Rôle Phase 3B |
|---------|---------------|
| `internal_scope_movements/lombard.py` | SoT dry-run — **réutiliser parsers** |
| `internal_scope_movements/utils.py` | Parsers collateral/borrow |
| `internal_scope_movements/pe_reader.py` | Déjà lit `trading_locked_collateral` + `liability` |
| `internal_scope_movements/compare.py` | Gap / risque double comptage |
| `scripts/internal_scope_movements_audit.py` | Validation pre/post backfill |

### Frontend — transition UX (post-writer)

| Fichier | Rôle |
|---------|------|
| `lombardWalletBalanceOverlay.ts` | Fallback → read-model PE |
| `lombardLedger.ts` | Inchangé prepare ; éventuellement enrichir metadata `collateral_decimals` au prepare |
| `lombardPositionService.ts` | Réconciliation / LTV live |
| `crypto-wallet/route.ts` | Exposer scopes PE locked/liability |
| `dashboardUpstream.ts` | Net worth − liability |
| `lombardCreditLineFormat.ts` | Aligner sur `liability` PE |

### Explicitement hors scope

- Vault (`vault_funding.py`, `vault_ovt_bridge.py`)
- Bundle (`bundle_funding.py`)
- Cost basis executions / PRU mutations
- Migrations Alembic (aucune nouvelle table requise Phase 3B — atoms + audit existants)
- Prod writes / backfill prod

---

## Risks / edge cases

| Risque | Sévérité | Mitigation |
|--------|----------|------------|
| `missing_decimals_gap` (collateral exotique) | Bloquant lock | Refuser writer ; gap audit ; enrichir metadata au prepare |
| `guarantee_amount` ≠ Morpho on-chain post-confirm | Moyen | Réconciliation tick ; ne pas auto-repair sans spec |
| Mock USDC + PE borrow double affichage | UX | Flag mock ; liability PE |
| Insufficient `trading_available` collateral PE | Bloquant | Fail closed ; log structuré (comme vault insufficient) |
| Un seul atom open par `(portfolio, instrument)` | Technique | **Résolu Phase 3B** — `locked_quantity` / metadata liability ; atom COLLATERAL repoussé Phase 4 |
| Approve OVT success sans open_loan | Info | Pas de scope movement |
| Double confirm open_loan | Moyen | Idempotence audit `already_applied` |
| `group_key` réutilisé | Faible | OVT unique constraint + audit by ovt_id |
| Intent sync void / échec | Info | Scope writer indépendant du intent (comme vault) |
| Lombard receipt déclenche vault fund | Critique | Garde `lombard_v1` dans vault hook — test existant |
| Partial loan (future top-up collateral) | Futur | Nouveau OVT / delta lock idempotent |

---

## Implementation phases

| Phase | Contenu | Statut |
|-------|---------|--------|
| **3B.0** | Dry-run Lombard audit CLI | ✅ |
| **3B.1** | Spec | ✅ |
| **3B.2** | `lombard_funding.py` + tests unitaires | ✅ |
| **3B.3** | `lombard_ovt_bridge.py` + hook `dual_write` | ✅ |
| **3B.4** | Spike contrainte unique → alternative `locked_quantity` | ✅ (pas de migration) |
| **3B.5** | Backfill local (`lombard_scope_backfill.py`) | ✅ local E2E |
| **3B.6** | UX read-model PE ; réduire overlay | Phase 4+ |
| **3B.7** | Patrimoine net worth − liability | Phase 4 |
| **3B.8** | Repay/unlock | **Phase 3C** |

**Séquence validée par l’équipe :** spec → **dry-run Lombard** → **writer** → UX.

---

## Test plan

### Tests unitaires writer (futur)

| Test | Assertion |
|------|-----------|
| `test_lock_collateral_debits_trading_available` | SPOT −qty, locked +qty |
| `test_borrow_credits_liability_and_trading_usdc` | liability +qty, trading USDC +qty |
| `test_open_loan_idempotent_double_call` | 1 audit pair, `skipped` second call |
| `test_insufficient_collateral_raises` | Pas de borrow si lock fail |
| `test_missing_decimals_skips_lock` | Gap reported, borrow blocked (fail closed) |
| `test_collateral_cbeth_18_decimals` | Régression dry-run existant |

### Tests intégration hook (futur)

| Test | Assertion |
|------|-----------|
| `test_lombard_open_loan_receipt_creates_scope_atoms` | Miroir `test_vault_forward_hook` |
| `test_lombard_receipt_still_no_vault_fund` | Régression existante |
| `test_lombard_approve_only_no_scope` | Pas de movement |

### Tests dry-run / audit (existants + étendre)

| Test | Fichier |
|------|---------|
| `test_lombard_collateral_lock_expected_movements` | `test_internal_scope_movements_dry_run.py` |
| `test_lombard_borrow_expected_usdc_and_liability` | idem |
| `test_lombard_unknown_collateral_skips_lock_and_reports_gap` | idem |
| Compare `lombard_lock_legacy_without_pe_scope` → absent post-backfill | `compare.py` |

### Tests regression suite ciblée

Après writer : relancer les **36 tests** Phase 2 + 3A + dry-run + vault_forward_hook (+ nouveaux Lombard).

---

## Recommendation

1. ~~Valider spec~~ → **implémenté local** (2026-06-02).
2. Push + deploy → validation prod mini borrow réel (optionnel).
3. **Phase 3C** : repay + unlock sur même représentation PE.
4. **Phase 4** : patrimony merge − liability ; refactor atom COLLATERAL optionnel ; UX overlay → read-model PE.

**Verdict :** Phase 3B writer **livré** — invariants métier validés (lock, borrow, idempotence, audits, gap reports, hooks vault intacts). Compromis technique `locked_quantity` documenté ; modèle comptable pur atom COLLATERAL = Phase 4 optionnelle.

---

## Références codebase

| Domaine | Chemin |
|---------|--------|
| Dry-run Lombard | `services/arquantix/api/services/portfolio_engine/internal_scope_movements/lombard.py` |
| Parsers metadata | `services/arquantix/api/services/portfolio_engine/internal_scope_movements/utils.py` |
| PE scope reader | `services/arquantix/api/services/portfolio_engine/internal_scope_movements/pe_reader.py` |
| Gap compare | `services/arquantix/api/services/portfolio_engine/internal_scope_movements/compare.py` |
| Intent sync | `services/arquantix/api/services/transaction_intents/lombard_intent_sync.py` |
| Dual-write | `services/arquantix/api/services/transaction_attempts/dual_write.py` |
| Vault reference | `services/arquantix/api/services/portfolio_engine/vault_execution/vault_funding.py` |
| Vault bridge | `services/arquantix/api/services/portfolio_engine/vault_execution/vault_ovt_bridge.py` |
| OVT prepare web | `services/arquantix/web/src/lib/portal/lombard/lombardLedger.ts` |
| Overlay UX | `services/arquantix/web/src/lib/portal/lombard/lombardWalletBalanceOverlay.ts` |
| Positions enums | `services/arquantix/api/services/portfolio_engine/positions/enums.py` |
| Tests dry-run | `services/arquantix/api/tests/test_internal_scope_movements_dry_run.py` |
| Test garde Vault/Lombard | `services/arquantix/api/tests/test_vault_forward_hook.py` |
| Closure status | `docs/arquantix/TRANSACTION_SYSTEM_CLOSURE_STATUS.md` |

---

*Phase 3B livrable — audit/spec uniquement. Aucun fichier code modifié.*
