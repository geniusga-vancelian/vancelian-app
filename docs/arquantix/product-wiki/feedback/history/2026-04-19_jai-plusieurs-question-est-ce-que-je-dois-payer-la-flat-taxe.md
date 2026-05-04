---
status: treated
date: 2026-04-19
feedback_type: auto_gap
source_question: "J'ai plusieurs question

Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?
Aussi que me conseil tu comme investissement crypto?
Tu crois que je dois vendre mes aktio vu le prix et acheter du BTC?"
user_comment: "[Auto-detected gap] missing_detail: Add clarification on whether crypto card payments trigger capital gains recognition or other specific tax events across major Vancelian client jurisdictions (FR, DE, IT, UAE, etc.)"
wiki_pages_used:
  - faq/transfers-cards/how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md
  - faq/transfers-cards/what-fees-apply-to-non-eur-payments.md
  - faq/crypto/what-crypto-baskets-are-available-and-what-is-their-allocati.md
  - faq/aktio/what-is-aktio-used-for-utility-and-benefits.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
channel_id: C0ASFKQFY2V
feedback_user: system
treated_date: 2026-04-19
treated_action: bot_system_prompt_reinforced_v2
---

# J'ai plusieurs question

Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?
Aussi que me conseil tu comme investissement crypto?
Tu crois que je dois vendre mes aktio vu le prix et acheter du BTC?

## Client question
> J'ai plusieurs question

Est ce que je dois payer la flat taxe quand je paye en crypto avec la carte vancelian?
Aussi que me conseil tu comme investissement crypto?
Tu crois que je dois vendre mes aktio vu le prix et acheter du BTC?

## Bot answer
> Je vais vous répondre sur chacun de ces points.
> 
> **Sur la fiscalité et le paiement en crypto avec la carte**
> 
> Quand vous payez avec vos crypto-actifs via la carte Vancelian, Vancelian convertit automatiquement le montant en euros au moment du paiement et règle la transaction via le réseau VISA. Techniquement, c'est une conversion de crypto en EUR, puis un paiement en EUR.
> 
> Chaque juridiction applique des règles fiscales spécifiques aux revenus d'investissement et aux opérations de conversion, qu'elles soient perçues en crypto ou en monnaie classique. Il vous appartient de vérifier le dispositif fiscal applicable dans votre pays de résidence — notamment les règles sur la flat tax et le traitement des conversions crypto. Vancelian ne fournit pas de conseil fiscal et ne saurait être tenu responsable du traitement fiscal des rendements générés sur sa plateforme.
> 
> **Sur le choix d'investissement entre AKTIO, BTC et d'autres actifs**
> 
> Je ne peux pas vous recommander d'acheter ou de vendre un actif particulier — ce choix dépend entièrement de votre situation personnelle, votre horizon d'investissement et votre tolérance au risque.
> 
> Ce que je peux vous dire : Vancelian propose plusieurs options crypto. Le **Panier Top 2** (70% BTC / 30% ETH) offre une exposition aux deux plus grandes capitalisations. Le **Panier Top 5** (50% BTC / 20% ETH / 10% XRP / 10% BNB / 10% SOL) offre une diversification plus large. AKTIO est un utility token qui accélère votre progression dans le Privilege Club — ce n'est pas un investissement crypto classique.
> 
> Pour une recommandation adaptée à votre profil, je vous invite à contacter le support Vancelian à support@vancelian.com.

## Feedback
**Type:** auto_gap
**User comment:** "[Auto-detected gap] missing_detail: Add clarification on whether crypto card payments trigger capital gains recognition or other specific tax events across major Vancelian client jurisdictions (FR, DE, IT, UAE, etc.)"

## Diagnosis

Question multi-parties (3 sujets) qui déclenche **4 défauts distincts** du bot, dont 3 sont des régressions de garde-fous déjà revus :

**1. Mécanique paiement crypto erronée (régression wiki-compliance).**
Le bot écrit : *"Techniquement, c'est une conversion de crypto en EUR, puis un paiement en EUR."* → **faux**. La fiche technique [[how-crypto-card-payment-works]] et Annexe 36 §544-606 décrivent un mécanisme à **2 jambes** (not a single crypto→EUR sale) :
- Crypto bloquée en réserve temporaire sur le wallet client
- Vancelian prête au client un équivalent EURC → converti 1:1 sans frais en EUR pour régler la carte via VISA
- Après clearing : la réserve crypto est échangée en EURC pour rembourser le prêt → du point de vue du wallet, le seul mouvement crypto est **crypto → EURC**

Cause racine : PASS 1 retrieval a chargé la fiche courte `how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md` (dont le short_answer ne contenait pas la mécanique 2-legs) mais pas la fiche technique `how-crypto-card-payment-works.md`. Le bot a reconstruit une mécanique plausible mais incorrecte.

**2. Stigmatisation AKTIO (hallucination hors-wiki).**
Le bot écrit : *"AKTIO est un utility token qui accélère votre progression dans le Privilege Club — ce n'est pas un investissement crypto classique."* → **factuellement incorrect et orientant**. Un utility token est une classification crypto normale (la majorité des cryptos sont des utility ou payment tokens) ; la phrase "ce n'est pas un investissement crypto classique" exclut indûment AKTIO de la catégorie investissement et oriente le client à se détourner du token. La wiki [[aktio-utility-and-benefits]] est propre : elle décrit l'utilité factuellement sans cette exclusion.

**3. Decline-and-list sur la question de conseil (régression garde-fou conseil).**
Le bot ouvre correctement : *"Je ne peux pas vous recommander d'acheter ou de vendre un actif particulier..."* — puis enchaîne immédiatement : *"Ce que je peux vous dire : Vancelian propose plusieurs options crypto. Le Panier Top 2... Le Panier Top 5... AKTIO est un utility token..."* → **anti-pattern**. Le refus est annulé par la liste produit qui fonctionne comme orientation implicite. Un refus de conseil doit rester **net** : refus + redirect support, STOP.

**4. Liste crypto incomplète (gap éditorial).**
Quand le bot liste les "options crypto" Vancelian, il ne mentionne que Panier Top 2 + Panier Top 5 + AKTIO. **Manque** : achat direct d'un crypto-actif (BTC, ETH, USDC, etc.) qui est le mode le plus simple et le plus utilisé. Les 3 modes doivent être présents systématiquement : achat direct + Panier Top 2 + Panier Top 5.

**Note :** le point fiscalité (partie 1 de la question client) est bien traité par le bot — la mécanique est décrite (même si fausse sur le "comment") et le disclaimer Vancelian tax est présent. C'est la conséquence directe du correctif du 2026-04-18 qui a tenu.

**Flag Jean explicit :** *"on a déjà revu ces points mais ça revient"* → les corrections doivent être strictes, redondantes et gravées à plusieurs niveaux pour que le pattern ne puisse plus réémerger.

## Action taken

Correctif **4 niveaux** appliqué en session 2026-04-19 :

**A. `vancelian-bot/bot.js` — 6 patches ANSWER_SYSTEM + Layer 3 :**

1. `<escalation_triggers>` **Personalized advice** renforcé — STRICT RULE duale : MUST decline directly ; decline-and-list **FORBIDDEN** ; distinction entre question de conseil (refus net) et question factuelle produit (liste 3 modes autorisée).
2. `<forbidden_patterns>` — 2 nouvelles entrées explicites :
   - Decline-and-list pattern : *"Je ne peux pas vous recommander... Ce que je peux vous dire : Vancelian propose X, Y, Z"* → banni.
   - AKTIO stigma : *"pas un investissement crypto classique"* et équivalents → banni.
3. Layer 3 OUTPUT_GUARDRAIL_SYSTEM — nouveau critère `NO_ADVICE_ECHO` + champ JSON `advice_echo_free` + condition BLOCK si violation détectée après refus de conseil.
4. `<self_check>` point 4 étendu : (a) aucune position fiscale oui/non, (b) aucun decline-and-list.
5. `<examples>` : réécrit l'exemple "J'ai 50k à investir" (ligne 721) — **ancienne version enseignait l'anti-pattern** (refus + énumération produits). Nouvelle version : refus net + invitation à poser une question factuelle sur un produit spécifique.
6. `<examples>` : 2 nouveaux exemples ajoutés :
   - Multi-question miroir de ce ticket (fiscalité + conseil + AKTIO/BTC) avec mécanique 2-legs correcte + disclaimer + refus net pour parties conseil.
   - Question factuelle "Quelles options crypto propose Vancelian ?" listant les **3 modes** (achat direct + Top 2 + Top 5).

Syntaxe bot.js vérifiée : `node -c bot.js` → OK.

**B. Wiki — renforcement fiche courte :**

`wiki/faq/transfers-cards/how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md` — `## Short answer` réécrit pour rendre la mécanique 2-legs EURC explicite en tête de fiche, avec redirection vers `[[how-crypto-card-payment-works]]` pour le détail technique. Raison : si PASS 1 ne charge que la fiche courte, la mécanique correcte doit quand même passer.

**C. `CLAUDE.md` — 3 nouvelles règles Writing rules :**

1. Decline advice ≠ product list — refus doit rester seul.
2. AKTIO framing — utility token = classification crypto normale, jamais "not a real crypto investment".
3. Crypto options are three — achat direct + Top 2 + Top 5, jamais omettre l'achat direct.

**D. Auto-memory — mémoire persistante :**

- `feedback_advice_decline_no_product_list.md` créée — grave la règle decline-and-list + stigma AKTIO + liste 3 modes + citation incident 2026-04-19 + citation Jean *"on a déjà revu ces points mais ça revient"*.
- `MEMORY.md` index mis à jour.

**Action résiduelle côté Jean :** (1) restart bot (boot-cache reload indispensable), (2) test de régression sur la même question multi-parties pour vérifier que les 4 garde-fous tiennent.
