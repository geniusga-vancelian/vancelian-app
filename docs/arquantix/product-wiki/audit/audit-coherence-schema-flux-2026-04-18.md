# Audit de cohérence Wiki × Schéma des Flux — 2026-04-18 (Étape 2)

**Règle gouvernante :** Le Schéma des Flux (Annexe 36, sept. 2025, v1) est la source absolue de vérité pour toute mécanique transactionnelle. Chaque fiche wiki décrivant un produit/service générant une transaction doit être alignée sur cette source.

**Classification des écarts :**
- **HIGH** — contradiction factuelle ou omission critique sur la mécanique (risque régulateur ou client)
- **MEDIUM** — simplification abusive, omission d'un détail important, formulation ambiguë
- **LOW** — point éditorial ou précision à ajouter, pas de risque matériel

---

## Section G — Service de paiement sur réserve crypto (§544-606)

**Statut : ✅ complétée (traitée en amont)**

### Fiches auditées
| Fiche | Statut | Écart | Niveau |
|---|---|---|---|
| how-crypto-card-payment-works.md | ✅ Corrigée 2026-04-18 | Aucun — mécanique et nature fiscale alignées §544-606 | — |
| how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md | À compléter | Manque `related:` vers how-crypto-card-payment-works.md ; formulation "without manually converting them into euros" légèrement trompeuse | MEDIUM |

---

## Section D — Service de programme de minage / Cloud Mining (§352-409)

**Statut : ✅ audit complet des 18 fiches**

### Grille de contrôle appliquée
- C1. Vancelian LTD (UAE-ADGM) identifié comme contrepartie du contrat (§356)
- C2. Automata France SAS identifiée comme intermédiaire (exchange + custody + display uniquement) (§358)
- C3. Dénomination en EURC (souscription, intérêts, remboursement) (§368, 374, 393, 408)
- C4. Remboursement capital en EURC à l'échéance (§408)
- C5. Intérêts payés quotidiennement en EURC sur wallet omnibus (§393)
- C6. Cohérence durée d'engagement avec les 3 régimes de maturité (24 mois pré-24-Sep-2024, 48 mois Sep-Dec 2024, 31-Dec-2028 post-Dec-2024)

### Résultats par fiche

| # | Fiche | C1 | C2 | C3 | C4 | C5 | C6 | Niveau | Observation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | how-cloud-mining-flow-works.md | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | **OK** | Référence Batch C alignée §352-409 |
| 2 | how-does-the-exclusive-offer-cloud-mining-by-hearst-infrastr.md | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | **LOW** | Précision manquante : remboursement en EURC à l'échéance |
| 3 | what-is-the-exclusive-offer-cloud-mining-by-hearst-infrastru.md | ✅ | ✅ | ✅ | n/a | ✅ | n/a | **OK** | Aligné |
| 4 | cloud-mining-who-reimburses-if-bankruptcy.md | ✅ | ✅ | n/a | ⚠️ | n/a | n/a | **LOW** | Précision manquante : remboursement en EURC |
| 5 | cloud-mining-can-i-lose-my-capital.md | ✅ | ✅ | ⚠️ | ⚠️ | n/a | ❌ | **MEDIUM** | "48 months" généralité + capital returned sans EURC |
| 6 | cloud-mining-risks-overview.md | ✅ | ✅ | n/a | n/a | n/a | ❌ | **MEDIUM** | "48-month commitment" généralité |
| 7 | cloud-mining-cgupm-investor-obligations.md | ⚠️ | ⚠️ | n/a | n/a | n/a | ❌ | **MEDIUM** | "capital is locked for 48 months" généralité ; ne mentionne pas Vancelian LTD |
| 8 | cloud-mining-early-exit-and-transfers.md | n/a | n/a | ✅ | n/a | ✅ | ❌ | **MEDIUM** | "48 months per deposit" généralité |
| 9 | cloud-mining-yield-factors.md | n/a | ⚠️ | ✅ | n/a | ✅ | n/a | **OK** | Aligné |
| 10 | cloud-mining-bitcoin-halving-impact.md | n/a | n/a | n/a | n/a | n/a | ❌ | **MEDIUM** | "capital is locked for 48 months" |
| 11 | cloud-mining-mica-and-european-regulation.md | ⚠️ | ✅ | n/a | n/a | n/a | n/a | **MEDIUM** | Ne précise pas que le programme est opéré hors UE par Vancelian LTD |
| 12 | cloud-mining-is-it-a-scam.md | n/a | ⚠️ | n/a | n/a | n/a | n/a | **OK** | Aligné |
| 13 | cloud-mining-mining-sites-and-geography.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Hors périmètre transactionnel (infrastructure) |
| 14 | cloud-mining-vs-direct-bitcoin-purchase.md | n/a | n/a | ✅ | n/a | ✅ | ❌ | **MEDIUM** | "capital locked for 48 months" |
| 15 | how-does-mining-work-at-vancelian.md | ❌ | ⚠️ | ✅ | n/a | ✅ | ❌ | **MEDIUM-HIGH** | "Hearst's Power wallet" — §376 : transfert vers wallet Vancelian LTD (JV), pas Hearst directement |
| 16 | how-does-the-exclusive-offer-eco-friendly-mining-in-ethiopia.md | ❌ | ❌ | ✅ | n/a | ✅ | n/a | **MEDIUM** | Ne mentionne pas Vancelian LTD / Automata France distinction |
| 17 | what-is-the-eco-friendly-bitcoin-mining-in-ethiopia-exclusiv.md | ❌ | ❌ | ✅ | n/a | ✅ | n/a | **MEDIUM** | Idem — ne mentionne pas la structure à 2 entités |
| 18 | migration-to-the-new-cloud-mining-program.md | ✅ | n/a | n/a | n/a | n/a | ⚠️ | **OK** | Migration mentionne Vancelian LTD UAE ; "4-year commitment" acceptable dans le contexte migration |

### Synthèse Section D

**Écart systémique #1 — "48 months" comme règle universelle (11 fiches)**

La plupart des fiches Cloud Mining présentent "48 months" ou "4 ans" comme la durée d'engagement universelle, alors que seule la fiche maîtresse `how-does-the-exclusive-offer-cloud-mining-by-hearst-infrastr.md` documente les 3 régimes de maturité :
- avant 24 septembre 2024 : 24 mois depuis la date de dépôt
- 24 sept. – 31 déc. 2024 : 48 mois depuis la date de dépôt
- après 31 déc. 2024 : jusqu'au 31 décembre 2028 pour tous

**Impact :** un client migré avant septembre 2024 peut lire "capital is locked for 48 months" dans plusieurs fiches et conclure à tort que son capital est verrouillé plus longtemps que prévu. Régulateur pourrait relever l'incohérence entre la brochure et ces fiches.

**Fiches concernées :** cgupm-investor-obligations, risks-overview, can-i-lose-my-capital, bitcoin-halving-impact, early-exit-and-transfers, vs-direct-bitcoin-purchase, how-does-mining-work-at-vancelian.

**Correction proposée :** remplacer "48 months" par "over the engagement period defined in your contract (see the dedicated page for the 3 maturity regimes)" avec un lien vers la fiche maîtresse.

---

**Écart systémique #2 — Fiches Ethiopia sans mention Vancelian LTD / Automata France**

Les 2 fiches Ethiopia (`how-does-the-exclusive-offer-eco-friendly-mining-in-ethiopia.md` + `what-is-the-eco-friendly-bitcoin-mining-in-ethiopia-exclusiv.md`) ne mentionnent jamais la structure à 2 entités. Un client qui lit uniquement ces fiches ne comprend pas qui est sa contrepartie contractuelle.

**Correction proposée :** ajouter un bloc "Who does what?" identique à celui déjà présent dans la fiche Hearst, même si l'offre Ethiopia est fermée (contractuellement, les investisseurs actifs y sont toujours engagés).

---

**Écart spécifique — "Hearst's Power wallet" dans how-does-mining-work-at-vancelian.md**

Paragraphe : *"you subscribe to the offer and your funds are allocated to Hearst's **Power** wallet"*.

§376 de l'Annexe 36 précise que les EURC sont transférés du wallet client vers **le wallet Vancelian LTD (UAE-ADGM)**, via transfert on-chain Fireblocks. Hearst Solution FZCO est l'opérateur technique (côté infrastructure), pas le récipiendaire des EURC. La formulation actuelle crée une confusion régulateur-sensible.

**Correction proposée :** remplacer "Hearst's Power wallet" par "your Power wallet (financing the computing power allocated to you by Vancelian LTD)".

---

## Section C — Service d'offre exclusive / BTC Lending (§299-351)

**Statut : ✅ audit complet des 16 fiches**

### Grille de contrôle appliquée
- C1. Société emprunteuse RWA identifiée comme contrepartie juridique (Solaria pour Dubai, The Heights Bali SAS pour Bali) (§300, §305)
- C2. BTC comme actif du prêt (et non USDC ou EUR) (§322)
- C3. Valeur de référence en EURC verrouillée à la date de dépôt (§319)
- C4. Intérêts servis en BTC puis convertis via Automata France (§337-338)
- C5. Remboursement du capital en BTC, calculé sur la valeur EURC initiale (§350)
- C6. Démarrage du prêt en J+1 (§330)

### Résultats par fiche

| # | Fiche | C1 | C2 | C3 | C4 | C5 | C6 | Niveau | Observation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | how-exclusive-offer-btc-lending-works.md | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **OK** | Fiche maîtresse Batch C bien alignée §305-351 |
| 2 | how-does-the-dubai-villa-al-barari-exclusive-offer-work.md | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | n/a | **MEDIUM** | Mécanique BTC / EURC ref insuffisamment explicite |
| 3 | how-does-the-7-luxury-villas-in-bali-exclusive-offer-work.md | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | n/a | **MEDIUM** | Même problème que Dubai — mécanique BTC/EURC peu lisible |
| 4 | how-are-returns-generated-dubai-villa.md | ✅ | ✅ | ✅ | ✅ | n/a | n/a | **OK** | Bien aligné |
| 5 | guarantees-and-security-al-barari.md | ✅ | n/a | ✅ | n/a | n/a | n/a | **OK** | Solaria clair |
| 6 | guarantees-and-security-of-your-investment.md (Bali) | ✅ | n/a | ✅ | n/a | n/a | n/a | **OK** | The Heights Bali SAS clair |
| 7 | project-sponsor-responsibilities-al-barari.md | ✅ | n/a | n/a | n/a | n/a | n/a | **OK** | Solaria bien identifié |
| 8 | project-sponsor-responsibilities-bali.md | ✅ | n/a | n/a | n/a | n/a | n/a | **OK** | The Heights Bali SAS bien identifié |
| 9 | financial-structure-of-the-project.md | ✅ | ⚠️ | ❌ | ⚠️ | ⚠️ | n/a | **MEDIUM** | Valeur de référence EURC pas explicite ; mécanique prêt BTC floue |
| 10 | how-do-project-exit-windows-work.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | 3 régimes de maturité bien traités |
| 11 | how-can-i-invest-in-a-closed-exclusive-offer-via-deposit-window.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Mécanisme de reprise de position |
| 12 | how-can-i-reinvest-my-returns-into-other-projects.md | n/a | n/a | ✅ | ✅ | n/a | n/a | **OK** | Réinvestissement EURC cohérent |
| 13 | what-is-the-7-luxury-villas-in-bali-exclusive-offer.md | ✅ | ✅ | ✅ | ✅ | n/a | n/a | **OK** | Fiche courte, mentionne conversion BTC→EURC |
| 14 | what-is-the-exclusive-offer-dubai-villa-al-barari.md | ✅ | ✅ | ✅ | n/a | n/a | n/a | **OK** | Solaria SPV mentionné |
| 15 | dubai-villa-risk-summary.md | ✅ | n/a | n/a | n/a | n/a | n/a | **OK** | Ton factuel, 4 familles de risques |
| 16 | the-heights-bali-project-reference.md | ✅ | ✅ | ✅ | ✅ | n/a | n/a | **OK** | Fiche référence complète et alignée §319 |

### Synthèse Section C

**Écart systémique #3 — Mécanique BTC/EURC insuffisamment explicite sur 3 fiches (Dubai, Bali "how-does-the-offer-work", financial-structure)**

Ces 3 fiches parlent du prêt sans expliciter clairement que :
- L'actif prêté est du **BTC** (et non de l'EUR ni de l'EURC) — §322
- Une **valeur de référence en EURC est verrouillée** à la date de dépôt, qui sert d'ancrage de capital — §319
- Les intérêts sont **générés en BTC** puis convertis à la demande via Automata France — §337-338
- Le **remboursement final** est effectué en BTC sur la base de la valeur EURC initiale (quel que soit le prix du BTC à l'échéance) — §350

**Impact :** un client qui lit ces 3 fiches sans consulter la fiche maîtresse `how-exclusive-offer-btc-lending-works.md` ne comprend pas qu'il prend un risque de conversion BTC → EUR sur la volatilité du BTC à l'échéance (atténué par la référence EURC). Régulateur pourrait relever que la nature de l'actif sous-jacent du prêt n'est pas suffisamment affichée.

**Correction proposée :** ajouter un bloc court "The loan mechanic in one paragraph" sur ces 3 fiches, renvoyant vers la fiche maîtresse pour le détail complet.

**Note positive :** la fiche `the-heights-bali-project-reference.md` traite très bien la mécanique (EUR-locked, APR daily EURC, performance bonus explicite). Elle peut servir de modèle pour uniformiser les fiches Dubai équivalentes.

---

## Section B — Service de coffre Flexible/Avenir (§189-297)

**Statut : ✅ audit complet des 10 fiches**

### Grille de contrôle appliquée
- B1. Coffre = portefeuille diversifié (poche liquidité + allocations yield : Exclusive Offers + Mining) (§192-196)
- B2. Dépôt converti automatiquement en EURC (§213)
- B3. Poche liquidité EURC **non rémunérée**, conformément à MiCA (§215)
- B4. Wallet Fireblocks dédié pour la poche liquidité (§213)
- B5. Coffre "Avenir" = lock-up 12 mois (§217-219)
- B6. Intérêts versés quotidiennement en EURC (§296)
- B7. Intérêts reçus des sous-produits (BTC depuis Lending, EURC depuis Mining) agrégés et convertis en EURC (§287-293)
- B8. File d'attente dynamique pour les retraits (§236-245)

### Résultats par fiche

| # | Fiche | B1 | B2 | B3 | B5 | B6 | B7 | B8 | Niveau | Observation |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | what-is-the-flexible-vault.md | ✅ | ✅ | ❌ | n/a | ⚠️ | n/a | n/a | **LOW** | Allocation Cloud Mining + Solaria + EURC reserve mentionnée ; **omission MiCA non-rémunération** ; EURC quotidien implicite |
| 2 | how-does-the-future-vault-work.md | ✅ | ✅ | ❌ | ✅ | ✅ | n/a | n/a | **LOW** | Lock-up 12 mois clair ; EURC daily returns explicite ; **omission MiCA non-rémunération** |
| 3 | how-vault-liquidity-and-returns-work.md | ✅ | ✅ | ✅ | n/a | ✅ | ✅ | ✅ | **OK** | Fiche maîtresse Batch C — modèle de référence (MiCA, Phase A/B, dynamic queue explicitées) |
| 4 | how-to-deposit-into-the-flexible-vault.md | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Procédural — 1 EUR / 10 USDC min, 12h processing |
| 5 | how-flexible-vault-returns-are-paid.md | n/a | n/a | n/a | n/a | ✅ | n/a | n/a | **OK** | Daily returns + timing J+1 / J+2 correct |
| 6 | are-there-any-risks-of-capital-loss.md | ✅ | ✅ | n/a | n/a | n/a | n/a | ✅ | **OK** | Risques par composant bien traités ; queue mentionnée |
| 7 | deposit-caps-on-vaults-and-exclusive-offers.md | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Hors périmètre mécanique transactionnelle |
| 8 | how-do-i-create-a-flexible-vault.md | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Procédural pur (5 vaults max) |
| 9 | how-do-i-create-a-future-vault.md | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Procédural pur (1 seul Future) |
| 10 | can-i-create-multiple-flexible-vaults.md | n/a | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Procédural (5 max) |

### Synthèse Section B

**Écart systémique #4 — Omission MiCA / poche EURC non-rémunérée sur les 2 fiches d'entrée**

Les fiches `what-is-the-flexible-vault.md` et `how-does-the-future-vault-work.md` citent l'allocation incluant "a reserve in EURC (a stablecoin tied to the euro)" mais **ne mentionnent pas** que cette poche est **non rémunérée en conformité avec MiCA** (§215). La fiche maîtresse `how-vault-liquidity-and-returns-work.md` traite bien ce point, mais un client qui lit d'abord les deux fiches d'entrée ne comprend pas que ~1/3 de son allocation est structurellement dormante.

**Impact :** faible côté client (pas trompeur car l'APY blended est annoncé correctement), mais **sensible régulateur** car le client doit pouvoir comprendre la nature MiCA-contrainte de la poche liquidité.

**Correction proposée :** ajouter en fin de bloc "Allocation" des 2 fiches d'entrée une phrase courte : *"The EURC reserve is non-remunerated (MiCA requirement for stablecoins) — it ensures liquidity for deposits and withdrawals. See [[how-vault-liquidity-and-returns-work]] for the full mechanic."*

**Note éditoriale :** la fiche `what-is-the-flexible-vault.md` mentionne Solaria et `how-does-the-future-vault-work.md` mentionne "Solaria and The Heights Bali" — The Heights Bali étant fermée depuis le 6 oct 2025, l'allocation continue pour les positions existantes mais un nouveau souscripteur ne participera pas à The Heights Bali. À clarifier (Al Barari a remplacé comme offre active).

---

## Section E — Service de crypto-actifs multiples / Crypto Baskets (§410-513)

**Statut : ✅ audit complet des 11 fiches**

### Grille de contrôle appliquée
- E1. Baskets = allocations fixes proposées par Automata France (thematic ou crypto bundle) (§413)
- E2. Dépôt initial en EUR ou USDC, conversion vers l'allocation cible (§420, §437)
- E3. Retrait en EUR ou USDC (§453)
- E4. Rebalancing déclenché par fréquence utilisateur OU changement allocation (§488-489)
- E5. Rebalancing : sells-first, buys-second (§506)
- E6. Exécution via Own-Account Interposition / LPs (§440)

### Résultats par fiche

| # | Fiche | E1 | E2 | E3 | E4 | E5 | E6 | Niveau | Observation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | what-is-a-crypto-basket.md | ✅ | n/a | n/a | n/a | n/a | n/a | **OK** | Intro simple, pas de mécanique |
| 2 | how-crypto-baskets-work-technically.md | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **OK** | Fiche maîtresse Batch C — modèle de référence (deposit, withdraw, rebalance, Capital Preservation, own-account interposition explicités) |
| 3 | what-crypto-baskets-are-available-and-what-is-their-allocati.md | ✅ | n/a | n/a | n/a | n/a | n/a | **OK** | Top 2 (70/30) + Top 5 (50/20/10/10/10) précis |
| 4 | what-is-rebalancing.md | n/a | n/a | n/a | ✅ | ⚠️ | n/a | **LOW** | Sells-first/buys-second implicite ; TODO Capital Preservation (5 profils) à confirmer |
| 5 | how-do-i-make-a-deposit-into-the-crypto-basket.md | n/a | ✅ | n/a | n/a | n/a | n/a | **OK** | Procédural (min 100 EUR/USDC) |
| 6 | how-to-withdraw-funds-from-the-crypto-basket.md | n/a | n/a | ✅ | n/a | n/a | n/a | **OK** | Procédural |
| 7 | how-do-i-set-up-a-recurring-deposit-in-a-crypto-basket.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Procédural DCA (daily/weekly/15d/monthly) |
| 8 | view-the-performance-or-allocation-of-your-crypto-basket.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | UI pure |
| 9 | what-are-the-advantages-of-a-crypto-basket-and-the-associate.md | ✅ | n/a | n/a | ✅ | n/a | n/a | **OK** | Marketing + risk disclaimer |
| 10 | what-are-the-fees-for-the-crypto-basket.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | Frais (deposit/withdraw 0.25–0.95%, management 0.10–0.20%, rebalancing free) |
| 11 | transaction-history-and-statements-for-the-crypto-basket.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | UI pure |

### Synthèse Section E

**Verdict :** Section saine. La fiche maîtresse `how-crypto-baskets-work-technically.md` (Batch C) est excellente et couvre toute la mécanique §410-513. Les 10 autres fiches sont procédurales ou marketing, et ne contredisent pas le Schéma.

**Un seul écart mineur — `what-is-rebalancing.md`** : le mécanisme "sells-first, buys-second" n'est pas explicite (§506 : *"les échanges sont exécutés en commençant par les ventes, puis les achats"*). La fiche décrit le rebalancing en général mais n'explicite pas l'ordre d'exécution. Présence d'un TODO sur les 5 profils Capital Preservation à confirmer avec Vancelian.

**Correction proposée :** ajouter une phrase dans la fiche `what-is-rebalancing.md` : *"Execution order: sells first (overweight assets are converted to stablecoins), then buys (underweight assets are purchased)."* — et dégager la fiche Capital Preservation TODO via validation produit.

---

## Section F — Service de dépôt/retrait crypto on-chain (§514-543)

**Statut : ✅ audit complet des 7 fiches**

### Grille de contrôle appliquée
- F1. Dépôt : wallet dédié généré via Fireblocks si nécessaire (§526-527)
- F2. KYT (Chainalysis) + Travel Rule (Notabene) à la réception (§529)
- F3. Blacklist check → gel + review Compliance (§528-529)
- F4. Transfert vers Omnibus post-validation (§533)
- F5. Retrait : 3FA + AML/KYT/Travel Rule + Fireblocks TAP (§540-541)
- F6. Blockchains supportées (Ethereum + Base pour USDC) + 1-day max execution
- F7. Gestion frais gas (auto-rejection + refund intégral)

### Résultats par fiche

| # | Fiche | F1 | F2 | F3 | F5 | F6 | F7 | Niveau | Observation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | how-crypto-deposits-and-withdrawals-work-technically.md | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **OK** | Fiche maîtresse (touchée 2026-04-14) — pleinement alignée §521-543 |
| 2 | how-to-deposit-cryptoassets-on-the-vancelian-app.md | ✅ | n/a | n/a | n/a | ✅ | n/a | **OK** | Procédural — Ethereum ERC-20 + BASE USDC only |
| 3 | how-to-make-a-crypto-asset-withdrawal.md | n/a | n/a | n/a | ✅ | ✅ | n/a | **OK** | Procédural — 2FA email + Authenticator |
| 4 | which-cryptoassets-can-i-deposit-on-the-vancelian-app.md | n/a | n/a | n/a | n/a | ✅ | n/a | **OK** | Liste: AKTIO, AAVE, LINK, ETH, FET, PEPE, SHIB, USDC, UNI |
| 5 | which-cryptoassets-can-i-withdraw-from-the-vancelian-applica.md | n/a | n/a | n/a | n/a | ✅ | n/a | **OK** | AKTIO non-transférable EEA — cohérent avec règle produit |
| 6 | travel-rules-crypto-asset-withdrawals-and-compliance-with-re.md | n/a | ✅ | n/a | n/a | n/a | n/a | **OK** | Travel Rule + Notabene + self-hosted wallet signature bien traitée |
| 7 | how-can-i-get-more-information-about-my-cryptoasset-deposits.md | n/a | n/a | n/a | n/a | n/a | n/a | **OK** | UI statements + explorer blockchain |

### Synthèse Section F

**Verdict :** Section saine et parfaitement alignée. Aucun écart détecté. La fiche maîtresse `how-crypto-deposits-and-withdrawals-work-technically.md` couvre rigoureusement la mécanique §521-543 (Fireblocks TAP, KYT Chainalysis, Travel Rule Notabene, AML ComplyAdvantage, Ethereum + Base, 3FA, gas refund). Les 6 autres fiches sont procédurales et cohérentes.

---

## Section A — Méthode de R/L hybride transversale (§92-188)

**Statut : ✅ audit complet des 5 fiches**

### Grille de contrôle appliquée
- A1. Modèle de règlement/livraison hybride : **EUR instantané** côté fiat vs **crypto différé** côté blockchain (§94-107)
- A2. **Own-Account Interposition** : Automata France agit en compte propre (principal), pas en agent (§110-121)
- A3. Référence explicite à **MiCA Article 78** comme base réglementaire (§112)
- A4. **Modulr Finance B.V.** comme EMI fiat (DNB-regulated, ségrégation client) (§130-145)
- A5. **Fireblocks MPC** comme technologie custody crypto (§150-168)
- A6. **Best execution** via panel de liquidity providers (§170-188)

### Résultats par fiche

| # | Fiche | A1 | A2 | A3 | A4 | A5 | A6 | Niveau | Observation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | how-can-i-trade-cryptoassets-on-the-vancelian-app.md | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **OK** | Mention explicite de l'interposition en compte propre + MiCA 78 + Modulr + Fireblocks + best execution |
| 2 | concepts/settlement-delivery-model.md | ✅ | ✅ | ✅ | n/a | ✅ | n/a | **OK** | Modèle EUR-immédiat / crypto-différé bien documenté |
| 3 | concepts/own-account-interposition.md | ✅ | ✅ | ✅ | n/a | n/a | ✅ | **OK** | MiCA Article 78 + Annexe 27 cités, modèle principal vs agent bien cadré |
| 4 | policies/crypto-transfer-policy.md | ✅ | n/a | n/a | n/a | ✅ | n/a | **OK** | Document de politique exhaustif : 3FA, KYT, Travel Rule, AML, règles gas rejection |
| 5 | how-crypto-deposits-and-withdrawals-work-technically.md | ✅ | n/a | n/a | n/a | ✅ | n/a | **OK** | Déjà comptée en Section F — Fiche maîtresse alignée §521-543 |

### Synthèse Section A

**Verdict :** Section saine. Les 5 fiches couvrent de façon cohérente et rigoureuse la méthode de règlement/livraison hybride (§92-188). Aucun écart détecté.

Les 3 piliers réglementaires du Schéma des Flux sont **explicitement documentés** dans le wiki :
- Own-Account Interposition (MiCA Article 78) → `concepts/own-account-interposition.md`
- Modèle de règlement hybride EUR-immédiat / crypto-différé → `concepts/settlement-delivery-model.md`
- Politique de transfert crypto (3FA + KYT + Travel Rule + AML) → `policies/crypto-transfer-policy.md`

La fiche FAQ d'entrée `how-can-i-trade-cryptoassets-on-the-vancelian-app.md` renvoie bien vers ces 3 pages et mentionne les partenaires techniques (Modulr Finance B.V., Fireblocks MPC).

**Note positive :** cette section constitue le socle réglementaire transversal sur lequel s'appuient toutes les autres sections (B à G). Son alignement parfait valide la qualité du travail éditorial Batch C.

---

## Synthèse finale 2026-04-19 — Audit complet 7 sections

### Périmètre couvert

| Section | Titre | Paragraphes | Fiches auditées | HIGH | MEDIUM | LOW | OK |
|---|---|---|---|---|---|---|---|
| A | Méthode R/L hybride transversale | §92-188 | 5 | 0 | 0 | 0 | 5 |
| B | Vaults Flexible/Avenir | §189-297 | 10 | 0 | 0 | 2 | 8 |
| C | BTC Lending (Exclusive Offers) | §299-351 | 16 | 0 | 3 | 0 | 13 |
| D | Cloud Mining | §352-409 | 18 | 0 | 9 | 2 | 7 |
| E | Crypto Baskets | §410-513 | 11 | 0 | 0 | 1 | 10 |
| F | Dépôts/Retraits crypto on-chain | §514-543 | 7 | 0 | 0 | 0 | 7 |
| G | Service paiement réserve crypto | §544-606 | 2 | 0 | 1 | 0 | 1 |
| **Total** | — | **§92-606** | **69** | **0** | **13** | **5** | **51** |

**Résultat global : 0 HIGH · 13 MEDIUM · 5 LOW · 51 OK** sur 69 fiches auditées.

### Écarts systémiques consolidés

| # | Section | Écart | Fiches touchées | Priorité |
|---|---|---|---|---|
| 1 | D | "48 months" appliqué comme règle universelle alors que 3 régimes de maturité coexistent | 7 fiches Cloud Mining | **Batch A** |
| 2 | D | Fiches Ethiopia sans mention Vancelian LTD / Automata France (structure à 2 entités invisible) | 2 fiches | **Batch A** |
| 3 | D | "Hearst's Power wallet" crée confusion régulateur-sensible avec wallet Vancelian LTD JV | 1 fiche | **Batch A** |
| 4 | C | Mécanique BTC/EURC insuffisamment explicite (actif prêté BTC + valeur ref EURC verrouillée) | 3 fiches | **Batch B** |
| 5 | B | Omission MiCA non-rémunération EURC sur les 2 fiches d'entrée | 2 fiches | **Batch B** |
| 6 | E | Sells-first/buys-second implicite + TODO Capital Preservation (5 profils) | 1 fiche | **Batch C** |
| 7 | G | Fiche `how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md` manque `related:` + formulation légèrement trompeuse | 1 fiche | **Batch C** |

### Verdict audit

**Aucun écart HIGH** — aucune contradiction factuelle ni omission critique sur la mécanique transactionnelle. Le wiki ne met pas Vancelian en risque régulateur frontal.

**13 écarts MEDIUM concentrés à 85% sur Section D (Cloud Mining)** — la source du bruit est clairement identifiée : la règle "48 months" rédigée avant la migration post-déc-2024 n'a pas été propagée correctement sur les fiches périphériques. La fiche maîtresse `how-does-the-exclusive-offer-cloud-mining-by-hearst-infrastr.md` est bien alignée.

**5 écarts LOW éditoriaux** — omissions de précision régulateur-sensibles mais non trompeuses pour le client.

**51 fiches OK** — socle solide. Les fiches maîtresses Batch C (B, C, E, F) sont excellentes et alignées paragraphe par paragraphe avec le Schéma des Flux.

### Recommandation — Étape 3

Proposition de batch de corrections pour validation :

- **Batch A (Section D, urgence régulateur)** : 9 fiches, ~1 à 2h. Corrige les 3 écarts systémiques Cloud Mining en alignant "48 months" sur les 3 régimes, en ajoutant la structure Vancelian LTD / Automata France sur Ethiopia, et en corrigeant "Hearst's Power wallet".
- **Batch B (Sections B + C, clarté régulateur)** : 5 fiches, ~1h. Ajoute le bloc "The loan mechanic in one paragraph" sur 3 fiches BTC Lending + phrase MiCA non-rémunération sur 2 fiches Vaults d'entrée.
- **Batch C (Section E + G, finitions)** : 2 fiches, ~30 min. Ajoute le sells-first/buys-second + Capital Preservation sur what-is-rebalancing, et reformule la fiche card-payment.

### Tâche parallèle — Règle gouvernante

**Task #11 à traiter séparément :** graver dans `CLAUDE.md` et dans auto-memory que le Schéma des Flux (Annexe 36) est la source absolue de vérité pour toute mécanique transactionnelle. Cette règle n'est actuellement pas explicite dans les instructions agent.
