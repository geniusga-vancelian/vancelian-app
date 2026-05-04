---
status: treated
date: 2026-04-18
feedback_type: negative
source_question: "Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?"
user_comment: "Vancelian propose le paiment en crypto avec une mecanique singulière.

Le flow chart montre que lors d'une demande de paiement ou retrait crypto, il est d'abord initié une ''credit line'' en EURC en fonction de la reserve disponible sur la crypto choisi pour la transaction.

Les EURC sont préter et convertie 1:1 sans frais  en EUR ce qui permet d'executer la transaction CB ou retrait.

Apres le paiement le montant exact debité en EUR permet de connaitre le montant a echanger (exemple si le client a utiliser le BTC, on va convertir les BTC en EURC pour couvrir la credit line dû en EURC pour cloturer la credit line temporaire.

Ainsi la transaction reel n'est pas directement une transaction Crypto => Fiat, mais une transaction Crypto=> crypto avec un pret intermediare en EURC => EUR (soit une echange EURC => EUR qui ne genere pas de plus value = flat)

Cette mecanique est propre a Vancelian, mem si la transaction direct n'est aps crypto => FIat , il imcombe au client de prendre ses responsabilité fiscale, cependant la nature de la transaction relaisé doit bien etre préciser telle quelle aux instance fiscale et peut en focntion des interpretation ne pas etre consider comme une transaction materialisant une somme inclu dans les montant de plus value de l'utilsiatuer"
wiki_pages_used:
  - faq/transfers-cards/how-crypto-card-payment-works.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
  - faq/account/why-and-how-do-i-provide-my-tax-identification-number-in-the.md
  - faq/transfers-cards/what-fees-apply-to-non-eur-payments.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-18
treated_action: "CEO-provided clarification on Vancelian's crypto card payment mechanic (reserve + EURC loan + EURC→EUR at parity, with crypto→EURC exchange at repayment) confirmed by Annexe 36 Schéma des flux §544-606. Wiki page wiki/faq/transfers-cards/how-crypto-card-payment-works.md rewritten in narrative style to expliciter the two-leg structure (Leg 1: EURC→EUR at parity, no gain/loss; Leg 2: crypto→EURC at market price, crypto-to-crypto exchange) and instruct the client to present this technical nature to their tax advisor. Vancelian does not qualify the tax regime. See the companion auto_gap entry of the same date for the full action log."
---

# Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?

## Client question
> Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?

## Bot answer
> La flat taxe est un régime fiscal spécifique applicable dans certaines juridictions. Vancelian ne fournit pas de conseil fiscal — chaque pays applique ses propres règles à l'imposition des revenus d'investissement et des transactions.
> 
> Concernant les paiements par carte Vancelian en crypto : techniquement, vous effectuez une conversion de crypto-actifs en EUR pour finaliser un paiement. Le traitement fiscal de cette conversion dépend entièrement de la législation de votre pays de résidence. Certaines juridictions considèrent cela comme une cession imposable, d'autres non.
> 
> Il est de votre responsabilité de vérifier le dispositif fiscal applicable dans votre pays de résidence et de consulter un conseiller fiscal qui pourra évaluer votre situation personnelle à la lumière de votre statut de résident et des règles locales en vigueur.
> 
> Vancelian ne saurait être tenu responsable du traitement fiscal des opérations effectuées sur sa plateforme.

## Feedback
**Type:** negative
**User comment:** "Vancelian propose le paiment en crypto avec une mecanique singulière.

Le flow chart montre que lors d'une demande de paiement ou retrait crypto, il est d'abord initié une ''credit line'' en EURC en fonction de la reserve disponible sur la crypto choisi pour la transaction.

Les EURC sont préter et convertie 1:1 sans frais  en EUR ce qui permet d'executer la transaction CB ou retrait.

Apres le paiement le montant exact debité en EUR permet de connaitre le montant a echanger (exemple si le client a utiliser le BTC, on va convertir les BTC en EURC pour couvrir la credit line dû en EURC pour cloturer la credit line temporaire.

Ainsi la transaction reel n'est pas directement une transaction Crypto => Fiat, mais une transaction Crypto=> crypto avec un pret intermediare en EURC => EUR (soit une echange EURC => EUR qui ne genere pas de plus value = flat)

Cette mecanique est propre a Vancelian, mem si la transaction direct n'est aps crypto => FIat , il imcombe au client de prendre ses responsabilité fiscale, cependant la nature de la transaction relaisé doit bien etre préciser telle quelle aux instance fiscale et peut en focntion des interpretation ne pas etre consider comme une transaction materialisant une somme inclu dans les montant de plus value de l'utilsiatuer"

## Diagnosis

CEO feedback (U01UY0Q7ZE1) — provides the authoritative description of Vancelian's singular card-payment mechanic, confirmed by the source document:

> **Annexe 36 "Schéma des flux" §552-606 — Service de paiement sur réserve de crypto-actifs**
> *§554 : « il choisit le crypto-actif à utiliser comme réserve »*
> *§560 : « Le montant maximum du paiement sur réserve est bloqué sur le wallet crypto du client en tant que réserve »*
> *§562 : « **L'équivalent de la réserve en crypto-actifs est prêté au client en EURC** »*
> *§575 : « Tout ou partie de la réserve en crypto-actif est **échangé pour un montant R en EURC** pour rembourser le paiement sur réserve »*
> *§592 : « L'utilisateur **a emprunté des EURC** d'un montant équivalent à la réserve de crypto-actif »*

This matches the CEO's description exactly: the only movement on the client's crypto-asset is crypto → EURC (not crypto → EUR). The EURC → EUR leg is a stablecoin-to-fiat exchange at parity that does not generate a gain or a loss.

The bot's previous answer misqualified the operation as *"techniquement, vous effectuez une conversion de crypto-actifs en EUR"* — which is the default description of a card-payment crypto flow in the market but does **not** describe Vancelian's actual mechanic. This is the core correction requested.

## Action taken

Wiki page `wiki/faq/transfers-cards/how-crypto-card-payment-works.md` fully rewritten in narrative style. New sections added:

- **"What happens after you pay — the repayment leg"** — explicit statement that the only movement on the crypto-asset is crypto → EURC (not crypto → EUR), matching §575 of Annexe 36.
- **"Why this mechanic matters — the technical nature of the transaction"** — decomposes the operation into Leg 1 (EURC → EUR at parity, no gain/loss) and Leg 2 (crypto → EURC at market price, crypto-to-crypto exchange). Mentions the French flat tax / article 150 VH bis CGI as an example of a regime where the qualification matters, **without qualifying the regime applicable to the client** (that remains the tax advisor's judgment).
- **"What Vancelian does and does not do"** — Vancelian provides the technical record of every leg; does not provide tax advice; does not qualify the regime.

The `questions:` field of the wiki page was expanded with French and English tax-related variants so the bot routes flat-tax queries to this page on next boot-cache reload.

**Restart required:** YES.

See the companion `auto_gap` entry of the same date for the full action log.
