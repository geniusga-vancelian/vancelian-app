# Transaction UX Framework V1 — Doctrine & plan de migration

**Date :** 2026-06-02  
**Statut :** doctrine validée — **R4.5-A** · canon validé — **R4.5-A.1**  
**Périmètre :** portail web client (`services/arquantix/web`) — présentation des flux transactionnels on-chain  
**Hors périmètre :** Portfolio Engine, backend FastAPI, mutations infra, R5 / repay Lombard  

**Prérequis avant R4.5-B :** [`TRANSACTION_PRODUCT_CANON_V1.md`](./TRANSACTION_PRODUCT_CANON_V1.md) (R4.5-A.1 — canon produit : wireframes, étapes, CTA, copy, Privy).

**Références :**

- Audit front : conversation R4.5-A (2026-06-02) — flux, Privy boundaries, maturité par produit
- Moteur & intents : [`TRANSACTION_INTENTS_DEFI.md`](./TRANSACTION_INTENTS_DEFI.md)
- Lombard multi-step / terminal states : [`LOMBARD_MULTI_STEP_RETRY_TERMINAL_STATE_SPEC.md`](./LOMBARD_MULTI_STEP_RETRY_TERMINAL_STATE_SPEC.md)
- Performance Phase 1 (shell sans Web3) : [`PORTAL_PERFORMANCE_PHASE1_IMPLEMENTATION_REPORT.md`](./PORTAL_PERFORMANCE_PHASE1_IMPLEMENTATION_REPORT.md)

---

## Executive summary

Les fondations techniques **R1 → R4** (confirm incrémental, états terminaux, retry Lombard, processing UX) sont en place côté moteur et Lombard. Le gap restant est **produit** : chaque flux (Swap, Vault, Bundle, Lombard) a encore sa propre philosophie d’écrans et de chargement Web3.

**Objectif V1 :** un seul cycle pour tous les flux transactionnels Vancelian :

```text
Transaction Setup
      ↓
Transaction Review
      ↓
Transaction Processing
      ↓
Transaction Result   (Success ou Impossible)
```

**Plus jamais** de paradigmes parallèles nommés « Swap UX », « Vault UX », « Bundle UX », « Lombard UX ». Ces produits deviennent des **mappers** (étapes, copy, hooks d’exécution) branchés sur le même framework.

**Référence d’extraction :** Lombard R4 (~8,5/10 maturité UX) — processing, succès, échec terminal et retry invisible. Le framework **sort de Lombard** en R4.5-B ; les autres flux migrent ensuite.

**Règle stratégique :** *Privy is an execution dependency, not a navigation dependency.*

---

## 1. Doctrine UX

### 1.1 Cycle unique

| Phase | Rôle utilisateur | Exécution on-chain | SDK Web3 |
|-------|------------------|--------------------|----------|
| **Setup** | Choisir montant, actif, destination, paramètres ; lire soldes ; simulation / preview API | **Interdit** | **Interdit** (lecture-only) |
| **Review** | Récap final ; frais / rendement / LTV / impact ; un CTA « Confirmer » | **Interdit** (pas encore de signature) | **Autorisé** (session wallet prête) |
| **Processing** | Voir des **étapes produit** lisibles ; retry invisible si recoverable | **Obligatoire** | **Obligatoire** |
| **Result** | **Réussie** ou **Impossible** (terminal) ; retry explicite seulement si métier le permet | Terminé | **Facultatif** (retry / resign) |

### 1.2 Règles produit (non négociables)

1. **Aucun flux ne s’exécute dans son écran Setup.**
2. **Aucun écran Setup read-only ne charge Privy, Wagmi ou Viem.**
3. **Privy = dépendance d’exécution, pas de navigation** — Markets, Wallet, Savings, Bundles (lecture), Portfolio, Credit Line restent sans SDK Web3.
4. L’utilisateur **ne voit jamais** :
   - `tx reverted`
   - `group_key`
   - `logical_borrow_id`
   - `retryable_failed`
   - hash de transaction brut (sauf panneau **Technical details** repliable)
5. **Trois vues client** pour une transaction engagée :
   - **En cours** (Processing)
   - **Réussie** (Result success)
   - **Impossible** (Result terminal failure — pas d’effet métier attendu, copy claire)

### 1.3 Ce qui disparaît au fil des migrations

| Anti-pattern actuel | Remplacement cible |
|---------------------|-------------------|
| Exécution inline sur le formulaire Vault | Setup → Review → Processing → Result |
| Confirm + processing + overlay Swap sur le même écran | Review séparé ; Processing dédié ; Result dédié |
| Popup Bundle → legs → popup success | Page (ou route) Setup/Review ; Processing multi-leg générique |
| Checkbox d’acknowledgment swap inutile | Review + CTA unique |
| Phases EN « Approval pending », « Confirming on-chain » dans le CTA | Libellés produit FR via `TransactionStep[]` |
| Warning jaune / hash tx dans le message de succès Vault | Result screen + Technical details |

### 1.4 Nommage

| Ancien vocabulaire | Vocabulaire V1 |
|--------------------|----------------|
| R4.5 « UX polish » | **Transaction UX Framework V1** |
| Flow Lombard / Swap / … | **Produit** + mapper sur le framework |
| `SwapExecutionPhase` exposé tel quel | Mappé vers `TransactionStatus` + steps produit |

---

## 2. Doctrine Privy & Web3 boundaries

### 2.1 Par phase transactionnelle

| Phase | Privy | Wagmi | Viem |
|-------|-------|-------|------|
| **Lecture** (navigation portefeuille) | Non | Non | Non |
| **Setup** | Non (idéal) | Non | Non |
| **Review** | Autorisé — **pas de signature** | Si sélection wallet externe | Non en UI |
| **Processing** | Obligatoire | Si externe | Via signer / RPC (exécution) |
| **Result** | Facultatif | Facultatif | Non |

### 2.2 Par type d’écran portail (hors transaction)

| Écran | Web3 |
|-------|------|
| Dashboard, Markets, Academy, Invest hub, Profile (hors connect externe) | Non |
| Wallet crypto, détail actif, historiques, Savings (lecture) | **Ne doit pas** charger Web3 (état actuel : layout `wallet` — à corriger en R4.5-F) |
| Credit Line (hub prêts) | Non |
| Login / Verify | Privy (auth — hors framework transaction) |
| Swap, Borrow, Vault invest page, Bundle invest page | Web3 **à partir de Review** (cible) ; aujourd’hui souvent au layout (écart) |

### 2.3 Montage actuel vs cible (audit 2026-06-02)

**Aujourd’hui — `PortalWeb3Boundary` eager dans :**

- `app/app/(shell)/wallet/layout.tsx`
- `app/app/(shell)/wallets/layout.tsx`
- `app/app/(shell)/borrow/layout.tsx`
- `app/app/(shell)/invest/vault/layout.tsx`
- `app/app/(shell)/invest/bundle/layout.tsx`

**Déjà conforme (lazy à l’ouverture) :**

- `PortalLazyBundleInvestDialog`, `PortalLazyEarnVaultModal`, `PortalLazyLedgityVaultModal`
- `PortalProfileExternalWalletConnect` → `PortalWeb3BoundaryLazy`

**Cible R4.5-F :** route groups `(read)` / `(execute)` ou segments `/review` — boundary Web3 uniquement sur branches exécution ; conserver `PortalWeb3BoundaryLazy` pour modales depuis hubs read-only.

### 2.4 Chaîne technique de signature (inchangée en V1)

Tous les produits continuent de passer par :

- `usePortalTxSigner` / `usePrivyLiveSession` (LI.FI, vault, Lombard)
- BFF prepare / confirm / poll (pas de logique métier dupliquée dans le framework UI)

Le framework **orchestre l’affichage et les phases** ; il ne remplace pas le moteur d’intents ni PE.

---

## 3. Tableau des flux — état actuel (audit)

Légende maturité : note /10 vs doctrine V1. **Écart principal** = distance au cycle Setup → Review → Processing → Result + Privy tardif.

| Produit | Route(s) actuelle(s) | Composants principaux | Setup exec ? | Privy dès setup ? | Review dédié ? | Processing | Result | Maturité |
|---------|----------------------|------------------------|--------------|-------------------|----------------|------------|--------|----------|
| **LI.FI Swap** | `/app/wallet/swap` | `PortalSwapFlow`, steps to/from/amount/confirm, `PortalSwapProcessingOverlay` | Non (confirm séparé) | Oui (layout wallet) | Partiel (confirm = review) | Dans confirm + overlay | Overlay | **6** |
| **Vault Morpho** | `/app/invest/vault/morpho/[address]`, modale lazy, savings panel | `PortalDefiVaultInvestFlow`, `PortalEarnVaultModal` | **Oui** (inline) | Page: layout vault ; modale: lazy | Non | Inline phases EN | Message + **tx hash** | **4** |
| **Vault Ledgity** | `/app/invest/vault/ledgity/[id]`, modale lazy, savings panel | Idem Ledgity execution hook | **Oui** | Idem | Non | Inline | Idem | **4** |
| **Vault withdraw** | `?mode=withdraw` | Même flow | **Oui** | Idem | Non | Inline | Idem | **4** |
| **Bundle invest** | Modale markets/invest ; page `/app/invest/bundle/[id]` | `PortalBundleInvestDialog`, `useBundleLifiInvest` | Non | Page: **oui** ; modale: lazy | `preview` | `executing` + legs | `done`/`error` dans dialog | **3** |
| **Bundle withdraw** | `/app/invest/bundle/[id]?mode=withdraw` | `PortalBundleWithdrawDialog` | Non | Layout bundle | `confirm` | `executing` | dialog | **3** |
| **Lombard borrow** | `/app/borrow` | `PortalLombardFlow`, `lombardProcessingUx` | Non | Oui (layout + `usePrivy` form) | **Non** (form → processing) | **Excellent** R4 | Success / TerminalFailure | **8,5** |
| **Credit Line** | `/app/credit-line` | Lecture positions | — | Non | — | — | — | N/A (hub) |
| **Portfolio / DCP web** | — | Non implémenté | — | — | — | — | — | — |
| **Invest offre CMS** | `/app/invest/[slug]/invest` | `PortalInvestFlow` simulation | Non | Non | N/A | N/A | N/A | Hors on-chain |

---

## 4. Flux cible par produit

Chaque produit expose un mapper `TransactionStep[]` et mappe les phases internes vers `TransactionStatus`.

### 4.1 Swap (LI.FI)

| Phase | Contenu |
|-------|---------|
| **Setup** | Choix paire, montant, quote API (`to` / `from` / `amount`) |
| **Review** | Récap pay/receive, frais, délai estimé ; CTA « Confirmer l’échange » |
| **Processing** | Préparation → Signature → Échange → Réception (pas « Token approval » / « bridging » en UI) |
| **Result** | Success : montant reçu ; Impossible : message produit, pas de jargon Li.FI |

### 4.2 Vault deposit / withdraw (Morpho & Ledgity)

| Phase | Contenu |
|-------|---------|
| **Setup** | Montant, source, simulation rendement, disclaimer (1ère fois) |
| **Review** | Montant, APY cible, risques résumés, frais Vancelian |
| **Processing** | Préparation → Autorisation (si requise) → Dépôt ou retrait → Mise à jour position |
| **Result** | Success écran dédié ; Impossible terminal ; hash uniquement en Technical details |

### 4.3 Bundle invest / withdraw

| Phase | Contenu |
|-------|---------|
| **Setup** | Montant, actif d’entrée ; **page** avec allocation cible + donut (plus de popup flow) |
| **Review** | Preview API, warnings métier traduits, récap allocation |
| **Processing** | Transfert interne → allocations (legs génériques, pas « Leg 2/5 ») → Portefeuille mis à jour |
| **Result** | Success / Impossible / reconciliation si applicable ; reprise session = entrée Processing, pas Setup |

### 4.4 Lombard borrow

| Phase | Contenu |
|-------|---------|
| **Setup** | Intro (optionnel), form : collateral, LTV, montant, capacity/quote API |
| **Review** | **À ajouter** — récap emprunt, garantie, LTV, frais ; CTA unique |
| **Processing** | Réutiliser `LOMBARD_PROCESSING_STEPS` via framework (autorisation → dépôt garantie → ouverture → réception) |
| **Result** | `PortalLombardBorrowSuccess` / terminal failure — comportement R4 inchangé |

### 4.5 Futur portfolio / DCP

Même cycle dès l’implémentation web ; Setup/Review sans Web3 ; Processing selon orchestration PE (hors spec V1).

---

## 5. Composants & types cibles (R4.5-B+)

Emplacement indicatif : `services/arquantix/web/src/components/portal/transaction/`

### 5.1 Composants UI

| Composant | Responsabilité |
|-----------|----------------|
| **`TransactionSetupShell`** | Layout setup (optionnel — souvent pages produit existantes refactorées) |
| **`TransactionReviewPage`** | Récap, impact, CTA confirmer ; monté sous boundary Web3 **à l’entrée Review** |
| **`TransactionProcessingPage`** | Stepper produit, sous-textes, rotation copy (pattern Lombard R4) |
| **`TransactionResultPage`** | Variantes `success` \| `impossible` \| `reconciliation_required` (copy + actions) |
| **`TransactionStepList`** | Rendu liste / stepper à partir de `TransactionStep[]` |
| **`TransactionTechnicalDetails`** | Panneau repliable : hash, contrat, réseau, ids internes **masqués du flux principal** |

### 5.2 Types

```ts
/** Étape affichée à l'utilisateur — jamais un statut backend brut. */
type TransactionStep = {
  id: string
  label: string
  defaultSubtext: string | ((ctx: unknown) => string)
}

/** Machine UI — distincte des statuts intent/OVT backend. */
type TransactionStatus =
  | 'idle'
  | 'reviewing'
  | 'signing'      // sous-phase processing, pas un écran séparé obligatoire
  | 'processing'
  | 'success'
  | 'impossible'
  | 'reconciliation_required'

/** Mapper produit : phase interne → index stepper + status UI */
type TransactionStepMapper<TPhase extends string> = {
  steps: TransactionStep[]
  stepIndex: (phase: TPhase) => number
  status: (phase: TPhase) => TransactionStatus
}
```

### 5.3 Hook d’orchestration (optionnel V1, recommandé)

**`useTransactionExecution()`** — façade au-dessus des hooks existants (`usePortalLombardExecution`, `useLifiSwapExecution`, `usePortalMorphoVaultExecution`, …) :

1. `prepare` (BFF)
2. boucle sign (`usePortalTxSigner`)
3. `confirm` incrémental (leçon R1/R4 Lombard)
4. poll / terminal
5. callbacks `onPhaseChange`, `onInvisibleRetry`

Le framework V1 **ne duplique pas** la logique métier ; il **uniformise** les transitions UI et les copy.

### 5.4 Extraction depuis Lombard (R4.5-B)

Sources à généraliser sans changer le comportement Lombard :

| Existant | Devient |
|----------|---------|
| `lombardProcessingUx.ts` — `LOMBARD_PROCESSING_STEPS`, stepper index | `TransactionStepList` + mapper `lombardSteps.ts` |
| `PortalLombardBorrowProcessing` | `TransactionProcessingPage` |
| `PortalLombardBorrowSuccess` | `TransactionResultPage` variant success |
| `PortalLombardBorrowTerminalFailure` | `TransactionResultPage` variant impossible |
| `DefiInvestTech` / `PortalSwapTechDetails` | `TransactionTechnicalDetails` unifié |

**Manque Lombard pour doctrine complète :** `TransactionReviewPage` (nouveau) ; retirer `usePrivy` du form Setup (Privy au passage Review).

---

## 6. Plan de migration

| Phase | Intitulé | Livrable | Prérequis |
|-------|----------|----------|-----------|
| **R4.5-A** | Doctrine & doc | **Ce document** | — |
| **R4.5-A.1** | Transaction Product Canon | [`TRANSACTION_PRODUCT_CANON_V1.md`](./TRANSACTION_PRODUCT_CANON_V1.md) — wireframes, étapes, CTA, copy, Privy Review+Processing | A validé |
| **R4.5-B** | Extract framework depuis Lombard | `TransactionProcessingPage`, `TransactionResultPage`, `TransactionStepList`, `TransactionTechnicalDetails`, `TransactionReviewPage` ; Lombard aligné canon A.1 | **A.1 validé** |
| **R4.5-C** | Migrate Swap | Setup → Review → Processing → Result ; supprimer checkbox ; masquer jargon ; Privy au Processing | B stable |
| **R4.5-D** | Migrate Vault | Review + Processing + Result ; supprimer warning jaune, hash visible, exec inline | B stable |
| **R4.5-E** | Migrate Bundle | Page setup/review (donut + allocation) ; Processing multi-leg générique ; fin popup flow | B stable, C/D patterns éprouvés |
| **R4.5-F** | Cleanup Privy layouts | Scinder layouts `wallet` / `borrow` / `vault` / `bundle` : routes read vs execute ; aligner `portalPerformanceGuard` | C/D/E ou en parallèle partiel |

### 6.1 Ordre et justification

1. **Lombard d’abord (B)** — référence UX la plus mature ; valide le framework avant ROI Swap/Vault.
2. **Swap (C)** — ROI rapide, trafic élevé, dette UX visible (checkbox, overlay, jargon).
3. **Vault (D)** — ROI rapide, dette la plus visible (inline, hash).
4. **Bundle (E)** — complexité maximale (multi-leg, locks, resume).
5. **Layouts Privy (F)** — impact perf navigation ; peut commencer tôt sur routes read-only wallet si validé.

### 6.2 Critères de done par phase

| Phase | Done when |
|-------|-----------|
| B | Lombard parcours identique en QA ; composants génériques utilisés ; tests existants Lombard verts |
| C | Swap : pas d’exec sur setup ; pas de Privy sur steps to/from/amount ; 3 vues client claires |
| D | Vault : pas de hash dans success principal ; pas d’exec sur form pane |
| E | Bundle : pas de dialog popup pour le happy path invest ; legs en steps produit |
| F | `/app/wallet/crypto` First Load sans chunks Privy documentés Phase 0 bis |

---

## 7. Do / Do not

### 7.1 Do

- Traiter chaque nouveau produit on-chain comme un **mapper** du framework V1.
- Réutiliser confirm incrémental et terminal states backend (R1–R4).
- Garder `portalPerformanceGuard` et étendre les chemins read-only.
- Documenter les écarts dans ce fichier avant chaque phase B–F.

### 7.2 Do not (R4.5-A → jusqu’à validation explicite)

- **Pas de refactor code** pendant R4.5-A.
- **Pas de migration** de flux pendant R4.5-A.
- **Pas de push** sans validation produit / tech.
- **Pas de R5**, repay Lombard, ni changement PE/backend dans le cadre UX Framework V1.
- **Pas de généralisation** du code R4 Lombard hors extraction B.

---

## 8. Fondations R1 → R4 (rappel)

| Release | Apport pour le framework UI |
|---------|----------------------------|
| **R1** | Confirm incrémental par step — évite stepper mensonger après revert partiel |
| **R2+** | Intents, statuts terminaux backend alignés Swap/Vault/Bundle/Lombard |
| **R3** | Lombard forward / PE — hors UI mais contraint les messages « Impossible » |
| **R4** | `lombardProcessingUx`, retry invisible, terminal failure copy — **source d’extraction B** |

Le framework V1 est la **couche présentation** au-dessus de ce moteur ; il ne le remplace pas.

---

## 9. Checklist validation

### R4.5-A (framework doctrine)

- [x] Doctrine cycle Setup → Review → Processing → Result validée produit
- [x] Doctrine Privy par phase validée
- [x] Ordre migration A.1 → B → C/D/E → F validé (F après migrations flux)

### R4.5-A.1 (product canon)

Voir checklist complète : [`TRANSACTION_PRODUCT_CANON_V1.md` §12](./TRANSACTION_PRODUCT_CANON_V1.md#12-checklist-validation-r45-a1).

- [x] Canon produit validé (design + produit + tech)
- [x] Feu vert R4.5-B (2026-06-02)

---

## 10. Historique

| Date | Action |
|------|--------|
| 2026-06-02 | R4.5-A — création doc, audit front consolidé, doctrine figée |
| 2026-06-02 | R4.5-A.1 — référence Transaction Product Canon ; B bloqué jusqu’à validation A.1 |
| 2026-06-02 | R4.5-B — extraction composants `transaction/` depuis Lombard (zéro changement visuel) |
| 2026-06-02 | R4.5-C — migration Swap LI.FI vers framework (review / processing / result) |
