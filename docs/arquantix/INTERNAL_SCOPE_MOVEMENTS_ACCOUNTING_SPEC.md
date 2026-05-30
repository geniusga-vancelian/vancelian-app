# Internal Scope Movements — Accounting Spec (Phase 1)

**Date :** 2026-05-30  
**Statut :** audit / spec uniquement — **aucune implémentation**  
**Auteur :** audit Cursor (read-only codebase + prod doctrine)

---

## Executive summary

Vancelian dispose déjà, en production, d’un **moteur de changement de poche comptable** pour le Bundle : `fund_bundle_cash_leg_from_self_trading` déplace des USDC de `direct_portfolio` (SPOT) vers `bundle_portfolio` (CASH) **sans mouvement Privy**, avec journal shadow, audit PE et projections historique filtrées par scope.

Le **Vault Morpho/Ledgity** et le **Lombard collateral** n’utilisent **pas** ce moteur aujourd’hui :

- Vault : silo `onchain_vault_transactions` + `user_vault_positions`, intents/attempts Phase 2, **aucun atom PE**.
- Lombard : silo OVT multi-step + overlay UI Morpho on-chain, **aucun atom collateral/dette PE**.

**Question centrale :** peut-on créer un moteur générique `internal_scope_movements` réutilisé par bundle funding/release, vault deposit/withdraw et Lombard collateral lock/unlock + borrow liability, **sans modifier la source of truth legacy pendant la transition** ?

**Réponse : oui**, à condition d’une approche **en couches** :

1. **Formaliser les scopes** et les règles anti double-comptage (cette spec).
2. **Phase 2 — PE atoms** : généraliser `bundle_funding.py` en `internal_scope_movements` ; le Bundle existant devient le premier adaptateur (wrapper, pas rewrite).
3. **Phase 3 — journal unifié** : généraliser `bundle_ledger_entries` ou introduire `internal_ledger_movements` (miroir append-only, legacy reste SoT).
4. **Projections** : règles UX distinctes par produit (Vault hors Trading ; Lombard **dans** Trading en deux lignes).

**Doctrine produit retenue :**


| Produit                | Mouvement comptable                                                  | UX                                                                                           |
| ---------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Bundle**             | Trading available → Bundle cash → Bundle positions (réallocation)    | Section Bundle                                                                               |
| **Vault USDC**         | Trading available → Vault position (mono-actif, pas de réallocation) | Section Vault (hors Trading)                                                                 |
| **Lombard collateral** | Trading available → Trading locked collateral                        | Section **Trading**, deux lignes : disponible (cadenas ouvert) / en garantie (cadenas fermé) |
| **Lombard borrow**     | Trading available USDC + ; Liability USDC +                          | Ligne USDC + dette déduite du net worth                                                      |


Le Vault est un **Bundle mono-actif sans réallocation**. Lombard collateral est un **lock intra-Trading** (l’actif reste possédé, indisponible au trade).

---

## 1. Bundle — modèle actuel (référence production)

### 1.1 Mécanisme funding

Fichier pivot : `services/arquantix/api/services/portfolio_engine/bundle_execution/bundle_funding.py`

```
direct_portfolio(entry_asset) SPOT  -= amount   (sync_direct_atom)
bundle_portfolio(entry_asset) CASH  += amount   (BundleOrchestrator._credit_cash_leg)
person_wallet_balances              = inchangé
```

Fonctions :


| Fonction                                  | Sens                                           |
| ----------------------------------------- | ---------------------------------------------- |
| `fund_bundle_cash_leg_from_self_trading`  | Trading → Bundle cash leg                      |
| `release_bundle_cash_leg_to_self_trading` | Bundle cash leg → Trading                      |
| `sync_self_trading_atom_from_custody`     | `expected_direct = privy_qty − Σ(bundle_cash)` |
| `resolve_self_trading_available`          | Solde investissable Mon Trading                |


### 1.2 Couches comptables


| Couche                  | Table / artefact                                      | Rôle                                                                       | SoT ?                        |
| ----------------------- | ----------------------------------------------------- | -------------------------------------------------------------------------- | ---------------------------- |
| **PE atoms**            | `pe_position_atoms`                                   | Positions SPOT direct, CASH bundle, SPOT bundle                            | **Oui** (court terme bundle) |
| **Journal shadow**      | `bundle_ledger_entries`                               | Miroir append-only (`BUNDLE_DEPOSIT`, `PE_TRANSFER`)                       | Non (audit)                  |
| **Audit PE**            | `pe_audit_events`                                     | `bundle.fund_cash_leg`, `bundle.release_cash_leg`                          | Replay / historique          |
| **Ledger comptable PE** | `pe_ledger_entries`                                   | Comptabilité custody/fiat P2P — **pas utilisé pour bundle crypto fund**    | SoT fiat/custody             |
| **On-chain**            | `person_wallet_swaps` + settlement                    | Allocation Li.FI : débit/crédit Privy + débit cash leg + crédit SPOT cible | Exécution                    |
| **Intents / attempts**  | `transaction_intents`, `onchain_transaction_attempts` | Observabilité Phase 2                                                      | Non                          |


Doc : `docs/arquantix/BUNDLE_LEDGER_PHASE4A.md` — atoms PE = vérité ; ledger = shadow.

### 1.3 Réallocation (phase 2 du bundle)

Après fund :

```
bundle CASH USDC  →  (legs Li.FI)  →  bundle SPOT BTC/ETH/…
```

Hooks : `bundle_lifi_leg_service.py`, `pe_settlement.py` (`apply_allocation_leg_atoms`), `record_bundle_deposit` / `record_allocation_buy` dans `bundle_ledger/service.py`.

### 1.4 Projections historique


| Fichier                            | Rôle                                                                                |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| `bundle_pe_transactions.py`        | Transferts fund/release visibles Mon Trading (`Transfert vers Bundle`)              |
| `bundle_portfolio_transactions.py` | Swaps + transferts côté espace Bundle                                               |
| `bundle_projection.py`             | Agrégats allocation par `batch_id`                                                  |
| `self_trading_projection.py`       | **Exclut** swaps internes bundle (`bundle_internal_swap`, `portfolio_scope=bundle`) |


### 1.5 Anti double-comptage patrimoine

- Enveloppes PE **disjointes** : `direct_portfolio` SPOT + `bundle_portfolio` CASH + SPOT.
- Formule custody : `expected_direct = privy − bundle_cash`.
- Invariant G (`invariant_g.py`) : Privy ≈ direct SPOT + bundle SPOT (cash legs exclus).
- NAV admin : somme buckets disjoints (`test_clients/router.py`).

---

## 2. Vault USDC — gap actuel

### 2.1 Modèle production


| Couche           | Implémentation                                                            | PE impact |
| ---------------- | ------------------------------------------------------------------------- | --------- |
| Exécution        | `onchain_vault_transactions` (Prisma/web, `morphoVaultLedger.ts`)         | Aucun     |
| Position agrégée | `user_vault_positions.principal_net_raw`                                  | Aucun     |
| Observabilité    | `morpho_intent_sync.py`, `dual_write_vault_step`                          | Aucun     |
| Privy ledger     | Pas de settlement type Li.FI au confirm                                   | Aucun     |
| Cost basis       | Doctrine : transfert de poche, PRU inchangé (`COST_BASIS_V2_DOCTRINE.md`) | Aucun     |


### 2.2 Gap vs modèle bundle


| Capacité bundle                                         | Vault aujourd’hui                                             |
| ------------------------------------------------------- | ------------------------------------------------------------- |
| `direct SPOT −` / destination scope `+`                 | ❌                                                             |
| Cost basis transféré avec l’atom                        | ❌                                                             |
| Journal shadow (`BUNDLE_DEPOSIT` équivalent)            | ❌                                                             |
| Projection `-10 Transfert vers Vault` / `+10 Réception` | ❌ (silo vault UI)                                             |
| `expected_direct = privy − vault_usdc`                  | ❌ (`atom_vaults` slot Invariant G = `_VAULTS_INCLUDED False`) |
| Section patrimoine distincte sans double comptage       | ⚠️ partiel via `user_vault_positions` seulement               |


### 2.3 Cible (alignée ENTERPRISE §5)

```
VAULT_DEPOSIT intent → attempts → OVT success
  → internal_scope_movement(trading_available → vault_position)
  → pe_position_atoms update
  → (optionnel) vault_ledger shadow entry
```

Vault deposit = **Bundle fund sans étape Li.FI** + mouvement on-chain deposit Morpho (comme un leg d’exécution, pas comme un changement d’actif).

---

## 3. Lombard — spécificité collateral

### 3.1 Modèle production


| Couche          | Implémentation                                                                                      |
| --------------- | --------------------------------------------------------------------------------------------------- |
| OVT             | `lombardLedger.ts` → `integration_mode=lombard_v1`, steps approve/authorize + `deposit` (open_loan) |
| Collateral lock | **Metadata OVT** + lecture Morpho SDK — pas d’écriture PE                                           |
| Dette USDC      | Morpho on-chain + overlay UI                                                                        |
| Overlay UX      | `lombardWalletBalanceOverlay.ts` : `availableBalance = privy − locked`, `balance = exposure totale` |
| Intents         | `lombard_intent_sync.py`, parent `lombard_borrow` + steps                                           |
| PE              | **Aucun** atom collateral/borrowing Lombard                                                         |


### 3.2 Doctrine UX (non négociable)

Lombard collateral **reste dans la section Trading** :

```
cbBTC disponible     0.50   🔓 tradable
cbBTC en garantie    0.20   🔒 locked
```

Patrimoine global : les **deux** lignes comptent comme actifs du client (possession).  
La **liability USDC** empruntée est une **dette** déduite du net worth.

Comptablement :

```
collateral lock :  trading_available cbBTC −0.1  →  trading_locked_collateral cbBTC +0.1
borrow          :  trading_available USDC +1000  +  liability USDC +1000
```

Ce n’est **pas** un changement de section UI (contrairement au Vault). C’est un **sous-scope intra-Trading**.

### 3.3 Gaps vs modèle cible


| Capacité                          | État                                                          |
| --------------------------------- | ------------------------------------------------------------- |
| Scope `trading_locked_collateral` | Absent (overlay ad hoc)                                       |
| Atom PE `COLLATERAL`              | Enum défini, **non dans ALLOWED_POSITION_TYPES** pour Lombard |
| Atom PE `BORROWING` (Lombard)     | Réservé P2P lending interne                                   |
| OVT step collateral_supply dédié  | Collateral en metadata seulement                              |
| Repay / unlock / close            | Non implémenté                                                |
| Cost basis collateral locked      | Non géré                                                      |


---

## 4. Modèle de scopes proposé

### 4.1 Enum scopes (formalisation)

Scopes **logiques** — pas nécessairement une colonne unique dès Phase 1 ; peuvent être dérivés de `(portfolio_id, position_type, metadata.scope)` :


| Scope ID                    | Description                          | Portfolio PE                                 | PositionType        | metadata hint                                            |
| --------------------------- | ------------------------------------ | -------------------------------------------- | ------------------- | -------------------------------------------------------- |
| `trading_available`         | Crypto tradable Mon Trading          | `direct_portfolio`                           | `spot`              | `scope=trading_available`                                |
| `trading_locked_collateral` | Garantie Lombard (non tradable)      | `direct_portfolio`                           | `collateral`*       | `scope=trading_locked_collateral`, `lock_reason=lombard` |
| `bundle_cash`               | USDC réservé en attente d’allocation | `bundle_portfolio`                           | `cash`              | `role=bundle_cash_leg` (existant)                        |
| `bundle_position`           | Actifs investis dans un bundle       | `bundle_portfolio`                           | `spot`              | `bundle_batch_id`, etc.                                  |
| `vault_position`            | Encours vault earn (USDC ou parts)   | `vault_portfolio`* ou produit dédié          | `spot` / `lending`* | `vault_address`, `integration_mode`                      |
| `liability`                 | Dette empruntée (Lombard USDC)       | `direct_portfolio` ou `liability_portfolio`* | `borrowing`*        | `protocol=lombard`, `market_id`                          |


 Types forward-compat déjà esquissés : `ProductType.YIELD_VAULT`, `PositionType.COLLATERAL`, `WalletType.VAULT_ACCOUNT`, `InstrumentType.VAULT_SHARE`.

### 4.2 Moteur générique (spec)

```python
# Spec — pas de code
internal_scope_movement(
    *,
    person_id, client_id,
    movement_type: InternalScopeMovementType,  # fund | release | lock | unlock | borrow | repay
    source_scope: ScopeRef,
    destination_scope: ScopeRef,
    asset: str,
    instrument_id: UUID,
    quantity: Decimal,
    cost_basis_eur: Decimal | None,  # transfert, pas nouveau PRU
    idempotency_key: str,
    linked_reference: LinkedReference,  # OVT id, batch_id, lombard group_key, …
    on_chain_tx_hash: str | None,
) -> InternalScopeMovementResult
```

**Adaptateurs produit** (wrappers, pas rewrite bundle) :


| Adaptateur                               | Appelle                                               | Legacy trigger        |
| ---------------------------------------- | ----------------------------------------------------- | --------------------- |
| `fund_bundle_cash_leg_from_self_trading` | `movement_type=FUND`, `trading_available→bundle_cash` | Inchangé (wrapper)    |
| `fund_vault_from_self_trading`           | `FUND`, `trading_available→vault_position`            | OVT deposit success   |
| `release_vault_to_self_trading`          | `RELEASE`, `vault_position→trading_available`         | OVT withdraw success  |
| `lock_lombard_collateral`                | `LOCK`, `trading_available→trading_locked_collateral` | OVT open_loan confirm |
| `unlock_lombard_collateral`              | `UNLOCK`, inverse                                     | Futur repay/close     |
| `credit_lombard_borrow`                  | `BORROW`, `liability+` + `trading_available USDC+`    | OVT open_loan confirm |


### 4.3 Conservation patrimoniale

Pour tout mouvement **interne** (pas d’acquisition/cession économique) :

```
Σ scopes actifs (par asset) = possession totale client
Net worth = Σ actifs − Σ liabilities
```

Formule custody étendue :

```
privy_on_chain(asset) ≈ trading_available(asset)
                        + trading_locked_collateral(asset)
                        + Σ bundle_cash(asset)
                        + Σ bundle_position(asset)   # après allocation, actif peut changer
                        + vault_position_usdc(asset) # USDC dans vault = hors wallet Privy
                        + reserved_pending(asset)
```

Note : après deposit vault, USDC **quitte** le wallet Privy → le scope `vault_position` compense la baisse Privy ; `trading_available` baisse via le fund PE **avant ou au confirm** (ordre à figer en Phase 2 impl).

---

## 5. Exemples comptables

### 5.1 Vault deposit 10 USDC


| Scope                    | Avant | Mouvement        | Après |
| ------------------------ | ----- | ---------------- | ----- |
| `trading_available` USDC | 100   | −10              | 90    |
| `vault_position` USDC    | 0     | +10              | 10    |
| Privy on-chain USDC      | 100   | −10 (tx deposit) | 90    |
| **Net worth USDC**       | 100   | 0                | 100   |


Historique Trading : `-10 USDC · Transfert vers Vault Morpho`  
Historique Vault : `+10 USDC · Réception depuis Trading`  
Intent : `morpho_earn` confirmed ; attempt deposit confirmed (Phase 2 ✅).

### 5.2 Vault withdraw 10 USDC

Inverse du deposit. OVT withdraw success → `vault_position −10`, `trading_available +10`, Privy +10.

### 5.3 Bundle invest 10 USDC (rappel — inchangé)


| Scope                    | Mouvement       |
| ------------------------ | --------------- |
| `trading_available` USDC | −10             |
| `bundle_cash` USDC       | +10             |
| Privy                    | inchangé (fund) |


Puis allocation : `bundle_cash −10`, `bundle_position BTC +ε`, Privy ± via Li.FI.

### 5.4 Lombard collateral 0.1 cbBTC


| Scope                             | Mouvement                                          |
| --------------------------------- | -------------------------------------------------- |
| `trading_available` cbBTC         | −0.1                                               |
| `trading_locked_collateral` cbBTC | +0.1                                               |
| Privy cbBTC                       | inchangé (collateral on Morpho, même wallet owner) |


UX Trading (même section) :

- cbBTC disponible : 0.4 (🔓)
- cbBTC en garantie : 0.1 (🔒)

Patrimoine cbBTC total : 0.5.

### 5.5 Lombard borrow 1000 USDC


| Scope                    | Mouvement                       |
| ------------------------ | ------------------------------- |
| `trading_available` USDC | +1000                           |
| `liability` USDC         | +1000                           |
| Privy USDC               | +1000 (crédit emprunt on-chain) |


Net worth : actifs +1000, dette +1000 → impact net sur equity selon usage des fonds (ici neutre si comptabilité full double-entry).

---

## 6. Règles de projection UX

### 6.1 Principes


| Règle                             | Détail                                                                                             |
| --------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Legacy SoT pendant transition** | OVT / Privy / PE atoms existants restent autoritaires ; projections lisent ces sources             |
| **Pas de double ligne**           | Un mouvement interne = une ligne debit source OU credit destination selon la vue                   |
| **Scope filtre**                  | `self_trading_projection.py` pattern : exclure internes, inclure transferts cross-scope explicites |


### 6.2 Par surface


| Surface                      | Inclut                                                                                                     | Exclut                                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Mon Trading — historique** | Transferts vers/depuis Bundle, Vault ; Lombard borrow ; locks/unlocks en événements explicites si souhaité | Swaps bundle internes, allocations Li.FI bundle |
| **Mon Trading — positions**  | Lignes `trading_available` + `trading_locked_collateral` (Lombard)                                         | Positions `vault_position` (section Vault)      |
| **Espace Bundle**            | fund, release, swaps allocation                                                                            | Transferts depuis Trading (miroir)              |
| **Espace Vault**             | deposit, withdraw, yield                                                                                   | USDC encore en Trading available                |
| **Patrimoine global**        | Somme scopes disjoints ; dettes soustraites                                                                | Double comptage Trading + Vault pour même USDC  |


### 6.3 Lombard — règle spécifique

- **Ne pas** déplacer collateral vers une section « Lombard assets ».
- Dériver les deux lignes depuis :
  - atom / scope `trading_available` → ligne 🔓
  - atom / scope `trading_locked_collateral` → ligne 🔒
- Fallback transition : conserver `lombardWalletBalanceOverlay.ts` jusqu’à alimentation PE ; overlay devient **read-model** du scope locked.

### 6.4 Vault — règle spécifique

- Vault **sort** de Mon Trading (comme Bundle a sa section).
- Mon Trading voit le **transfert sortant** ; Vault voit l’**encours**.

---

## 7. Fichiers et services impactés (future impl)

### 7.1 Cœur moteur (nouveau / généralisé)


| Fichier actuel                                             | Rôle future                                                                                     |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `bundle_execution/bundle_funding.py`                       | Devient adaptateur Bundle ou délègue à `internal_scope_movements.py`                            |
| **(nouveau)** `portfolio_engine/internal_scope_movements/` | Moteur générique, enums scopes, idempotence                                                     |
| `direct_overlay.py`                                        | `sync_self_trading_atom_from_custody` étendu (`− bundle_cash − vault_usdc − locked_collateral`) |
| `invariants/invariant_g.py`                                | Activer `atom_vaults`, inclure locked collateral                                                |


### 7.2 Journal


| Fichier actuel             | Rôle future                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------- |
| `bundle_ledger/service.py` | Généraliser ou parallèle `internal_ledger_movements`                                |
| `bundle_ledger/enums.py`   | Ajouter `VAULT_DEPOSIT`, `VAULT_WITHDRAWAL`, `COLLATERAL_LOCK`, `LIABILITY_OPEN`, … |


### 7.3 Vault


| Fichier                                     | Hook                                                          |
| ------------------------------------------- | ------------------------------------------------------------- |
| `web/src/lib/portal/morphoVaultLedger.ts`   | Post-confirm → appeler API scope movement (async, idempotent) |
| `transaction_intents/morpho_intent_sync.py` | Après `mark_morpho_intent_confirmed`                          |
| `user_vault_positions` (Prisma)             | Reste agrégat UI ; PE atom = SoT patrimoine cible             |


### 7.4 Lombard


| Fichier                                       | Hook                                   |
| --------------------------------------------- | -------------------------------------- |
| `web/src/lib/portal/lombard/lombardLedger.ts` | Post-confirm open_loan                 |
| `lombard_intent_sync.py`                      | Step confirm                           |
| `lombardWalletBalanceOverlay.ts`              | Migration vers read-model scopes       |
| `lombardWalletTransactions.ts`                | Historique borrow + futurs lock/unlock |


### 7.5 Projections


| Fichier                                   | Extension                                                         |
| ----------------------------------------- | ----------------------------------------------------------------- |
| `bundle_pe_transactions.py`               | Modèle pour `vault_pe_transactions`, `lombard_scope_transactions` |
| `self_trading_projection.py`              | Exclusions scope vault/bundle ; inclusions lock lines             |
| `bundle_projection.py`                    | Inchangé (bundle only)                                            |
| `privy_wallet/patrimony_merge.py`         | NAV = scopes PE, pas seulement Privy brut                         |
| `cryptoTransactionHistoryFormat.ts` (web) | Titres transferts vault / lock collateral                         |


### 7.6 Phase 2 observabilité (déjà en place)


| Fichier                       | Lien                                                             |
| ----------------------------- | ---------------------------------------------------------------- |
| `dual_write.py`               | Attempts on-chain par step — **orthogonal** au scope movement PE |
| `transaction_trace_logger.py` | Traces `attempt_confirmed` — complémentaire                      |


`pe_ledger_entries` : couche **custody/fiat** distincte ; ne pas mélanger avec scope crypto interne sans spec dédiée.

---

## 8. Risques de double comptage


| Risque                                 | Mitigation                                                                                 |
| -------------------------------------- | ------------------------------------------------------------------------------------------ |
| USDC compté Trading + Vault            | Scopes disjoints ; `vault_position` exclu de `trading_available` ; formule custody         |
| USDC compté Trading + Bundle cash      | Existant : `privy − bundle_cash`                                                           |
| cbBTC compté 2× (available + locked)   | **Non** : available + locked = total ; lignes UI, pas double NAV                           |
| Collateral lock + retrait Privy        | Lock = mouvement scope only ; Privy total cbBTC unchanged until on-chain supply            |
| Vault deposit sans fund PE             | Gap actuel — fund PE au confirm **obligatoire**                                            |
| Lombard overlay + futurs atoms         | Période transition : overlay **ou** atoms, pas les deux en SoT                             |
| `user_vault_positions` + PE vault atom | UVP = dérivé OVT ; PE = SoT patrimoine ; reconciler, pas additionner                       |
| Bundle rewrite casse prod              | Wrapper adaptateur ; tests régression `test_phase2_forward_dual_write` + bundle invest E2E |
| Intent/attempt + scope movement        | Deux couches : attempts = exécution ; scope = comptabilité patrimoine                      |


---

## 9. Phases migration / implémentation (recommandées)

### Phase 1 — Spec (ce document) ✅

Audit, scopes, règles UX, anti double-comptage. **Aucun code.**

### Phase 2 — Formalisation read-model (sans mutation soldes)

- Documenter mapping scope → sources legacy (OVT, audit, overlay).
- Étendre rapports dry-run : `verify_internal_scope_consistency` (comme `verify_vault_forward_attempt_consistency`).
- Lombard : overlay alimenté par Morpho **documenté** comme proxy de `trading_locked_collateral`.

**Legacy SoT : inchangé.**

### Phase 3 — PE atoms (moteur scope, bundle wrapper)

- Introduire `internal_scope_movements` ; `fund_bundle_cash_leg` délègue (comportement identique).
- Vault : hook confirm → `trading_available −` / `vault_position +`.
- Lombard : hook open_loan → lock collateral + liability + USDC credit.
- Étendre Invariant G.
- Activer `PositionType.COLLATERAL` pour Lombard locked.

**Legacy SoT : OVT + Privy ; PE devient SoT patrimoine.** Shadow ledger miroir.

### Phase 4 — Journal unifié

- Généraliser `bundle_ledger_entries` → `internal_ledger_movements` (table nouvelle **avec validation migration explicite**).
- Idempotence `{source_system}:{source_id}:{movement_type}:{direction}`.

### Phase 5 — Projections & UX

- Historique transferts vault.
- Lombard deux lignes depuis scopes (remplace overlay progressif).
- Patrimoine global via somme scopes.

### Phase 6 — Réconciliation Controller (Phase 3 enterprise)

- Gap types : `scope_movement_missing`, `scope_imbalance_vs_privy`, `ovt_success_without_scope_fund`.
- Replay idempotent scope movements depuis OVT/audit.

---

## 10. Plan de tests (future)


| Test                   | Assertion                                                                         |
| ---------------------- | --------------------------------------------------------------------------------- |
| Bundle fund regression | Comportement identique post-wrapper                                               |
| Vault deposit E2E      | `trading_available −10`, `vault_position +10`, attempt confirmed, 1 seul movement |
| Vault withdraw E2E     | Inverse idempotent                                                                |
| Lombard lock           | `available −0.1`, `locked +0.1`, Privy cbBTC unchanged                            |
| Lombard borrow         | `liability +1000`, `trading_available USDC +1000`                                 |
| Double confirm OVT     | 1 scope movement (idempotence)                                                    |
| Invariant G extended   | Privy ≈ sum scopes                                                                |
| Patrimoine merge       | Trading 90 + Vault 10 = 100, pas 110                                              |
| Projection Trading     | Vault transfer visible ; vault balance not in Trading positions                   |
| Projection Lombard     | Deux lignes cbBTC ; net worth − dette USDC                                        |
| Gap report             | 0 `scope_inconsistent_with_legacy` sur session forward                            |


---

## 11. Recommandation : projection-only vs PE atoms vs internal_ledger_movements


| Approche                         | Avantages                                                               | Inconvénients                                                                 | Verdict                                                |
| -------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------ |
| **A. Projection-only**           | Zero risque soldes ; rapide pour UX Lombard 2 lignes                    | Pas de SoT patrimoine unifié ; double comptage latent (vault) ; replay faible | **Insuffisant seul** — OK transition Lombard overlay   |
| **B. PE atoms** (modèle bundle)  | SoT patrimoine ; invariants ; cost basis transfert ; aligné prod bundle | Impl PE ; migration progressive                                               | **Recommandé — cœur du moteur**                        |
| **C. internal_ledger_movements** | Audit event-sourced ; replay enterprise ; indépendant UI                | Nouvelle table (migration) ; miroir si sans PE                                | **Recommandé — Phase 4 shadow**, comme `bundle_ledger` |


**Recommandation finale :**

1. **PE atoms + `internal_scope_movements`** comme moteur comptable (B), en **wrappant** le bundle existant.
2. `**internal_ledger_movements`** en miroir append-only (C), généralisation de Phase 4A bundle ledger.
3. **Projections** comme read-model dérivé (A), jamais SoT.
4. **Legacy** (OVT, Privy, `user_vault_positions`) reste SoT **exécution** pendant transition ; PE devient SoT **patrimoine** par produit activé (Vault puis Lombard).
5. **Pas de repair mode** : dry-run gaps + micro-sync idempotent ciblée (pattern Phase 2 vault).

---

## 12. Réponse à la question centrale

**Peut-on créer un moteur générique `internal_scope_movements` réutilisé par bundle, vault et Lombard, sans modifier la SoT legacy actuelle ?**

**Oui**, avec cette séquence :

- Bundle : **déjà implémenté** — extraction en moteur générique sans changer le comportement.
- Vault : **Bundle mono-actif** — `trading_available → vault_position`, section UX Vault séparée.
- Lombard collateral : **lock intra-Trading** — `trading_available → trading_locked_collateral`, deux lignes UX, même section Trading.
- Lombard borrow : **liability + crédit USDC** — dette déduite du net worth.

Unification long terme : **Bundle · Vault · Lombard** = variantes d’un même moteur de **changement de scope interne**, avec exécution on-chain (OVT / Li.FI / Morpho) en couche séparée (intents/attempts Phase 2).

---

## 13. Références codebase


| Domaine              | Chemins                                                                               |
| -------------------- | ------------------------------------------------------------------------------------- |
| Bundle funding       | `services/arquantix/api/services/portfolio_engine/bundle_execution/bundle_funding.py` |
| PE atoms             | `services/arquantix/api/services/portfolio_engine/positions/models.py`, `enums.py`    |
| PE ledger (fiat)     | `services/arquantix/api/services/portfolio_engine/ledger_entries/models.py`           |
| Bundle ledger shadow | `services/arquantix/api/services/portfolio_engine/bundle_ledger/`                     |
| Audit PE             | `services/arquantix/api/services/portfolio_engine/hardening/audit_models.py`          |
| Projections          | `bundle_pe_transactions.py`, `bundle_projection.py`, `self_trading_projection.py`     |
| Vault OVT            | `services/arquantix/web/src/lib/portal/morphoVaultLedger.ts`                          |
| Vault positions      | `user_vault_positions` (Prisma schema)                                                |
| Lombard              | `web/src/lib/portal/lombard/lombardLedger.ts`, `lombardWalletBalanceOverlay.ts`       |
| Invariant G          | `services/arquantix/api/services/portfolio_engine/invariants/invariant_g.py`          |
| Enterprise target    | `docs/arquantix/ENTERPRISE_TRANSACTION_REPLAY_ARCHITECTURE.md` §3, §5, §6             |
| Cost basis doctrine  | `docs/arquantix/COST_BASIS_V2_DOCTRINE.md`                                            |
| Bundle ledger doc    | `docs/arquantix/BUNDLE_LEDGER_PHASE4A.md`                                             |


---

*Phase 1 livrable — audit/spec uniquement. Aucun fichier code modifié.*