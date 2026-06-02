# Lombard multi-step — Retry, états terminaux & annulation métier

**Date :** 2026-06-02  
**Statut :** spec / doctrine — **aucune implémentation**  
**Prérequis :** Phase 3B Lombard forward validée ([`TRANSACTION_ENGINE_PHASE3B_CLOSURE_STATUS.md`](./TRANSACTION_ENGINE_PHASE3B_CLOSURE_STATUS.md))  
**Spec parente :** [`INTERNAL_SCOPE_MOVEMENTS_PHASE3B_LOMBARD_SPEC.md`](./INTERNAL_SCOPE_MOVEMENTS_PHASE3B_LOMBARD_SPEC.md) · [`TRANSACTION_INTENTS_DEFI.md`](./TRANSACTION_INTENTS_DEFI.md)

---

## Executive summary

Le moteur comptable Lombard Phase 3B (PE lock + borrow) est **robuste sur le succès final**. Le gap restant est **produit / état** : une transaction multi-step peut rester « entre deux eaux » (`partial`, stepper trompeur, retry non lié).

**Doctrine figée :** toute transaction utilisateur doit finir dans un **état terminal clair**. Lombard n’est pas une exception.

**Prochaine implémentation prioritaire :** **R1 — confirm incrémental par step** (bug racine : approve on-chain OK non persisté backend quand `open_loan` revert).

---

## Incident prod de référence (2026-06-02)

**Person pilote :** `8b0e0044-f1ef-47a5-99d4-370598a77492` (Gael)  
**Audit :** prod read-only, aucune mutation.

### Tentative 1 — échec partiel

| Champ | Valeur |
|-------|--------|
| **group_key** | `ce0bf19a-8917-4a90-bc03-6ce43680e503` |
| **Timestamp** | 2026-06-02 ~09:56 UTC |
| **intent_id** | `43237b4a-eeb3-4563-9988-69f3255f390b` |
| **Intent status** | `partial` (non terminal) |
| **OVT approve** | `cmpwgptvo005yad01dabqrwc3` — `pending`, tx_hash **null** |
| **OVT open_loan** | `cmpwgptvt005zad01v8cnr493` — `reverted` |
| **tx_hash open_loan** | `0x6f4989d84d5946da32c987a16a0403a955a79b3cd245b8d2f937a556434af577` |
| **attempt open_loan** | `a9c10ecd-7827-4f52-ac91-c5272ccc9c8e` — `reverted` |
| **Attempt approve** | absent |
| **PE audits** | aucun (correct — pas de borrow ouvert) |

**UX observée :** approve perçu OK · open_loan revert · message « On-chain transaction reverted » · bouton « Réessayer ».

**Cause racine identifiée :** sur revert `open_loan`, le client confirme uniquement l’OVT en échec ; l’approve exécuté on-chain dans la même session n’est **pas** confirmé backend (confirm batch en fin de boucle jamais atteint).

### Retry — succès

| Champ | Valeur |
|-------|--------|
| **group_key** | `f83658c9-3b04-4de5-826e-f03ef7c3bba6` |
| **Timestamp** | 2026-06-02 ~10:01 UTC |
| **intent_id** | `525f2e93-dae9-4f1f-bd0c-9e2754cfb820` |
| **Intent status** | `confirmed` |
| **OVT open_loan** | `cmpwgx3dz0060ad01fm3e97xq` — `success` |
| **tx_hash** | `0x56d6c715e501ec1092c6e7bace0545ababa2dc57cb30ce4eeef10919a5287a61` |
| **Approve step** | absent (allowance on-chain suffisante — Morpho SDK skip) |
| **PE audits** | `lombard.lock_collateral` + `lombard.open_borrow` |

### Lien actuel entre les deux flows

| Élément | État actuel |
|---------|-------------|
| `logical_borrow_id` | **absent** |
| `retry_of_group_key` | **absent** |
| Relation DB | **deux intents / deux groups indépendants** |
| Verdict utilisateur | succès perçu, mais historique fragmenté |

---

## Doctrine — état terminal utilisateur

### Principe global (aligné Swap / Vault / Bundle)

| Produit | Attendu |
|---------|---------|
| LI.FI swap | success **ou** failed / reconciliation_required |
| Vault deposit | success **ou** failed |
| Bundle invest | success **ou** failed / reconciliation_required |
| **Lombard borrow** | **success **ou** failed** — même si multi-step |

**Interdit :** laisser une transaction « en cours » indéfiniment (`partial` sans issue, spinner sans TTL, stepper incohérent avec la DB).

### États terminaux globaux

| État | Signification |
|------|---------------|
| **`confirmed`** | Opération réussie ; effet métier réel (borrow ouvert, PE écrit si applicable) |
| **`failed_final`** | Échec définitif ; pas d’effet métier Lombard |
| **`cancelled_business`** | Clôture métier sans succès (abandon utilisateur, retry épuisé sans succès) |
| **`reconciliation_required`** | État ambigu (timeout receipt, divergence on-chain vs DB) — terminal transitoire ops |

États **non terminaux** (transitoires ou intermédiaires) : `created`, `awaiting_signature`, `submitted`, `partially_confirmed`, `retryable_failed`, `retrying`.

État terminal **de remplacement** : `superseded` — tentative initiale remplacée par un retry réussi.

---

## Annulation métier ≠ rollback blockchain

### Cas Lombard : approve OK, open_loan KO

| Couche | État |
|--------|------|
| **On-chain** | Allowance token peut **rester** (pas de revoke économique en v1) |
| **Métier** | Emprunt **non ouvert** |
| **Collateral** | **Non locké** (pas de supply Morpho effectif) |
| **USDC** | **Non empruntés** |
| **PE** | **Aucun** `lombard.lock_collateral` / `lombard.open_borrow` |

**État métier documenté :**

```
borrow_not_opened
collateral_not_locked
usdc_not_borrowed
approval_may_remain_on_chain
```

La transaction utilisateur **peut et doit** être clôturée en `failed_final` ou `cancelled_business` sans rollback on-chain obligatoire.

### UX type — échec partiel récupérable

> Autorisation validée  
> Emprunt non ouvert  
> Aucun USDC emprunté  
> Aucune garantie déposée  
> Vous pouvez réessayer ou fermer cette tentative

### UX type — échec définitif (retry épuisé)

> Échec définitif  
> Aucun emprunt n’a été ouvert  
> Votre garantie n’a pas été déposée  
> L’autorisation de garantie a pu être validée, mais l’emprunt n’a pas été ouvert. Aucun montant n’a été emprunté.

---

## États cibles Lombard

| Statut | Terminal ? | Description |
|--------|------------|-------------|
| **`confirmed`** | Oui | Toutes les steps requises success ; borrow ouvert |
| **`retryable_failed`** | Non | Approve OK (ou allowance suffisante) ; open_loan revert/fail ; retry autorisé |
| **`retrying`** | Non | Retry en cours (consentement utilisateur, nouvelle signature) |
| **`failed_final`** | Oui | Échec définitif ; retry épuisé ou non recoverable |
| **`cancelled_business`** | Oui | Utilisateur ferme / abandon sans succès |
| **`reconciliation_required`** | Transitoire | Timeout ou ambiguïté receipt |
| **`superseded`** | Oui | Tentative remplacée par un retry `confirmed` |

### Flux principal (doctrine)

```
1. approve collateral success (confirmée backend)
2. open_loan revert/fail
   → retryable_failed
3. utilisateur retry open_loan (max 1 en v1)
   → retrying
4a. retry success → confirmed (global) ; tentative initiale → superseded
4b. retry fail   → failed_final / cancelled_business
```

---

## State machine Lombard multi-step

```
prepared
  → awaiting_signature
  → submitted
  → partially_confirmed     (≥1 step confirmée backend, borrow pas terminal)
  → retryable_failed        (recoverable)
  → retrying
  → confirmed               [TERMINAL — succès]
  → failed_final            [TERMINAL — échec]
  → cancelled_business      [TERMINAL — abandon]
  → reconciliation_required [TERMINAL transitoire — ops]
  → superseded              [TERMINAL — remplacé par retry OK]
```

**Règle d’or :** une `logical_borrow_id` → **un seul** verdict global :

- `confirmed` si au moins un retry a réussi ;
- `failed_final` / `cancelled_business` si tous les essais ont échoué ou abandon.

---

## SoT — où vit l’état user-facing ?

| Couche | Rôle | Terminal ? |
|--------|------|------------|
| **`transaction_intents`** | SoT opération produit Lombard | **Primaire** |
| **`onchain_vault_transactions`** | Ledger par step | Par step |
| **`onchain_transaction_attempts`** | Observabilité Phase 2 | Par attempt |
| **`transaction_trace_events`** | Timeline audit | Événements |
| **Session UI React** | Éphémère | **Non** |

**Décision :** statut affiché = `transaction_intents.status` + `metadata_json.terminal_outcome` + projection `logical_borrow_id`.

---

## Modèle DB minimal (via `metadata_json`)

Pas de nouvelle table obligatoire en v1. Champs à standardiser dans `transaction_intents.metadata_json` :

| Champ | Type | Description |
|-------|------|-------------|
| **`logical_borrow_id`** | UUID | ID stable pour toute la séquence (initial + retries) |
| **`retry_of_group_key`** | string | group_key de la tentative précédente (null si initial) |
| **`retry_of_intent_id`** | UUID | intent parent (optionnel, redondant avec group) |
| **`retry_attempt_number`** | int | `0` = initial, `1` = premier retry |
| **`max_retry_attempts`** | int | `1` en v1 |
| **`terminal_outcome`** | enum string | `borrow_opened` \| `borrow_not_opened` \| `retry_exhausted` \| `cancelled_by_user` |
| **`superseded_by_group_key`** | string | Rempli sur intent initial quand retry success |
| **`superseded_by_intent_id`** | UUID | idem |
| **`group_key`** | string | Déjà présent — = idempotency key prepare |

Chaque tentative conserve son **propre `group_key`** (audit trail Phase 2 intact).

### Projection user-facing (read model)

Service ou vue read-only :

```text
logical_borrow_id
  terminal_status: confirmed | failed_final | cancelled_business | reconciliation_required
  winning_group_key: <group du confirmed, si existe>
  attempts: [{ retry_attempt_number, group_key, intent_status, ... }]
```

### Marquage par entité (retry épuisé)

| Entité | Action |
|--------|--------|
| Intent retry | `failed_final` |
| Intent initial | `superseded` ou `failed_final` |
| OVT open_loan | `reverted` / `failed` (inchangé) |
| Attempt | `reverted` / `failed` |
| Trace | `lombard.retry_exhausted` |

### Marquage (retry success)

| Entité | Action |
|--------|--------|
| Intent retry | `confirmed` |
| Intent initial | `superseded` + `superseded_by_*` |
| OVT open_loan initial | conserve `reverted` (historique) |
| OVT open_loan retry | `success` |
| PE | hook sur OVT retry success uniquement |
| UX | fusionner les deux flows = **une** opération logique terminée |

---

## Règles de retry (v1)

| Règle | Valeur |
|-------|--------|
| **`max_retry_attempts`** | **1** |
| Step retryable | **`open_loan` uniquement** |
| Skip approve | **Oui** si allowance on-chain suffisante (Morpho SDK) |
| Consentement | **Obligatoire** — nouvelle signature utilisateur |
| Auto-retry blockchain | **Interdit** |
| Nouvel intent par retry | **Oui** (nouveau group_key) |
| Lien | `logical_borrow_id` + `retry_of_group_key` |

---

## Confirm incrémental par step (R1 — bug racine)

### Problème actuel

Dans `usePortalLombardExecution`, le client accumule les steps réussies puis confirme en batch **en fin de boucle**. Sur revert `open_loan`, seul l’OVT en échec est confirmé ; l’approve exécuté on-chain **n’est pas persisté**.

### Comportement cible

```
Pour chaque step (approve, open_loan) :
  send tx
  wait receipt
  confirm backend immédiatement (success ou reverted)
  si reverted et steps précédentes OK → intent = retryable_failed
  si toutes success → intent = confirmed
```

**Sans R1**, les statuts `retryable_failed` et le stepper DB-driven sont **non fiables**.

---

## UX cible

| État UI | Copy / comportement | Actions |
|---------|---------------------|---------|
| **Processing** | Stepper driven by **DB steps** (OVT/intent), pas `lastProgressPhase` local | — |
| **Retryable failed** | « Autorisation validée · Emprunt non ouvert » | **Réessayer l’ouverture** · Fermer |
| **Retrying** | « Nouvelle tentative… » | — |
| **Success global** | 4 étapes cochées · recap emprunt | Voir mes emprunts |
| **Failed final** | « Échec définitif · Aucun emprunt ouvert » | Fermer · Support |
| **Reconciliation** | « Vérification en cours… » | Attendre / support |

### Règles stepper

- Cocher une étape **uniquement** si step backend = `confirmed` / OVT = `success`
- **Ne pas** cocher « Garantie déposée » tant que `open_loan` ≠ success
- En `retryable_failed` : approve coché si confirmé ; dépôt/emprunt **non** cochés

---

## Trace events à ajouter

| Event | Quand |
|-------|-------|
| `lombard.step_confirmed` | Step success confirmée backend |
| `lombard.open_loan_failed` | open_loan revert |
| `lombard.retryable_failed` | Transition vers retryable |
| `lombard.retry_started` | Utilisateur clique Réessayer |
| `lombard.retry_succeeded` | Retry open_loan OK |
| `lombard.retry_exhausted` | Retry KO → failed_final |

---

## Modèle cible — incident de référence

```text
logical_borrow_id = <uuid créé au prepare initial>

Intent ce0bf19a… :
  status = superseded
  terminal_outcome = borrow_not_opened
  superseded_by_group_key = f83658c9…

Intent f83658c9… :
  status = confirmed
  retry_of_group_key = ce0bf19a…
  retry_attempt_number = 1
  logical_borrow_id = <same>

Projection user-facing :
  terminal_status = confirmed
  winning_attempt = retry #1
```

---

## Plan d’implémentation

| Phase | Scope | Couche |
|-------|-------|--------|
| **R0** | Ce document (doctrine figée) | Doc |
| **R1** | Confirm incrémental par step | Web BFF (`usePortalLombardExecution`) |
| **R2** | Statuts intent : `retryable_failed`, `superseded`, `failed_final` dans `recompute_lombard_parent_status` + TTL | API |
| **R3** | `logical_borrow_id`, `retry_of_*` au prepare retry | Web + API |
| **R4** | UX écran retryable + stepper DB-driven | Web |
| **R5** | UX failed final après max retries | Web |
| **R6** | Projection historique merged (wallet / crédit line) | API + Web |
| **R7** | `reconciliation_required` sur timeout receipt | Web + API |

**Ordre impératif :** R1 avant R2–R4 (dépendance statuts fiables).

---

## Do not do

- **Pas d’auto-retry invisible** — chaque retry = consentement utilisateur (signature).
- **Pas de revoke allowance v1** — `approval_may_remain_on_chain` accepté.
- **Pas de repair prod** — intents `partial` historiques restent tels quels.
- **Pas de backfill historique** — pas de rétro-lien `ce0bf19a` ↔ `f83658c9` en prod sans runbook dédié.
- **Pas de migration** dans le cadre de cette spec.
- **Pas de modification PE Phase 3B** — hook inchangé ; s’applique uniquement sur open_loan success.

---

## Références

- Clôture forward 3B : [`TRANSACTION_ENGINE_PHASE3B_CLOSURE_STATUS.md`](./TRANSACTION_ENGINE_PHASE3B_CLOSURE_STATUS.md)
- Spec PE Lombard : [`INTERNAL_SCOPE_MOVEMENTS_PHASE3B_LOMBARD_SPEC.md`](./INTERNAL_SCOPE_MOVEMENTS_PHASE3B_LOMBARD_SPEC.md)
- Intents DeFi : [`TRANSACTION_INTENTS_DEFI.md`](./TRANSACTION_INTENTS_DEFI.md)
- Code UX actuel : `usePortalLombardExecution.ts`, `PortalLombardFlow.tsx`, `lombard_intent_sync.py`

---

## Synthèse doctrine

```
Toute tx utilisateur → état terminal explicite
Lombard multi-step   → même règle

approve OK + open_loan KO  →  retryable_failed (1 retry max)
retry OK                   →  confirmed (global), initial superseded
retry KO                   →  failed_final

Annulation métier ≠ rollback chain
approval_may_remain · borrow_not_opened · no PE

SoT : transaction_intents + logical_borrow_id
Semi-auto UX oui · retry blockchain invisible non

Bug racine : R1 confirm incrémental
```
