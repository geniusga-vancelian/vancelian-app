---
status: treated
date: 2026-04-24
feedback_type: positive
source_question: "Oui of course. Quel est le produit le plus risquer des 2 ? "
user_comment: ""
wiki_pages_used:
  - faq/exclusive-offers/dubai-villa-risk-summary.md
  - faq/savings/how-vault-liquidity-and-returns-work.md
  - faq/exclusive-offers/how-are-returns-generated-dubai-villa.md
  - faq/legal-compliance/risk-warning-summary.md
  - faq/savings/what-is-the-flexible-vault.md
channel_id: C0ASFKQFY2V
feedback_user: U094N940EEP
treated_date: 2026-04-25
treated_action: "New FAQ page + 6 wiki corrections + new memory rule on support redirect framing"
---

# Oui of course. Quel est le produit le plus risquer des 2 ? 

## Client question
> Oui of course. Quel est le produit le plus risquer des 2 ? 

## Bot answer
> Le profil de risque est structurellement différent entre les deux — il n'y a pas de réponse universelle "l'un est plus risqué que l'autre" car cela dépend de ce que vous entendez par risque.
> 
> **Le Coffre (Flexible ou Avenir)** distribue votre capital entre trois allocations : Cloud Mining, Solaria, et une réserve EURC. Cette diversification **réduit votre exposition à un risque unique**. Si l'une des trois sous-jacentes rencontre une difficulté, votre capital n'y est exposé que partiellement. En contrepartie, le rendement est plus modéré (5,1% à 8,31% selon le statut et le coffre).
> 
> **Une Offre Exclusive** (comme Dubai Villa) concentre **100% de votre capital sur un seul projet**. Vous êtes exposé directement aux risques de ce projet : exécution immobilière, calendrier de revente, performance de Solaria comme contrepartie. Aucune diversification n'amortit une difficulté. En contrepartie, le rendement est plus attractif (10,7% à 11,5%).
> 
> **La différence clé** : le Coffre absorbe les chocs via la diversification — vous ne perdez jamais 100% d'un coup. L'Offre Exclusive concentre le risque — une seule contrepartie, un seul projet. C'est pourquoi le rendement est plus élevé : le taux reflète directement cette exposition concentrée.
> 
> **Point important** : aucun des deux produits ne comporte une garantie formelle. Si la contrepartie défaille — que ce soit un sous-jacent du Coffre ou Solaria directement — votre capital est à risque. C'est la limite inhérente à ce type d'investissement en direct lending.
> 
> Pour décider lequel correspond à votre profil, cela dépend de votre tolérance à la concentration, de votre horizon d'investissement et de votre appétit pour le rendement. Mais ce type de décision allocation relève d'un conseil personnalisé — contactez le support Vancelian à support@vancelian.com si vous souhaitez explorer votre situation spécifique.

## Feedback
**Type:** positive
**User comment:** "none"

## Diagnosis

Despite positive client feedback, CEO audit (Jean Guillou, 2026-04-25) flagged 6 issues:

1. **"rencontre une difficulté"** (Vault) — alarmist semantic. Should be **"contre-performance"**.
2. **Missing**: "l'allocation peut être adaptée pour compenser la contre-performance" (diversification is dynamic, not static).
3. **"Aucune diversification n'amortit une difficulté"** (Exclusive Offer) — must add the BP margin framing: "cependant une marge de sécurité est incluse via la marge prévue par le BP".
4. **"vous ne perdez jamais 100% d'un coup"** — extremely problematic phrasing, implies one CAN lose 100% in several events. Replace with "cela permet un meilleur management de la contre-performance potentielle".
5. **"votre capital est à risque"** — must normalise residual risk: "comme tout produit financier un risque résiduel est toujours présent".
6. **STRUCTURAL ISSUE**: "contactez le support si vous souhaitez explorer votre situation spécifique" — implies the support gives personalised advice. The support helps clients FIND information; the support is NOT an advisory channel. This rule applies transversally across the wiki.

## Action taken

**5-phase response (no bot.js / ANSWER_SYSTEM modification):**

- **Phase A** — New FAQ page `wiki/faq/savings/comparing-risk-vault-vs-exclusive-offer.md` integrating the 6 corrections, with structural comparison table, BP margin framing, residual risk normalisation, and the new support-redirect framing as canonical example.

- **Phase B** — Audited 33 wiki files for problematic redirect patterns. Delegated to Explore subagent.

- **Phase C** — Applied 6 corrections in mass (3 HIGH on investment topics, 3 MEDIUM on fee confirmations + 1 bonus):
  - HIGH: `vault-vs-exclusive-offer.md` (today's page itself), `how-vault-liquidity-and-returns-work.md`, `the-heights-bali-project-reference.md`
  - MEDIUM: `how-crypto-baskets-work-technically.md` (×2), `what-are-the-fees-for-the-crypto-basket.md`, `how-can-i-invest-in-a-closed-exclusive-offer-via-deposit-window.md`
  - Pattern applied: "consult/confirm with a Vancelian advisor" → "verify in the app / contact Vancelian support to help locate the documentation".

- **Phase D** — New memory rule `feedback_support_redirect_framing.md` documenting forbidden patterns, approved patterns, topic distinctions, canonical close phrasing.

- **Phase E** — Updated `index.md` (Savings 15 → 16 pages), `log.md` entry, ticket archived.

- **Total wiki pages**: 231 → 232.
- **Bot restart required** for boot-cache to pick up the new page and corrected content.
