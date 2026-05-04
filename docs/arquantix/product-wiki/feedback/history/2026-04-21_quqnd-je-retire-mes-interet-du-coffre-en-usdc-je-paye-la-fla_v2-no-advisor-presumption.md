---
status: treated
date: 2026-04-21
feedback_type: negative
source_question: "quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?"
user_comment: "la notion d'expert comptable ici ne vas pas

Il faut juste preciser administration fiscale, nous n'avons pas a preampté sur le fait que le client a iun conseillé ou pas"
wiki_pages_used:
  - faq/savings/how-flexible-vault-returns-are-paid.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-21
treated_action: "RETEST POST-RESTART — réponse 3 paragraphes courts OK (règle silence-mécanique-amont tient). Nouveau défaut subtil : presumption conseiller. Règle 'No tax advisor presumption' gravée → 1 nouveau forbidden_pattern bot.js + 3 examples tax alignés (flat taxe USDC, BNC Cloud Mining, combien je vais payer) + 2 fiches wiki nettoyées (declaring-my-vancelian-account.md, where-can-i-find-a-statement-of-all-my-transactions.md) + Extension 2026-04-21 bis dans feedback_tax_question_structure.md. Redirect canonique : 'administration fiscale + Waltio optionnel'. Restart requis."
---

# quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains? (v2 — retest)

## Contexte

Ce ticket est le **retest du matin** (2026-04-21) après redémarrage du bot intégrant la règle Extension 2026-04-21 (silence sur mécanique en amont + forbidden_pattern "Tax scenario mechanic description" + example canonique 3 paragraphes).

## Client question
> quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?

## Bot answer (retest post-restart)
> La qualification fiscale de vos intérêts — notamment si la flat taxe s'applique — dépend entièrement de votre situation personnelle, de votre pays de résidence, et du régime fiscal applicable dans votre juridiction.
>
> Chaque juridiction applique des règles fiscales spécifiques aux revenus d'investissement, qu'ils soient générés en crypto ou en monnaie classique. Il vous appartient de vérifier le dispositif fiscal applicable dans votre pays de résidence. Vancelian ne fournit pas de conseil fiscal et ne saurait être tenu responsable du traitement fiscal des rendements générés sur sa plateforme.
>
> Pour connaître le régime applicable à vos intérêts et la taxe exigible, contactez votre expert-comptable ou un conseiller fiscal qualifié dans votre juridiction. Ils pourront vous aider à qualifier votre situation et vos opérations.

## Feedback
**Type:** negative
**User comment:** *"la notion d'expert comptable ici ne va pas. Il faut juste préciser administration fiscale, nous n'avons pas à préempter sur le fait que le client a un conseiller ou pas."*

## Diagnosis (2026-04-21)

### Amélioration vs v1 (matin)

- **Longueur :** 3 paragraphes (vs 6 le matin) ✓
- **Silence sur mécanique :** le bot ne décrit plus le flux EURC → USDC ✓
- **Structure :** disclaimer → qualification situation personnelle → redirect ✓

La règle Extension 2026-04-21 gravée ce matin **tient correctement** après restart.

### Défaut résiduel — presumption conseiller

Le redirect final ouvre par *"contactez votre expert-comptable ou un conseiller fiscal qualifié"*. C'est une **présomption sociale** :
- Elle implique que le client a, ou doit avoir, un professionnel fiscal payé.
- Elle exclut implicitement tous les clients qui n'en ont pas (et qui n'ont pas besoin d'en avoir un pour leurs déclarations crypto Vancelian).
- Elle crée une frontière tacite avec une partie du public Vancelian.

**Positionnement institutionnel :** Vancelian s'adresse à des investisseurs de tous niveaux, pas uniquement à ceux qui disposent d'un conseiller patrimonial. La source officielle, neutre, **disponible à tous**, est l'**administration fiscale**.

Jean 2026-04-21 : *"la notion d'expert-comptable ici ne va pas. Il faut juste préciser administration fiscale, nous n'avons pas à préempter sur le fait que le client a un conseiller ou pas."*

## Redirect canonique (gravé)

**FR :**
> *"Pour toute précision sur votre imposition, contactez votre administration fiscale. Vous pouvez également solliciter notre partenaire Waltio pour vos déclarations crypto."*

**EN :**
> *"For any precision on your taxation, contact your tax administration. You may also use our partner Waltio for your crypto declarations."*

**Waltio conservé** comme outil partenaire Vancelian documenté (outil de préparation déclarations crypto, proposé en option avec *"vous pouvez également"*, pas comme présomption).

## Action taken

**A. bot.js — 1 nouveau `<forbidden_patterns>`** *"Presuming a tax advisor in tax redirects"* ajouté après *"Tax scenario mechanic description"* : interdit tous les phrasés présumant un conseiller (expert-comptable, conseiller fiscal, tax advisor, fiscal expert, conseiller qualifié). Phrasage canonique imposé.

**B. bot.js — 3 examples tax alignés** :
1. Example BNC Cloud Mining (l. 1057-1068) — supprimé *"Elle relève de votre expert-comptable ou conseiller fiscal, éventuellement en lien avec le rescrit fiscal"*, supprimé *"pour alimenter votre analyse avec votre expert"*, supprimé *"données matérielles à transmettre à votre expert-comptable ou à votre conseiller fiscal"* → remplacés par phrasé neutre *"pour alimenter votre déclaration"* et redirect canonique.
2. Example *"combien je vais payer"* (l. 1078-1085) — supprimé *"contactez votre expert-comptable ou un conseiller fiscal qualifié dans votre juridiction"* → remplacé par redirect canonique.
3. Example *"flat taxe USDC"* créé ce matin — dernier paragraphe aligné sur le redirect canonique (*"Pour toute précision sur votre imposition, contactez votre administration fiscale. Vous pouvez également solliciter notre partenaire Waltio pour vos déclarations crypto."*).

**C. Auto-memory** — `feedback_tax_question_structure.md` enrichi avec **Extension 2026-04-21 bis** : règle "No tax advisor presumption", phrases bannies listées, redirect canonique FR/EN fixé, justification institutionnelle.

**D. Wiki — 2 fiches nettoyées** :
- `faq/company/declaring-my-vancelian-account.md` (l. 83) — *"please consult a tax advisor, tax expert, or our partner Waltio"* → *"contact your tax administration. You may also use our partner Waltio for your crypto declarations"*.
- `faq/crypto/where-can-i-find-a-statement-of-all-my-transactions.md` (l. 44) — *"please contact a fiscal expert or our partner Waltio"* → *"contact your tax administration. You may also use our partner Waltio for your crypto declarations"*.

**E. Validation syntaxe** — `node -c bot.js` → OK.

## Restart requis

Boot-cache bot ⇒ le nouveau forbidden_pattern et les 3 examples corrigés ne seront actifs qu'**après redémarrage du bot**.
