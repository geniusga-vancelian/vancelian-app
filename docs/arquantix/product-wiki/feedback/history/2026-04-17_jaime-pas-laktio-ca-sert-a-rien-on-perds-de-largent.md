---
status: treated
date: 2026-04-17
feedback_type: positive
source_question: "J'aime pas l'aktio ca sert a rien, on perds de l'argent"
user_comment: ""
wiki_pages_used:
  - faq/aktio/what-is-aktio.md
  - faq/aktio/aktio-utility-and-benefits.md
  - faq/memberships/privilege-club-tier-benefits.md
  - faq/company/about-vancelian.md
channel_id: C0ASFKQFY2V
feedback_user: U08A82QF5T9
treated_date: 2026-04-21
treated_action: "Règle AKTIO 2-level triage gravée dans bot.js (2 forbidden_patterns + 2 examples canoniques) et auto-memory feedback_aktio_framing.md. Bénéfices Privilege Club jamais cités par défaut → redirect vancelian.com/en/memberships. Restart requis."
---

# J'aime pas l'aktio ca sert a rien, on perds de l'argent

## Client question
> J'aime pas l'aktio ca sert a rien, on perds de l'argent

## Bot answer
> Je comprends votre frustration. Permettez-moi de clarifier ce qu'est réellement AKTIO et son rôle dans Vancelian.
>
> **Ce qu'AKTIO n'est pas**
>
> AKTIO n'est pas une action Vancelian, ni un investissement financier classique. C'est un jeton utilitaire (utility token) émis sur la blockchain Ethereum selon la norme ERC-20. Il ne promet pas de rendement garanti, et sa valeur en EUR fluctue comme tout actif crypto.
>
> **Ce qu'AKTIO sert réellement à faire**
>
> AKTIO est conçu pour accélérer votre progression dans le **Privilege Club** — le programme de fidélité de Vancelian. Plus vous en détenez ou en verrouillez, plus vous gagnez de **Points de Fidélité**, ce qui vous propulse vers les tiers supérieurs (Bronze → Elite).
>
> **Les bénéfices concrets aux tiers supérieurs**
>
> À titre d'exemple, un client Elite bénéficie de :
> - Rendements plus élevés : Coffre Flexible jusqu'à 6,43% APY, Coffre Avenir jusqu'à 8,31% APY
> - Frais de trading réduits : 0,25% contre 0,95% en Bronze
> - Carte VISA Metal gratuite
> - Commissions de parrainage jusqu'à 15%
>
> Ces avantages s'appliquent à TOUS vos investissements et transactions Vancelian — pas seulement à AKTIO.
>
> **Si vous ne l'utilisez pas**
>
> Si AKTIO ne vous intéresse pas, vous n'êtes pas obligé d'en détenir. Vous pouvez progresser dans le Privilege Club par d'autres moyens documentés — vérifiez auprès du support à support@vancelian.com pour explorer les alternatives.
>
> Souhaitez-vous que j'approfondisse comment fonctionnent les Points de Fidélité ou les bénéfices des tiers supérieurs ?

## Feedback
**Type:** positive
**User comment:** "none"

## Diagnosis (2026-04-21)

Positive feedback trompeur — la réponse est **structurellement fausse** sur 6 plans. Le message client n'est pas une question, c'est une **opinion négative vague sans sollicitation**. Le bot a néanmoins produit un pitch commercial complet en 7 paragraphes, ce qui ouvre une surface de spam (un utilisateur peut répéter des plaintes pour générer des défenses répétées du jeton).

### Défaut 1 — Absence de triage sollicitation vs non-sollicitation

Le bot n'a pas distingué *"J'aime pas ça"* (opinion, pas de question) de *"AKTIO est-il un scam ?"* (question factuelle explicite). Les deux méritent des traitements opposés.

### Défaut 2 — Reflective listening prohibé

*"Je comprends votre frustration. Permettez-moi de clarifier..."* viole la règle gravée `feedback_institutional_framing.md` (registre sobre, pas de décoration empathique).

### Défaut 3 — Structure éditoriale marketing

*"Ce qu'AKTIO n'est pas / Ce qu'AKTIO sert à faire / Les bénéfices concrets"* est une structure de pitch commercial, pas une réponse support.

### Défaut 4 — Énumération des bénéfices Privilege Club avec chiffres

Le bot a listé : APY 6,43% Flex, 8,31% Avenir, frais 0,25% vs 0,95%, carte VISA Metal gratuite, commissions 15%. Ces chiffres n'ont pas à être cités par défaut — ils sont sur la page dédiée `https://vancelian.com/en/memberships`, évoluent, et leur énumération est exactement le pattern "défense → pitch" qui ouvre la surface de spam.

### Défaut 5 — "Alternatives" sans redirect URL page dédiée

*"explorer les alternatives"* redirige seulement vers support@vancelian.com sans mentionner la page canonique `vancelian.com/en/memberships` qui documente toutes les voies de progression Privilege Club.

### Défaut 6 — Clôture engageante

*"Souhaitez-vous que j'approfondisse les bénéfices des tiers supérieurs ?"* = engagement commercial prohibé par `feedback_institutional_framing.md` (pas d'anticipation de sous-questions) et par la nouvelle règle AKTIO (ne jamais proposer d'approfondir les bénéfices).

## Action taken

**A. Wiki** — Aucune correction nécessaire (les fiches AKTIO et Privilege Club sont factuelles ; c'est le bot qui détournait le contenu). Vérifié que `faq/memberships/privilege-club-tier-benefits.md` reste la page canonique et que l'URL publique `https://vancelian.com/en/memberships` est la référence canonique pour la redirection.

**B. bot.js — 2 nouveaux `<forbidden_patterns>`** ajoutés après le pattern "Stigmatising AKTIO" (ligne 718) :

1. **AKTIO pitching on a vague complaint or opinion** — sur une plainte vague sans question explicite, le bot doit répondre par la phrase guardrail unique et s'arrêter.
2. **AKTIO benefits enumeration without explicit request** — ne jamais lister les bénéfices Privilege Club (APY, frais, carte, commissions) quand la question porte sur AKTIO lui-même.

**C. bot.js — 2 nouveaux `<example>` canoniques** ajoutés avant `</examples>` :

Niveau 1 (plainte vague) :
```
Client: J'aime pas l'AKTIO ça sert à rien, on perd de l'argent
Assistant: Je n'ai pas détecté de sollicitation précise dans votre message. Si vous avez une question spécifique sur AKTIO, précisez et je ferai de mon mieux pour y répondre.
```

Niveau 2 (question factuelle scam/perte) :
```
Client: L'AKTIO c'est un scam ou pourquoi on perd de l'argent dessus ?
Assistant: AKTIO est un actif numérique (crypto) avec un objectif utilitaire dans l'écosystème Vancelian.
Comme tout actif numérique, investir en crypto comporte des risques de volatilité. L'investissement dans ces actifs peut ne pas être adapté à votre profil de risque.
Si AKTIO ne vous intéresse pas, vous n'êtes pas obligé d'en détenir. Vous pouvez progresser dans le Privilege Club par d'autres moyens documentés — pour plus d'informations, consultez la page dédiée https://vancelian.com/en/memberships ou contactez support@vancelian.com.
```

**D. Auto-memory** — `feedback_aktio_framing.md` créé avec règle 2-level triage, réponses canoniques, interaction avec règles antérieures, forbidden patterns canoniques. Entrée ajoutée à `MEMORY.md`.

**E. Validation syntaxe** — `node -c bot.js` OK.

## Restart requis

Boot-cache bot ⇒ les 2 nouveaux forbidden_patterns et les 2 nouveaux examples ne seront actifs qu'**après redémarrage du bot**.
