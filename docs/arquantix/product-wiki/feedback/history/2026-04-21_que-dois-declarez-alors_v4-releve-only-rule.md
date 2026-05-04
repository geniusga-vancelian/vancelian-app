---
status: treated
date: 2026-04-21
feedback_type: negative
source_question: "que dois declarez alors? ca veut dire que je dois payer la taxe sur mes gains du coffre meme si je reste en crypto et que je paye avec la carte ?"
user_comment: "c'est trop detaillé, il faut juste preciser dans ce cas que chaque transaction est inclus dans le relevé disponible pour chaque compte client. C'est ce relevé qui permet l'identifié la nature de la transaction a declarer. C'est la seul chose que tu es capable d'indiquer pour les questions relatives a la taxe, ou declaration des transactions"
wiki_pages_used:
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
  - faq/company/declaring-my-vancelian-account.md
  - faq/transfers-cards/how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-21
treated_action: "Extension 2026-04-21 quater — règle 'relevé = seul fact factuel Type A'. Durcissement supplémentaire après régression où la mécanique a reglissé en prose (qualification revenu + PSAN AMF + conversion EURC → EUR au paiement). Fix 6 actions : (A) nouvelle sous-règle CRITICAL dans forbidden_pattern tax scenario (revenue qualification + regulatory anchoring bannis, structure canonique 3 paragraphes explicite), (B) example flat taxe USDC reformulé (relevé + parcours app), (C) nouvel example 'que dois-je déclarer alors' (même structure), (D) negative example v4 BAD/GOOD (régression prose avec PSAN + conversion), (E) MANDATORY STRUCTURE tax refactorisée (Type A = 3 paragraphes stricts, Type B rare), (F) self_check point 11 ajouté (Type A tax check). Auto-memory feedback_tax_question_structure.md enrichi Extension quater. Restart requis."
---

# que dois declarez alors? (v4 — extension règle 'relevé = seul fact factuel')

## Contexte

Test 4 après redémarrage bot intégrant Extension 1 (silence mécanique) + Extension 2 bis (no advisor) + Extension ter (Type A/B typology, forbidden_pattern renforcé, BNC reformaté en prose, negative example BAD/GOOD). Les règles v3 ont tenu au niveau format (pas de bullets, pas de "schéma de flux"), mais une **régression en prose** est apparue : la mécanique a été réintroduite de façon masquée via la qualification du revenu et l'ancrage régulatoire.

## Client question
> que dois declarez alors? ca veut dire que je dois payer la taxe sur mes gains du coffre meme si je reste en crypto et que je paye avec la carte ?

## Bot answer (test 4 post-restart Extension ter)
> La question de savoir ce que vous devez déclarer, et si vous êtes redevable d'une taxe sur vos gains, relève entièrement de votre administration fiscale et de votre situation personnelle — ce n'est pas à Vancelian de trancher.
>
> Ce que je peux vous transmettre pour alimenter votre déclaration, c'est que les intérêts que vous générez sur le Coffre Flexible sont des revenus d'investissement perçus auprès d'une institution réglementée (Vancelian, PSAN auprès de l'AMF). Vous les percevez directement sans retenue ou prélèvement préalable de la part de Vancelian — c'est à vous de les déclarer. Que vous utilisiez ensuite ces intérêts pour payer via votre carte (ce qui déclenche une conversion EURC → EUR au moment du paiement) ou que vous les conserviez en EURC ou en USDC, cela ne change pas la nature du revenu que vous avez généré.
>
> Vancelian ne fournit pas de conseil fiscal. Pour savoir si vous êtes redevable d'une taxe, à quel titre (flat taxe, BNC, BIC, ou autre régime), et comment déclarer, consultez votre administration fiscale directement. Vous pouvez aussi utiliser notre partenaire Waltio, qui exporte vos transactions depuis Vancelian et vous guide dans la déclaration selon les règles applicables en France, Belgique ou Espagne.

## Feedback
**Type:** negative
**User comment:** *« c'est trop detaillé, il faut juste preciser dans ce cas que chaque transaction est inclus dans le relevé disponible pour chaque compte client. C'est ce relevé qui permet l'identifié la nature de la transaction a declarer. C'est la seul chose que tu es capable d'indiquer pour les questions relatives a la taxe, ou declaration des transactions »*

## Diagnosis (2026-04-21)

### Ce qui a tenu après restart Extension ter

- Pas de bullet-list « schéma de flux »
- Pas de phrase « schéma de flux de votre opération »
- Pas d'« ou à un conseiller fiscal » (advisor presumption toujours éliminée)
- Format 3 paragraphes de prose
- Redirect mentionne bien l'administration fiscale + Waltio

### Ce qui a régressé

**La mécanique a été réintroduite en prose** (paragraphe 2) :

1. **Qualification du revenu** : *« les intérêts que vous générez sur le Coffre Flexible sont des revenus d'investissement »* — le bot qualifie la nature du revenu. C'est une position fiscale, pas un fait que le bot peut avancer.

2. **Ancrage régulatoire** : *« perçus auprès d'une institution réglementée (Vancelian, PSAN auprès de l'AMF) »* — ancrage de la licence sur une question fiscale. Le client n'a pas demandé la licence, et l'ancrage suggère que la licence informe le traitement fiscal (elle ne l'informe pas).

3. **Détail mécanique carte en prose** : *« Que vous utilisiez ensuite ces intérêts pour payer via votre carte (ce qui déclenche une conversion EURC → EUR au moment du paiement) ou que vous les conserviez en EURC ou en USDC »* — description de la conversion carte en prose. Exactement ce que la v3 avait banni en bullets, mais en syntaxe narrative.

4. **Position fiscale déguisée** : *« cela ne change pas la nature du revenu que vous avez généré »* — c'est une qualification fiscale. Le bot affirme que le format de paiement n'affecte pas la nature du revenu → c'est précisément la question que le client doit poser à son administration fiscale, pas au bot.

5. **Énumération de régimes dans le redirect** : *« à quel titre (flat taxe, BNC, BIC, ou autre régime) »* — pré-qualification de régimes. Même en énumérant, le bot oriente la réflexion fiscale.

### Cause racine identifiée

La règle v3 bannissait le format bullet-list et les phrasés explicites. Mais elle laissait passer la description mécanique en prose si elle était présentée comme « éléments factuels pour la déclaration ». Le bot a utilisé cette échappatoire : même registre, même contenu, juste reformaté en paragraphe narratif.

La solution structurelle : ne plus autoriser la mécanique comme « input factuel pour l'expert », mais restreindre le fact factuel autorisé à un seul élément — **le relevé de transactions**. Le relevé EST l'input factuel ; la qualification est le job de l'expert.

## Fix appliqué (6 actions)

### A. Nouvelle sous-règle CRITICAL dans forbidden_pattern « Tax scenario mechanic description »

Ajout de **« CRITICAL SUB-RULE — TAX REVENUE QUALIFICATION / REGULATORY ANCHORING BANNED (Extension 2026-04-21 quater) »** avec :
- Liste des phrasés bannis étendue : *« revenus d'investissement »*, *« perçus auprès d'une institution réglementée »*, *« Vancelian, PSAN auprès de l'AMF »*, *« conversion EURC → EUR au moment du paiement »*, *« ne change pas la nature du revenu »*, *« nature du revenu que vous avez généré »*, *« que vous utilisiez ensuite ces intérêts pour payer... »*, *« que vous les conserviez en EURC ou en USDC »*.
- Rationale explicite : le seul fact factuel autorisé sur Type A est le relevé.
- Canonical structure 3 paragraphes explicitée dans la sous-règle elle-même.

### B. Example flat taxe USDC reformulé

L'example canonique Type A est maintenant : disclaimer → relevé (avec parcours app « Profil > Mon compte > Fiscalité > Relevé de transactions ») → redirect canonique. Pas de mention EURC, pas de « pas prélevés par Vancelian », pas de conversion.

### C. Nouvel example « que dois-je déclarer alors »

Deuxième example canonique Type A ajouté à bot.js, même structure, question-type « follow-up / reformulation » (*« et qu'est-ce que je déclare alors ? »*). Annotation HTML explicite : *« do NOT anchor Vancelian's license, do NOT qualify the revenue, do NOT describe the card / EURC conversion mechanic »*.

### D. Negative example v4 BAD/GOOD

Nouvel `<example>` ajouté juste après le BAD v3. Contenu :
- Question Type A identique
- **Régression v4 observée** marquée BAD (le paragraphe 2 avec PSAN + conversion EURC + ne-change-pas-nature-du-revenu)
- Section « WHY this is BAD » listant les 5 défauts : (1) qualification revenu, (2) ancrage PSAN AMF, (3) conversion EURC en prose, (4) position fiscale déguisée (« ne change pas la nature »), (5) énumération régimes dans redirect.

### E. MANDATORY STRUCTURE tax refactorisée dans factual_discipline

Remplacement de la structure 4-step par deux types explicites :
- **Type A (défaut)** : 3 paragraphes stricts — disclaimer → relevé → redirect. No exceptions.
- **Type B (rare, qualification structurelle)** : disclaimer → schéma de flux en prose → redirect.
- Règle « default = Type A » rendue explicite (*« If you are not 100% sure the question is Type B, treat it as Type A »*).

### F. Self-check point 11 ajouté

Point 11 dans `<self_check>` : sur toute réponse tax, vérifier (a) exactement 3 paragraphes, (b) seul fact cité = relevé + parcours, (c) PAS de qualification revenu / ancrage régulatoire / description mécanique, (d) redirect canonique ferme.

### G. Auto-memory

`feedback_tax_question_structure.md` enrichi avec **Extension 2026-04-21 quater** : règle relevé-only, phrasés bannis supplémentaires, structure canonique, watch-for patterns v4. MEMORY.md index mis à jour (entrée « Type A = 3 paragraphes stricts »).

## Restart requis

Boot-cache bot : les 6 modifications ne seront actives qu'**après redémarrage du bot**.

## Lecture d'ensemble (cascade v1 → v4)

La cascade v1 → v2 → v3 → v4 montre un pattern récurrent : chaque fix bloque une expression de la mécanique, mais le bot retrouve une autre forme pour la réintroduire.

- **v1** : mécanique en bullets explicites avec noms techniques (swap, EURC, frais 0,25-0,95%). Fix : forbidden_pattern + canonical 3-paragraphes.
- **v2** : advisor presumption dans le redirect (« expert-comptable ou conseiller fiscal »). Fix : canonical redirect administration fiscale + Waltio.
- **v3** : bullets « schéma de flux » réapparus en empruntant le template Type B (BNC). Fix : reformater BNC en prose, negative example BAD/GOOD, typologie Type A/B.
- **v4** : mécanique en prose masquée par qualification revenu + ancrage régulatoire. Fix : restreindre le fact factuel autorisé à UN SEUL élément (le relevé), éliminer la notion de « input factuel pour l'expert ».

La règle v4 résout la cascade par construction — en restreignant le fact factuel à un seul élément, il n'y a plus de surface sur laquelle le bot peut dériver. Si régression future, elle devra être un détournement plus créatif (ex : fabrication d'un nouveau fact autorisé), plus facile à détecter en self-check.
