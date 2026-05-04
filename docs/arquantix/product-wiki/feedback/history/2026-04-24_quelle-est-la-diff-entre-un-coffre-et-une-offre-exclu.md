---
status: treated
date: 2026-04-24
feedback_type: positive
source_question: "Quelle est la diff entre un coffre et une offre exclu ?"
user_comment: ""
wiki_pages_used:
  - faq/savings/what-is-the-flexible-vault.md
  - faq/savings/how-does-the-future-vault-work.md
  - faq/exclusive-offers/what-is-the-7-luxury-villas-in-bali-exclusive-offer.md
  - faq/exclusive-offers/what-is-the-exclusive-offer-dubai-villa-al-barari.md
  - faq/savings/how-vault-liquidity-and-returns-work.md
channel_id: C0ASFKQFY2V
feedback_user: U094N940EEP
treated_date: 2026-04-25
treated_action: "Wiki corrections + new concept page + new comparison FAQ page (3 phases)"
---

# Quelle est la diff entre un coffre et une offre exclu ?

## Client question
> Quelle est la diff entre un coffre et une offre exclu ?

## Bot answer
> Un Coffre (Flexible ou Avenir) et une Offre Exclusive sont deux produits d'investissement structurellement différents.
> 
> **Un Coffre** est un portefeuille diversifié que vous ouvrez et gérez directement. Vous déposez votre capital, et Vancelian l'alloue automatiquement entre plusieurs sous-jacents : Cloud Mining, Solaria, et une réserve en EURC. Vous percevez des rendements quotidiens (composés automatiquement), et vous pouvez retirer vos fonds à tout moment pour le Flexible, ou après 12 mois pour l'Avenir. Le rendement dépend du mix d'allocation et fluctue légèrement selon l'évolution de cette allocation.
> 
> **Une Offre Exclusive** est un projet spécifique — un programme d'investissement unique avec sa propre structure, sa contrepartie, son calendrier et son rendement dédié. Vous financez directement ce projet : Cloud Mining (achat de puissance de calcul auprès de Hearst Solution FZCO), Dubai Villa (prêt en BTC à Solaria), ou Bali (prêt en BTC à un SPV immobilier). Chaque offre a ses propres conditions : commitment période fixe, maturity date, rendement spécifique, fenêtres de sortie.
> 
> **En résumé** : un Coffre est une **enveloppe diversifiée et flexible** que Vancelian gère pour vous, tandis qu'une Offre Exclusive est un **investissement ciblé dans un projet unique** avec des termes contractuels dédiés. Vous ne pouvez pas « entrer » dans une Offre Exclusive via un Coffre — si vous souhaitez investir dans Dubai Villa, vous créez un dépôt séparé directement dans cette offre.
> 
> Souhaitez-vous des précisions sur l'une ou l'autre structure ?

## Feedback
**Type:** positive
**User comment:** "none"

## Diagnosis

Despite the positive client feedback (👍, no comment), CEO audit (Jean Guillou, 2026-04-25) flagged 7 semantic and regulatory imprecisions in the bot answer:

1. **"portefeuille diversifié"** — gestion/bourse semantics, regulator-sensitive. Should be **"poche diversifiée"**.
2. **"Vancelian alloue automatiquement entre plusieurs sous-jacents"** — missing "**définis en amont du dépôt**" (allocation is contractual, not discretionary).
3. **"fluctue légèrement"** — qualifier "légèrement" is regulator-unsafe; should be **"peut fluctuer"** without qualifier; AND missing the buffer mechanic.
4. **Missing mechanic surfaced**: distributed rates on Vaults and real estate Exclusive Offers are **fixed**; Cloud Mining is the contractual exception (variable); Vancelian's **intermediation margin acts as a buffer** absorbing small variations on the gross yield to preserve a stable client rate. This was not in the wiki.
5. **"Vous financez directement ce projet"** — verb "financer" inadequate (Cloud Mining is a computing-power purchase contract, not financing). Should be **"Vous participez à"** (generic verb).
6. **"Vancelian gère pour vous"** — wrong attribution of responsibility. Client manages by accepting T&C and the pre-defined allocation framework.
7. **"Vous ne pouvez pas entrer dans une Offre Exclusive via un Coffre"** — false framing. Vault allocation explicitly includes Solaria and Cloud Mining. Phrase removed.

## Action taken

Three-phase wiki correction (no bot.js / ANSWER_SYSTEM modification):

- **Phase 1 — New concept page** `wiki/concepts/vancelian-rate-smoothing-and-margin.md` — documents the fixed-rate framework, Cloud Mining variable exception, and Vancelian's intermediation margin acting as a buffer (audience: client, sober, no margin %). Source: CEO directive 2026-04-25.

- **Phase 2 — Corrected 3 source pages**:
  - `wiki/faq/savings/what-is-the-flexible-vault.md` — "portfolio" → "pocket", allocation "defined upfront", new section on rate stability + cross-link.
  - `wiki/faq/savings/how-does-the-future-vault-work.md` — same corrections + risks section reformulated to distinguish fixed distributed rate from underlying allocation risks.
  - `wiki/faq/savings/how-vault-liquidity-and-returns-work.md` — "two-layer portfolio" → "two-layer pocket", new "Why your distributed rate stays stable" section.

- **Phase 3 — New comparison FAQ page** `wiki/faq/savings/vault-vs-exclusive-offer.md` — integrates the 7 corrections in client-facing prose, with a comparison table and counterparty mapping per offer (Vancelian LTD JV for Cloud Mining, Solaria for Dubai, Bali SPV for Bali). Removes the misleading exclusivity framing.

- **Index** updated: Savings 14 → 15 pages; Concepts 4 → 5 pages.
- **Total wiki pages**: 229 → 231.
- **Bot restart required** to reload boot-cache with the new pages and corrected content.
