# Cartographie Schéma des Flux × Wiki — 2026-04-18

**Objet :** Matrice de correspondance entre les services documentés dans l'Annexe 36 *Schéma des Flux* (Notice Vancelian, septembre 2025, v1) et les fiches wiki qui décrivent ces mêmes mécaniques.

**Règle gouvernante :** Le Schéma des Flux est la **source absolue de vérité** pour toute mécanique transactionnelle. C'est le document que le régulateur utilise pour vérifier la réalité opérationnelle. Toute fiche wiki qui décrit un produit/service générant une transaction doit être alignée sur cette source.

**Convention de référence dans la matrice :** `§N-M` = paragraphes N à M du document `raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx`.

---

## Vue d'ensemble — 7 services transactionnels

L'Annexe 36 décrit 7 blocs de services :

| # | Service | Plage § | Type |
|---|---------|---------|------|
| A | Méthode de R/L hybride (base transversale) | §92-188 | Infrastructure règlement-livraison |
| B | Service de coffre "Flexible" / "Avenir" (Vaults) | §189-297 | Produit d'épargne |
| C | Service d'offre exclusive (BTC Lending) | §299-351 | Produit de prêt |
| D | Service de programme de minage (Cloud Mining) | §352-409 | Produit de vente de puissance de calcul |
| E | Service de crypto-actifs multiples (Crypto Baskets) | §410-513 | Produit de portefeuille diversifié |
| F | Service de dépôt et retrait crypto | §514-543 | Transaction on-chain |
| G | Service de paiement sur réserve crypto (Card Payment) | §544-606 | Paiement carte |

---

## Section A — Méthode de R/L hybride (infrastructure transversale)

**Schéma des Flux — §92-188**
- §92-113 : Modèle hybride (R/L crypto différé fin de journée + R/L EUR immédiat temps réel)
- §114-142 : Fonctionnalité d'échange crypto↔fiat et crypto↔crypto (modèle d'interposition de comptes)
- §144-155 : R/L différé crypto fin de journée (consolidation, deltas nets, custody Fireblocks)
- §157-168 : R/L immédiat EUR (comptes Modulr ségrégués)
- §170-188 : Ajustement de liquidité avec LPs fin de journée

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| how-can-i-trade-cryptoassets-on-the-vancelian-app.md | faq/crypto/ | À vérifier |
| how-crypto-deposits-and-withdrawals-work-technically.md | faq/crypto/ | Touchée 2026-04-14 (Fireblocks framing) — à revérifier |
| settlement-delivery-model.md | concepts/ | Touchée 2026-04-14 (Fireblocks + Modulr DNB) — à revérifier |
| own-account-interposition.md | concepts/ | Touchée 2026-04-14 — à revérifier |
| crypto-transfer-policy.md | policies/ | Touchée 2026-04-14 — à revérifier |

---

## Section B — Service de coffre "Flexible" / "Avenir" (Vaults)

**Schéma des Flux — §189-297**
- §189-204 : Contexte de fonctionnement + structure d'allocation (poche liquidité EURC + poches yield + rééquilibrages)
- §205-223 : Dépôt client (conversion auto en EURC, wallet Fireblocks dédié, MiCA → EURC non rémunéré, lock-up Avenir, phase passive)
- §225-251 : Retrait client (file d'attente dynamique, vérification poche liquidité, conversion, canaux de sortie)
- §253-297 : Paiement intérêts + rééquilibrage fin de journée (Phase A allocation review + Phase B agrégation intérêts conversion BTC→EURC)

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| what-is-the-flexible-vault.md | faq/savings/ | À vérifier |
| how-does-the-future-vault-work.md | faq/savings/ | À vérifier |
| how-vault-liquidity-and-returns-work.md | faq/savings/ | Réécrite 2026-04-18 (Batch C) — à valider vs §253-297 |
| how-to-deposit-into-the-flexible-vault.md | faq/savings/ | À vérifier |
| how-flexible-vault-returns-are-paid.md | faq/savings/ | À vérifier |
| are-there-any-risks-of-capital-loss.md | faq/savings/ | À vérifier |
| how-do-i-create-a-flexible-vault.md | faq/savings/ | Procédural — moins critique |
| how-do-i-create-a-future-vault.md | faq/savings/ | Procédural — moins critique |
| can-i-create-multiple-flexible-vaults.md | faq/savings/ | Procédural |
| deposit-caps-on-vaults-and-exclusive-offers.md | faq/savings/ | À vérifier |

---

## Section C — Service d'offre exclusive (BTC Lending)

**Schéma des Flux — §299-351**
- §299-304 : Contexte (Automata France partenariat Sociétés RWA, programme de prêt BTC)
- §305-331 : Phase de souscription (dépôt client, conversion auto vers BTC si besoin, livraison BTC fin de journée)
- §333-351 : Phase de paiement intérêts + remboursement

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| how-exclusive-offer-btc-lending-works.md | faq/exclusive-offers/ | Réécrite 2026-04-18 — à valider vs §305-351 |
| how-does-the-dubai-villa-al-barari-exclusive-offer-work.md | faq/exclusive-offers/ | À vérifier |
| how-does-the-7-luxury-villas-in-bali-exclusive-offer-work.md | faq/exclusive-offers/ | À vérifier |
| the-heights-bali-project-reference.md | faq/exclusive-offers/ | Réécrite 2026-04-18 (Batch C) — à valider |
| how-are-returns-generated-dubai-villa.md | faq/exclusive-offers/ | À vérifier |
| guarantees-and-security-al-barari.md | faq/exclusive-offers/ | Touchée 2026-04-18 — à revérifier |
| guarantees-and-security-of-your-investment.md | faq/exclusive-offers/ | À vérifier |
| project-sponsor-responsibilities-al-barari.md | faq/exclusive-offers/ | À vérifier |
| project-sponsor-responsibilities-bali.md | faq/exclusive-offers/ | À vérifier |
| financial-structure-of-the-project.md | faq/exclusive-offers/ | À vérifier |
| how-do-project-exit-windows-work.md | faq/exclusive-offers/ | À vérifier |
| how-can-i-invest-in-a-closed-exclusive-offer-via-deposit-window.md | faq/exclusive-offers/ | À vérifier |
| how-can-i-reinvest-my-returns-into-other-projects.md | faq/exclusive-offers/ | À vérifier |
| what-is-the-7-luxury-villas-in-bali-exclusive-offer.md | faq/exclusive-offers/ | À vérifier |
| what-is-the-exclusive-offer-dubai-villa-al-barari.md | faq/exclusive-offers/ | À vérifier |
| dubai-villa-risk-summary.md | faq/exclusive-offers/ | Créée 2026-04-14 — à revérifier |

---

## Section D — Service de programme de minage (Cloud Mining)

**Schéma des Flux — §352-409**
- §352-360 : Contexte (vente de puissance de calcul, Vancelian LTD ADGM, partenaire Hearst)
- §361-383 : Phase de souscription (EURC encaissé contre vente de puissance de calcul)
- §385-409 : Phase de paiement intérêts + remboursement capital

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| how-cloud-mining-flow-works.md | faq/exclusive-offers/ | Réécrite 2026-04-18 (Batch C) — à valider vs §352-409 |
| how-does-the-exclusive-offer-cloud-mining-by-hearst-infrastr.md | faq/exclusive-offers/ | Touchée 2026-04-18 — à revérifier |
| how-does-the-exclusive-offer-eco-friendly-mining-in-ethiopia.md | faq/exclusive-offers/ | Touchée 2026-04-18 (Batch B) — à revérifier |
| what-is-the-exclusive-offer-cloud-mining-by-hearst-infrastru.md | faq/exclusive-offers/ | À vérifier |
| what-is-the-eco-friendly-bitcoin-mining-in-ethiopia-exclusiv.md | faq/exclusive-offers/ | À vérifier |
| how-does-mining-work-at-vancelian.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-risks-overview.md | faq/exclusive-offers/ | Réécrite 2026-04-18 (Batch C) — à valider |
| cloud-mining-can-i-lose-my-capital.md | faq/exclusive-offers/ | Réécrite 2026-04-18 (Batch C) — à valider |
| cloud-mining-cgupm-investor-obligations.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-bitcoin-halving-impact.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-yield-factors.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-mica-and-european-regulation.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-early-exit-and-transfers.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-who-reimburses-if-bankruptcy.md | faq/exclusive-offers/ | Touchée 2026-04-18 — à revérifier |
| cloud-mining-is-it-a-scam.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-mining-sites-and-geography.md | faq/exclusive-offers/ | À vérifier |
| cloud-mining-vs-direct-bitcoin-purchase.md | faq/exclusive-offers/ | À vérifier |
| migration-to-the-new-cloud-mining-program.md | faq/exclusive-offers/ | À vérifier |

---

## Section E — Service de crypto-actifs multiples (Crypto Baskets / Multi-Digital Assets)

**Schéma des Flux — §410-513**
- §410-414 : Contexte (Multi-Digital Assets)
- §415-447 : Dépôt client (calcul allocation cible, exchanges, interposition)
- §448-481 : Retrait client (sells-first / buys-second)
- §482-513 : Rebalancing (trigger frequency ou allocation change, sells-first / buys-second, Capital Preservation)

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| what-is-a-crypto-basket.md | faq/crypto/ | À vérifier |
| how-crypto-baskets-work-technically.md | faq/crypto/ | Réécrite 2026-04-18 (Batch C) — à valider vs §410-513 |
| what-crypto-baskets-are-available-and-what-is-their-allocati.md | faq/crypto/ | À vérifier |
| what-is-rebalancing.md | faq/crypto/ | À vérifier |
| how-do-i-make-a-deposit-into-the-crypto-basket.md | faq/crypto/ | Procédural |
| how-to-withdraw-funds-from-the-crypto-basket.md | faq/crypto/ | Procédural |
| how-do-i-set-up-a-recurring-deposit-in-a-crypto-basket.md | faq/crypto/ | Procédural |
| view-the-performance-or-allocation-of-your-crypto-basket.md | faq/crypto/ | À vérifier |
| what-are-the-advantages-of-a-crypto-basket-and-the-associate.md | faq/crypto/ | À vérifier |
| what-are-the-fees-for-the-crypto-basket.md | faq/crypto/ | À vérifier |
| transaction-history-and-statements-for-the-crypto-basket.md | faq/crypto/ | À vérifier |

---

## Section F — Service de dépôt et retrait crypto (on-chain)

**Schéma des Flux — §514-543**
- §514-520 : Contexte (dépôts/retraits on-chain via custody Fireblocks)
- §521-535 : Dépôt client (adresse générée, attente confirmation, crédit wallet)
- §536-543 : Retrait client (vérification destination, Travel Rule, envoi)

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| how-crypto-deposits-and-withdrawals-work-technically.md | faq/crypto/ | Touchée 2026-04-14 — à revérifier vs §514-543 |
| how-to-deposit-cryptoassets-on-the-vancelian-app.md | faq/crypto/ | Procédural |
| how-to-make-a-crypto-asset-withdrawal.md | faq/crypto/ | Procédural |
| which-cryptoassets-can-i-deposit-on-the-vancelian-app.md | faq/crypto/ | À vérifier |
| which-cryptoassets-can-i-withdraw-from-the-vancelian-applica.md | faq/crypto/ | Touchée 2026-04-18 (Batch B AKTIO) — à revérifier |
| travel-rules-crypto-asset-withdrawals-and-compliance-with-re.md | faq/crypto/ | À vérifier |
| how-can-i-get-more-information-about-my-cryptoasset-deposits.md | faq/crypto/ | À vérifier |

---

## Section G — Service de paiement sur réserve crypto (Card Payment)

**Schéma des Flux — §544-606**
- §544-547 : Contexte (réserve crypto 15 min, non rémunérée)
- §548-563 : Création du paiement sur réserve (blocage crypto + prêt EURC)
- §564-583 : Remboursement (crypto → EURC, partiel/total)
- §585-606 : Demande de paiement (fenêtre 15 min, utilisation, delta, annulation auto)

**Fiches wiki concernées :**
| Fiche | Emplacement | Statut |
|---|---|---|
| how-crypto-card-payment-works.md | faq/transfers-cards/ | ✅ **Corrigée 2026-04-18** (narrative + nature fiscale) |
| how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md | faq/transfers-cards/ | À vérifier (probable doublon ou procédural) |

---

## Résumé statut global

| Section | Fiches totales | Déjà réécrites 2026-04 | À vérifier |
|---|---|---|---|
| A — R/L hybride | 5 | 5 (touchées 2026-04-14, à revérifier) | 0 |
| B — Vaults | 10 | 1 | 9 |
| C — BTC Lending | 16 | 3 | 13 |
| D — Cloud Mining | 18 | 6 | 12 |
| E — Crypto Baskets | 11 | 1 | 10 |
| F — Dépôt/Retrait crypto | 7 | 2 | 5 |
| G — Card Payment | 2 | 1 | 1 |
| **TOTAL** | **69** | **19** | **50** |

69 fiches wiki décrivent directement une mécanique transactionnelle couverte par l'Annexe 36. Sur ces 69 :
- **19 ont été réécrites ou touchées en avril 2026** → doivent être revérifiées contre l'Annexe 36 avec la nouvelle grille (certaines l'ont été partiellement — ex: la fiche carte crypto l'a été aujourd'hui).
- **50 n'ont jamais été explicitement auditées contre le Schéma des Flux** → scan nécessaire à l'étape 2.

## Non couvert par le Schéma des Flux (rappel)

Fiches à exclure du périmètre de cet audit (elles ne décrivent pas de mécanique transactionnelle soumise au Schéma) :
- `account/` — KYC, 2FA, profil client, sécurité
- `legal-compliance/` — sauf si mentionne un produit
- `company/`, `business/`, `affiliate-partner/`, `b2b-agent/`
- `memberships/` — benefits et frais, pas transactionnel
- `aktio/` — tokenomics et utilité, pas de transaction applicative structurée par Annexe 36
- `transfers-cards/` — hors `how-crypto-card-payment-works.md`, le reste est SEPA/procédural

## Prochaine étape (sur validation)

Étape 2 — Audit de cohérence : pour chaque fiche "à vérifier" ou "à revérifier", vérifier que la mécanique décrite correspond exactement aux paragraphes Annexe 36 de la section. Classer les écarts HIGH / MEDIUM / LOW.

**Proposition de priorisation pour l'étape 2 :**
1. Commencer par section G (déjà faite, sert de référence méthodologique)
2. Puis sections transactionnelles lourdes : D (Cloud Mining — 18 fiches, sensible régulateur + client), C (BTC Lending — 16 fiches)
3. Puis B (Vaults), E (Baskets)
4. Puis F (Dépôt/Retrait), A (R/L transversal)
