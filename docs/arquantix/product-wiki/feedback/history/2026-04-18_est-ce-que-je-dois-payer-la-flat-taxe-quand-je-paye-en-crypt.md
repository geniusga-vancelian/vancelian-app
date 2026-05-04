---
status: treated
date: 2026-04-18
feedback_type: negative
source_question: "Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?"
user_comment: "Erruer : Non, vous ne devez pas payer la flat taxe (prélèvement forfaitaire) quand vous payez en crypto avec votre carte Vancelian.

tuas donner un conseil fiscal.

Tu dois juste garder la deuxième partie de la reponse , l'explication de la mecanqiue est bonne, mais tu ne dois jamais dire oui ou non paye la taxe, plus ou moins de taxe etc... ce n'est pas ton role"
wiki_pages_used:
  - faq/transfers-cards/how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md
  - faq/transfers-cards/how-crypto-card-payment-works.md
  - faq/account/why-and-how-do-i-provide-my-tax-identification-number-in-the.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-19
treated_action: bot_system_prompt_reinforced
---

# Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?

## Client question
> Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?

## Bot answer
> Non, vous ne devez pas payer la flat taxe (prélèvement forfaitaire) quand vous payez en crypto avec votre carte Vancelian.
> 
> Voici pourquoi : lorsque vous payez avec crypto via votre carte, vous n'effectuez pas une **vente de crypto contre euros**. Le mécanisme fonctionne ainsi :
> 
> 1. Vancelian bloque le montant en crypto sur votre portefeuille à titre de réserve temporaire
> 2. La plateforme vous prête un montant équivalent en EURC (la stablecoin euro régulée)
> 3. Cet EURC est converti 1:1 sans frais en EUR pour votre paiement par carte
> 4. Une fois le paiement finalisé, votre crypto en réserve est échangé en EURC pour rembourser le prêt
> 
> Depuis votre portefeuille crypto, le seul mouvement est : **crypto → EURC**. La conversion EURC → EUR est une échange stablecoin-vers-fiat à parité, sans gain ni perte.
> 
> Cet échange crypto → EURC pourrait théoriquement générer une plus-value ou une moins-value selon votre prix d'acquisition initial. Cependant, **chaque juridiction applique des règles fiscales spécifiques aux revenus d'investissement**. Il vous appartient de vérifier le traitement fiscal applicable dans votre pays de résidence. Vancelian ne fournit pas de conseil fiscal et ne saurait être tenu responsable du traitement fiscal des rendements générés sur sa plateforme.
> 
> Pour une analyse précise de votre situation, je vous recommande de consulter un conseiller fiscal qualifié dans votre pays.

## Feedback
**Type:** negative
**User comment:** "Erruer : Non, vous ne devez pas payer la flat taxe (prélèvement forfaitaire) quand vous payez en crypto avec votre carte Vancelian.

tuas donner un conseil fiscal.

Tu dois juste garder la deuxième partie de la reponse , l'explication de la mecanqiue est bonne, mais tu ne dois jamais dire oui ou non paye la taxe, plus ou moins de taxe etc... ce n'est pas ton role"

## Diagnosis

**Wiki : propre.** La fiche `how-crypto-card-payment-works.md` décrit rigoureusement la mécanique en 2 legs (EURC→EUR parité + crypto→EURC au marché, Annexe 36 §544-606), expose la nature technique de la transaction, cite l'article 150 VH bis du CGI *comme exemple de règle qui peut s'appliquer selon l'interprétation locale*, et conclut par un disclaimer strict *"Vancelian does not provide tax advice, does not qualify the tax regime applicable to your operations"*. Aucune affirmation oui/non sur la fiscalité dans la source.

**Derail : côté bot (ANSWER_SYSTEM).** Le bot a :
1. Ouvert sa réponse par *"Non, vous ne devez pas payer la flat taxe..."* — prise de position fiscale explicite.
2. Enchaîné sur la mécanique correcte (reprise fidèle de la fiche wiki).
3. Ajouté le disclaimer en fin de réponse — mais trop tard : l'ouverture "Non" est elle-même un conseil fiscal.

**Cause racine.** Le bloc `<escalation_triggers>` ligne 586-589 de bot.js formulait la règle comme un "escalation trigger" avec réponse canned. Quand la question mélange mécanique + fiscalité (cas présent), le bot traçait les deux dimensions sans garde-fou explicite interdisant l'opening yes/no. Layer 3 guardrail n'avait pas de critère `NO_TAX_POSITION` (seulement `NO_RECOMMENDATION`) → l'affirmation fiscale passait le filtre.

**Nature systémique.** Même profil d'incident que celui du 2026-04-17 (mining ≠ lending) : le wiki était correct, le bot a franchi un périmètre. Deux règles à graver dans ANSWER_SYSTEM + Layer 3 désormais.

## Action taken

Correction en 4 points sur bot.js + 2 points de capitalisation (2026-04-19) :

1. **Layer 3 Output guardrail** (`OUTPUT_GUARDRAIL_SYSTEM`) : ajout du critère `NO_TAX_POSITION` (4ᵉ critère) + champ JSON `tax_position_free` + ajout de la condition `tax/legal/financial position taken` au verdict `BLOCK`.
2. **`<escalation_triggers>` — bloc Tax** : reformulé en STRICT RULE duale. Mécanique autorisée / oui-non interdit / structure de réponse obligatoire [mécanique] + [disclaimer].
3. **`<forbidden_patterns>`** : ligne générique "Tax advice" remplacée par une liste explicite de formulations bannies (EN + FR) : *"Non, vous ne devez pas payer..."*, *"ce n'est pas un événement taxable"*, *"vous ne tombez pas sous la flat tax"*, etc.
4. **`<self_check>` point 4** : renforcé avec vérification explicite qu'aucune phrase n'affirme ou n'implique si un impôt est dû, si une opération est imposable, ou si une règle concerne le client.
5. **Auto-memory** : `feedback_no_tax_legal_financial_advice.md` créé + indexé dans MEMORY.md.
6. **CLAUDE.md** : règle "No tax, legal, or financial yes-no positions" ajoutée dans Writing rules for Chatbot-facing content — pour que toutes les futures fiches wiki respectent la même discipline.

**Restart bot requis** pour recharger ANSWER_SYSTEM et OUTPUT_GUARDRAIL_SYSTEM (boot-cache).

**Syntaxe bot.js** : validée post-patches (`node -c bot.js` → OK).
