---
status: treated
date: 2026-04-20
feedback_type: positive
source_question: "J'ai plusieurs question

Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?
Aussi que me conseil tu comme investissement crypto?
Tu crois que je dois vendre mes aktio vu le prix et acheter du BTC?"
user_comment: ""
wiki_pages_used:
  - faq/transfers-cards/how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md
  - faq/transfers-cards/what-fees-apply-to-non-eur-payments.md
  - faq/crypto/what-are-the-advantages-of-a-crypto-basket-and-the-associate.md
  - faq/exclusive-offers/cloud-mining-vs-direct-bitcoin-purchase.md
  - faq/aktio/what-is-aktio-used-for.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-20
treated_action: regression_test_passed
related_tickets:
  - feedback/history/2026-04-18_est-ce-que-je-dois-payer-la-flat-taxe-quand-je-paye-en-crypt.md
  - feedback/history/2026-04-19_jai-plusieurs-question-est-ce-que-je-dois-payer-la-flat-taxe.md
---

# Test de régression — question multi-parties (19/04 + 18/04)

## Contexte
Rejeu de la question composite qui avait déclenché les deux incidents consécutifs :
- **2026-04-18** : conseil fiscal ("Non, vous ne devez pas payer la flat taxe")
- **2026-04-19** : 4 défauts (mécanique crypto fausse + stigma AKTIO + decline-and-list + liste crypto incomplète)

Après application des 2 vagues de correctifs (ANSWER_SYSTEM + Layer 3 + wiki short answer + CLAUDE.md + auto-memory) et restart du bot.

## Client question
Mêmes 3 sujets qu'au ticket 2026-04-19 : fiscalité paiement crypto + conseil investissement + arbitrage AKTIO/BTC.

## Bot answer — observation
1. **Mécanique paiement crypto** : décrite correctement en 2 jambes EURC (crypto→réserve, prêt EURC→EUR, crypto→EURC remboursement). Conforme Annexe 36 §544-606.
2. **Fiscalité** : mécanique + disclaimer Vancelian tax, aucune position oui/non. Correctif 2026-04-18 tient.
3. **Conseil investissement** : refus net sans liste produit. Redirect support clair. Correctif 2026-04-19 tient.
4. **AKTIO** : non mentionné — le bot a correctement identifié que "vendre mes AKTIO pour acheter du BTC" relève du conseil, refusé en bloc, pas d'orientation implicite.

## Diagnosis
Aucun défaut. Les 4 garde-fous renforcés fonctionnent en synergie sur une seule question multi-parties :
- `<escalation_triggers>` Tax block (STRICT RULE duale)
- `<escalation_triggers>` Personalized advice (STRICT RULE duale + decline-and-list ban)
- `<forbidden_patterns>` (4 entrées explicites)
- Layer 3 `NO_TAX_POSITION` + `NO_ADVICE_ECHO`
- `<examples>` canoniques (multi-question + factuelle crypto)

## Action taken
Ticket archivé directement en `history/` avec tag `regression_test_passed`.

Aucune action correctrice requise. Confirme que le cycle incident → diagnosis → 4-level fix → test régression est clos pour les patterns :
- Conseil fiscal oui/non
- Decline-and-list
- Mécanique paiement crypto
- Stigmatisation AKTIO
- Liste crypto incomplète
