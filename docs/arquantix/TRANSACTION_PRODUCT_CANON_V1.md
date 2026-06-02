# Transaction Product Canon V1

**Date :** 2026-06-02  
**Statut :** canon produit validé — **R4.5-A.1**  
**Prérequis technique :** [`TRANSACTION_UX_FRAMEWORK_V1.md`](./TRANSACTION_UX_FRAMEWORK_V1.md) (doctrine & plan)  
**Bloque :** R4.5-B (extraction code) jusqu’à validation checklist §12  

**Objectif :** permettre à un **designer produit** et à un **développeur senior** d’implémenter la plateforme transactionnelle Vancelian **sans ambiguïté**, avant tout refactor.

**Hors périmètre :** code, refactor, push, backend PE, R5, repay Lombard.

---

## Executive summary

Vancelian doit passer de **flux métier isolés** (Swap UX, Vault UX, …) à une **plateforme transactionnelle** : quatre écrans canoniques, mêmes règles, mappers par produit.

| Écran canon | Rôle |
|-------------|------|
| **TransactionSetup** | Choix + simulation — **zéro** exécution, **zéro** Web3 |
| **TransactionReview** | Récap + risques — **seul** point d’entrée Privy obligatoire (session prête, pas de signature) |
| **TransactionProcessing** | Plein écran, stepper produit — signature, poll, retry invisible |
| **TransactionResult** | **Réussi** ou **Impossible** uniquement |

**Référence visuelle Result / Processing :** écrans Lombard R4 actuels (processing stepper FR, success, terminal failure).

**Gain perf/UX prioritaire (après canon) :** Privy monté sur **Review + Processing** uniquement — plus sur `wallet` / `vault` / `bundle` / `borrow` layouts entiers.

---

## 1. Matrice produit — aujourd’hui vs canon

| Produit | Setup | Review | Processing | Result | Écart canon |
|---------|-------|--------|------------|--------|-------------|
| **Lombard** | Oui (form + quote) | **Non** | Excellent | Excellent | Ajouter Review ; retirer Privy du Setup |
| **Swap** | Oui (wizard) | Partiel (confirm) | Moyen (dans confirm + overlay) | Moyen (overlay) | Séparer Review / Processing / Result ; supprimer checkbox |
| **Vault** | Oui (form unique) | Non | Faible (inline CTA) | Faible (message + hash) | Review + Processing plein écran + Result |
| **Bundle** | Popup / form | Preview | Faible (legs, dialog) | Faible (dialog) | Page Setup ; Review ; Processing plein écran |
| **Portfolio / DCP** | — | — | — | — | Appliquer canon dès V1 web |

---

## 2. Canon global — contenu obligatoire par écran

### 2.1 TransactionSetup

**Toujours présent (selon produit) :**

| Bloc | Obligatoire si… |
|------|-----------------|
| Montant | Tout produit avec saisie montant |
| Actif source | Swap, Vault deposit, Bundle invest, Lombard |
| Actif destination | Swap, Vault (parts vault), Bundle (allocation cible) |
| Simulation | Vault (rendement), Bundle (preview allocation), Lombard (capacity + quote) |
| Rendement / allocation / LTV | Vault APY, Bundle donut + poids, Lombard LTV + jauge |

**Interdictions absolues :**

- Aucune transaction on-chain déclenchée
- Aucune signature
- Aucun Privy, Wagmi, Viem
- 100 % API / BFF / DB
- Pas de popup comme conteneur principal du happy path (Bundle)
- Pas de spinner dans le CTA principal
- Pas de mention utilisateur : LI.FI, Privy, Morpho, Leg n/m, Batch, tx hash

**CTA Setup :** toujours **« Continuer »** ou **« Voir le récapitulatif »** — jamais « Confirmer », « Investir », « Emprunter », « Swapper ».

---

### 2.2 TransactionReview

**Toujours présent :**

| Bloc | Description |
|------|-------------|
| Récapitulatif | Montants, paires, garantie, allocation |
| Frais | Frais réseau / Vancelian (waived si applicable) |
| Rendement / impact | APY, LTV projeté, réception estimée |
| Allocation | Bundle : donut + liste cible ; Swap : receive estimate |
| Risques | Disclaimer court ou lien ; pas de mur de texte juridique sur mobile |

**CTA unique :** **« Confirmer »** (FR). Variante anglaise produit : **« Confirm »** si locale EN — une seule action primaire.

**Privy :** **première montée obligatoire** du boundary Web3 à l’entrée de cet écran (session wallet prête). **Pas de signature** sur Review — la signature démarre au passage Processing.

**Interdictions :** checkbox d’acknowledgment swap ; exécution ; overlay processing ; progress dans le bouton.

---

### 2.3 TransactionProcessing

**Layout :** **toujours plein écran** (page ou route dédiée). Pas popup, pas overlay, pas drawer.

**En-tête fixe :**

- Titre : **« Transaction en cours »**
- Sous-titre : rappel montant / produit (ex. « Votre échange de X USDC vers ETH… »)
- Mention : **« Ne fermez pas cette fenêtre. »** (ou équivalent mobile)

**Stepper :** 4 étapes produit maximum par défaut (extensions documentées par produit). États visuels : `done` | `current` | `pending` — pas de libellé technique.

**Interdictions copy UI :**

| Interdit | Remplacer par |
|----------|----------------|
| Approval pending | Autorisation (étape produit) |
| Confirming on-chain | Mise à jour / Finalisation |
| Leg 2/5 | Exécution des allocations (step 3 Bundle) |
| LI.FI, Privy, Morpho, Wagmi | *(aucune mention)* |
| Token approval, Sign swap, bridging | Étapes canon §3 |

**Retry :** invisible pour l’utilisateur si recoverable (pattern Lombard R4). Pas de bouton « Réessayer » pendant Processing sauf abandon explicite (secondaire, ghost).

**Privy :** obligatoire (signature + envoi tx).

**Fermeture :** icône fermer = abandon avec confirmation si tx engagée ; sinon retour hub produit.

---

### 2.4 TransactionResult

**Deux variantes uniquement :**

#### A. Réussi

- Icône succès
- Titre produit (ex. « Échange terminé », « Dépôt effectué », « Emprunt ouvert »)
- Montant / effet principal en gras
- Sous-texte rassurant (fonds visibles sous X secondes)
- CTA primaire : **« Voir mon portefeuille »** / **« Voir ma position »** / **« Voir mes prêts »** (selon produit)
- CTA secondaire : **« Fermer »**
- **Technical details** repliable en bas (hash, contrat, réseau) — jamais dans le titre ou le corps principal

#### B. Impossible

- Titre : **« Impossible de … »** (verbe produit)
- 2–3 lignes factuelles : ce qui **n’a pas** eu lieu (ex. Lombard R4 : aucun emprunt, garantie non déposée)
- Pas de `reverted`, pas de code erreur backend
- CTA primaire : **« Réessayer »** (relance Review → Processing si métier OK)
- CTA secondaire : **« Fermer »**

**Pas de troisième écran** « échec partiel » utilisateur — `reconciliation_required` = copy Impossible + mention support en Technical details (ops).

**Privy :** non requis. Facultatif si « Réessayer » nécessite re-session.

---

## 3. Mapping des étapes produit (Processing)

Étapes **exactes** affichées à l’utilisateur — mapping technique interne invisible.

### 3.1 Swap

| # | Label stepper (FR) | Sous-texte type | Phase technique mappée (interne) |
|---|-------------------|-----------------|----------------------------------|
| 1 | Préparation | Vérification de votre solde et de la route d’échange. | preparing, quote lock |
| 2 | Signature | Validation de l’opération sur votre wallet. | approving, signing |
| 3 | Échange | Conversion de vos actifs. | submitting |
| 4 | Réception | Crédit sur votre portefeuille. | bridging, poll confirm |

### 3.2 Vault (deposit & withdraw)

| # | Label (FR) | Deposit | Withdraw |
|---|------------|---------|----------|
| 1 | Préparation | Préparation du dépôt. | Préparation du retrait. |
| 2 | Autorisation | Autorisation d’utilisation de vos fonds. | Autorisation si requise. |
| 3 | Dépôt / Retrait | Dépôt vers le produit d’épargne. | Retrait vers votre wallet. |
| 4 | Mise à jour du portefeuille | Votre position est mise à jour. | Idem |

*Withdraw : si pas d’étape autorisation on-chain, step 2 reste « Autorisation » masquée en avance rapide (stepper saute visuellement à done) — implémentation B.*

### 3.3 Bundle (invest & withdraw)

| # | Label (FR) | Invest | Withdraw |
|---|------------|--------|----------|
| 1 | Préparation | Préparation de votre investissement. | Préparation du retrait. |
| 2 | Répartition du portefeuille | Structuration de l’allocation cible. | Déstructuration / ventes si besoin. |
| 3 | Exécution des allocations | Application des lignes d’allocation. | Libération des lignes. |
| 4 | Mise à jour du portefeuille | Votre panier est à jour. | Idem |

*Multi-leg LI.FI = sous le capot de l’étape 3 — jamais « Leg i/n ».*

### 3.4 Lombard borrow

| # | Label (FR) | Sous-texte (référence R4) |
|---|------------|---------------------------|
| 1 | Autorisation de la garantie | Utilisation du collateral comme garantie. |
| 2 | Dépôt de la garantie | Montant collateral déposé. |
| 3 | Ouverture de l’emprunt | Montant USDC + LTV ; rotation sous-textes autorisée (R4). |
| 4 | Réception des fonds | USDC sur wallet Vancelian. |

### 3.5 Portfolio / DCP (futur)

| # | Label (FR) | Note |
|---|------------|------|
| 1 | Préparation | Ordre / souscription |
| 2 | Validation | Conformité / limites |
| 3 | Exécution | Allocation PE |
| 4 | Mise à jour du portefeuille | Position DCP |

Détail allocation = Setup + Review ; Processing aligné Bundle.

---

## 4. Mapping Privy & Web3 boundaries

### 4.1 Par écran canon

| Écran | Privy | Wagmi | Viem | Boundary Next |
|-------|-------|-------|------|-----------------|
| **Setup** | Non | Non | Non | Aucun |
| **Review** | Oui (session) | Si wallet externe | Non UI | `PortalWeb3Boundary` à l’entrée |
| **Processing** | Oui (sign) | Si externe | Signer only | Même boundary (route enfant ou layout `(execute)`) |
| **Result** | Non* | Non | Non | Aucun |

\* Facultatif si CTA Réessayer sans re-navigation Review.

### 4.2 Architecture cible (layouts)

**Aujourd’hui (à supprimer progressivement — R4.5-F) :**

```text
wallet/layout  → Privy (toute la branche)
vault/layout   → Privy
bundle/layout  → Privy
borrow/layout  → Privy
```

**Cible :**

```text
…/swap/setup          → aucun SDK
…/swap/review         → PortalWeb3Boundary
…/swap/processing     → PortalWeb3Boundary
…/swap/result         → aucun SDK

…/borrow/setup        → aucun SDK
…/borrow/review       → PortalWeb3Boundary
…/borrow/processing   → PortalWeb3Boundary
…/borrow/result       → aucun SDK

(idem vault, bundle, futur dcp)
```

**Hubs lecture (jamais de boundary) :** `/app/wallet/crypto`, `/app/markets`, savings overview, bundle detail read-only, `/app/credit-line`, dashboard.

**Auth login/verify :** Privy hors canon transaction (inchangé).

### 4.3 Règle d’or

> **Privy is an execution dependency, not a navigation dependency.**

Montage = **Review + Processing** uniquement, pas le layout parent du portefeuille entier.

---

## 5. Mapping des CTA

### 5.1 Tableau global

| Écran | Primaire | Secondaire | Tertiaire / dismiss |
|-------|----------|------------|---------------------|
| **Setup** | Continuer / Voir le récapitulatif | Retour | Fermer (X) |
| **Review** | **Confirmer** | Retour (modifier montant) | Fermer |
| **Processing** | *(aucun primaire)* | — | Fermer (avec garde) |
| **Result — Réussi** | Voir portefeuille / position | Fermer | — |
| **Result — Impossible** | Réessayer | Fermer | — |

### 5.2 Par produit — libellés primaires Setup → Review

| Produit | Setup CTA | Review CTA | Result success CTA |
|---------|-----------|------------|-------------------|
| Swap | Continuer | Confirmer l’échange | Voir [actif destinataire] |
| Vault deposit | Continuer | Confirmer le dépôt | Voir mon épargne |
| Vault withdraw | Continuer | Confirmer le retrait | Voir mon épargne |
| Bundle invest | Continuer | Confirmer l’investissement | Voir mon panier |
| Bundle withdraw | Continuer | Confirmer le retrait | Voir mon panier |
| Lombard | Continuer | Confirmer l’emprunt | Voir mes prêts |
| DCP (futur) | Continuer | Confirmer la souscription | Voir mon portefeuille |

**Interdit sur Setup :** « Swap now », « Invest », « Emprunter maintenant », « Preview » comme action finale (Preview = action intermédiaire Bundle **dans** Setup, avant CTA Continuer vers Review).

### 5.3 Bundle — flux CTA canon

```text
Setup (montant + entry asset + donut preview)
  → CTA « Continuer »
Review (preview validée + allocation + warnings)
  → CTA « Confirmer l’investissement »
Processing
Result
```

« Preview » sur Setup = **recalcul** simulation, pas navigation finale.

---

## 6. Règles de copywriting

### 6.1 Langue & ton

- **UI transactionnelle :** français prioritaire (portail FR) ; anglais acceptable pour disclaimers réglementaires longs.
- Ton : **factuel, rassurant, court** — pas de jargon blockchain.
- Tutoiement / vouvoiement : aligné portail actuel (**vous** dans Lombard R4).

### 6.2 Mots interdits (UI principale)

`reverted` · `group_key` · `logical_borrow_id` · `retryable_failed` · `partial` · `intent` · `OVT` · `tx hash` · `0x…` · `LI.FI` · `Privy` · `Morpho` · `Wagmi` · `Leg` · `Batch` · `approve` · `open_loan` · `bridging` · `on-chain` (sauf Technical details)

### 6.3 Mots autorisés (exemples)

Transaction en cours · Impossible de [verbe] · Confirmer · Réussi · Réessayer · Garantie · Allocation · Niveau d’emprunt · Portefeuille · Panier · Épargne

### 6.4 Technical details (repliable)

**Titre bloc :** « Détails techniques »

**Contenu autorisé :** hash tronqué + copier, adresse contrat, chaîne (Base), identifiants support si copie ops, message reconciliation.

**Placement :** bas de Review (optionnel) et bas de Result — jamais au-dessus du CTA.

### 6.5 Messages d’erreur

- Une phrase **produit** + action (Réessayer / Fermer).
- Pas d’erreur brute API dans le corps principal.
- Quote expirée (Swap) : « Votre estimation a expiré. Modifiez le montant et consultez à nouveau le récapitulatif. »

### 6.6 Lombard — copy Result référence (ne pas changer en B)

**Impossible :**

- Titre : « Impossible d’ouvrir l’emprunt »
- Lignes : « Aucun montant n’a été emprunté. » · « Votre garantie n’a pas été déposée. »

**Processing titre :** « Transaction en cours »

---

## 7. Wireframes textuels — Desktop

Convention : `[ ]` champ · `( )` bouton · `{ }` zone optionnelle

### 7.1 Swap

**Setup (étape montant — après choix paires)**

```text
┌─────────────────────────────────────────────────────────────┐
│ [←] Échanger                                                │
├─────────────────────────────────────────────────────────────┤
│ Vous payez                          Solde · Max              │
│ [ 1 000,00___________ ]  [ USDC ▼ ]                          │
│ ─────────────────────────────────────────────────────────── │
│ Vous recevez                                                 │
│ [ 0,42______________ ]  [ ETH ▼ ]   (lecture seule estim.)   │
│                                                              │
│ { Quick fee hint: frais réseau couverts si applicable }      │
├─────────────────────────────────────────────────────────────┤
│                              [ Continuer ]                   │
└─────────────────────────────────────────────────────────────┘
```

**Review**

```text
┌─────────────────────────────────────────────────────────────┐
│ [←] Récapitulatif de l’échange                               │
├─────────────────────────────────────────────────────────────┤
│ Vous payez          1 000 USDC                               │
│ Vous recevez        ~0,42 ETH                                │
│ Frais               Couverts par Vancelian                   │
│ Délai estimé        < 2 min                                  │
│ { ▼ Détails techniques }                                     │
├─────────────────────────────────────────────────────────────┤
│ [ Retour ]                    [ Confirmer l’échange ]        │
└─────────────────────────────────────────────────────────────┘
```

**Processing** — stepper §3.1 · **Result Réussi** — titre + montant reçu + CTA portefeuille

---

### 7.2 Vault

**Setup**

```text
┌─────────────────────────────────────────────────────────────┐
│ [×] Investir — Vault USDC Morpho                             │
├─────────────────────────────────────────────────────────────┤
│ { Disclaimer première fois — bouton J’ai compris }           │
│ Je place                    Solde · Max                      │
│ [ 10 000___________ ]  [ USDC ]                              │
│ ─────────────────────────────────────────────────────────── │
│ Je reçois (parts vault)     10 000 USDC estimé               │
│                                                              │
│ Simulation                                                   │
│ [══════════○════] slider                                     │
│ + XX € / jour · mois · an                                    │
├─────────────────────────────────────────────────────────────┤
│                              [ Continuer ]                   │
└─────────────────────────────────────────────────────────────┘
```

**Review** — récap montant, APY cible, risques une ligne, Confirmer le dépôt  
**Processing** — §3.2  
**Result** — pas de hash dans le corps ; Détails techniques repliable

---

### 7.3 Bundle invest

**Setup (page pleine — plus de popup)**

```text
┌─────────────────────────────────────────────────────────────┐
│ [←] Investir — Panier Growth                                 │
├─────────────────────────────────────────────────────────────┤
│ Actif d’entrée [ USDC ▼ ]                                    │
│ Montant [ 5 000________ ]                                    │
│                                                              │
│ ┌──────────────────────┐  Allocation cible (preview API)    │
│ │      [ DONUT ]       │  · BTC 40%                         │
│ │                    │  · ETH 30%                         │
│ └──────────────────────┘  · USDC 30%                       │
│ [ Actualiser la simulation ]                                 │
├─────────────────────────────────────────────────────────────┤
│                              [ Continuer ]                   │
└─────────────────────────────────────────────────────────────┘
```

**Review** — preview warnings traduits, donut confirmé, Confirmer l’investissement  
**Processing** — §3.3 · **Result** — Voir mon panier

---

### 7.4 Lombard

**Setup** (form actuel sans CTA emprunt direct)

```text
┌─────────────────────────────────────────────────────────────┐
│ [←] Emprunter sur garantie crypto                            │
├─────────────────────────────────────────────────────────────┤
│ Garantie [ cbBTC ▼ ]    Solde · …                            │
│ Montant emprunt [ ______ ] USDC    LTV [====○===] 28%        │
│ Capacité · Devis · Jauge risque                              │
│ { pas de hint Privy ici en canon }                           │
├─────────────────────────────────────────────────────────────┤
│                              [ Continuer ]                   │
└─────────────────────────────────────────────────────────────┘
```

**Review** *(nouveau)*

```text
┌─────────────────────────────────────────────────────────────┐
│ Récapitulatif de l’emprunt                                   │
│ Emprunt · Garantie · LTV · Coût indicatif                    │
│ [ Retour ]                    [ Confirmer l’emprunt ]          │
└─────────────────────────────────────────────────────────────┘
```

**Processing / Result** — **inchangés** vs R4 (référence visuelle)

---

## 8. Wireframes textuels — Mobile

**Principes :** une colonne ; CTA primaire **sticky bottom** ; stepper vertical ; pas de popup plein flux.

### 8.1 Structure commune Processing mobile

```text
┌──────────────────────┐
│ [×]                  │
│ Transaction en cours │
│ Sous-titre montant   │
│ Ne fermez pas…       │
├──────────────────────┤
│ ● Autorisation…      │
│   sous-texte         │
│ ○ Dépôt…             │
│ ○ …                  │
│ ○ Réception…         │
└──────────────────────┘
```

### 8.2 Review mobile

- Récap en cartes empilées
- CTA **Confirmer** sticky
- Retour = lien secondaire sous le sticky

### 8.3 Result mobile

- Icône + titre centré
- CTA primaire sticky « Voir … »
- Technical details = accordéon bas de page

### 8.4 Swap mobile

- Setup : steps to/from/amount conservés **tant que** pas d’exec — fusion possible en une page Setup avec step indicator **produit** (1/3, 2/3) pas technique

### 8.5 Bundle mobile

- Donut + liste scrollable sous montant
- Review : donut simplifié + 3 lignes max warning

---

## 9. Parcours canon par produit (résumé implémentation)

| Produit | Routes indicatives | Setup | Review | Processing | Result |
|---------|-------------------|-------|--------|------------|--------|
| Swap | `…/swap/setup` → `review` → `processing` → `result` | Wizard ou page unique | Séparé de confirm actuel | Plein écran | 2 variantes |
| Vault | `…/vault/…/setup` → … | Form | Nouveau | Plein écran | Nouveau |
| Bundle | `…/bundle/…/setup` → … | Page + donut | Preview → Review | Plein écran | Page |
| Lombard | `…/borrow/setup` → … | Intro + form | **Nouveau** | R4 | R4 |
| DCP | `…/dcp/…` | À définir | Idem Bundle | 4 steps §3.5 | Idem |

---

## 10. Anti-patterns explicites (régression)

| # | Anti-pattern | Canon |
|---|--------------|-------|
| 1 | Exécuter depuis Setup | Confirmer uniquement sur Review |
| 2 | Privy sur layout wallet entier | Boundary Review/Processing |
| 3 | Processing dans overlay Swap | Route processing plein écran |
| 4 | Checkbox avant swap | Review seul |
| 5 | Hash tx dans message succès Vault | Technical details |
| 6 | Warning jaune disclaimer à chaque submit | Disclaimer Setup première fois |
| 7 | Bundle popup invest happy path | Page setup |
| 8 | « Leg 2/5 — ETH » | Étape 3 Bundle |
| 9 | Spinner + « Approval pending » dans CTA | Processing stepper |
| 10 | Troisième état UI « partial » | Impossible ou support via details |

---

## 11. Lien avec phases techniques

| Phase | Contenu | Prérequis |
|-------|---------|-----------|
| **R4.5-A** | Doctrine framework | Done |
| **R4.5-A.1** | **Ce canon** | Done à validation |
| **R4.5-B** | Extraction composants depuis Lombard | **A.1 validé** |
| **R4.5-C … F** | Migrations Swap, Vault, Bundle, layouts | B stable |

**Ne pas démarrer R4.5-B** tant que la checklist §12 n’est pas cochée — risque de figer les mauvais abstractions (ex. Review manquant Lombard, popup Bundle).

---

## 12. Checklist validation R4.5-A.1

- [x] Quatre écrans canon et interdictions validés produit
- [x] Étapes Processing §3 validées pour Swap, Vault, Bundle, Lombard
- [x] Privy Review+Processing only validé tech
- [x] CTA §5 validés
- [x] Copywriting §6 validé (legal si besoin)
- [x] Wireframes desktop/mobile §7–8 validés design
- [x] Lombard Review écran spécifié et accepté
- [x] Bundle page Setup (donut) accepté vs popup
- [x] Feu vert **R4.5-B** (2026-06-02)

---

## 13. Historique

| Date | Action |
|------|--------|
| 2026-06-02 | R4.5-A.1 — création Transaction Product Canon V1 |
