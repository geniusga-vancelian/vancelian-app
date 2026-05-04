---
status: treated
date: 2026-04-20
feedback_type: negative
source_question: "Vous pouvez me dire combien je vais payer d'impôts sur mes gains crypto ?"
user_comment: "[le complément technique après le redirect expert] n'est pas utile"
wiki_pages_used:
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-20
treated_action: bot_rule_extended_post_redirect_stop
---

# Vous pouvez me dire combien je vais payer d'impôts sur mes gains crypto ?

## Client question
> Vous pouvez me dire combien je vais payer d'impôts sur mes gains crypto ?

## Bot answer (structure)

La réponse bot comporte 5 blocs :
1. Décline directe (*"Je ne peux pas vous dire combien..."*).
2. Qualification dépend de la situation/pays, avec exemples de juridictions (France, Belgique, Luxembourg, Suisse).
3. Disclaimer Vancelian + responsabilité client.
4. **[Problématique]** *"Ce que je peux vous transmettre à titre factuel..."* → 3 bullets : EURC stablecoin, pas de retenue, responsabilité client.
5. Clôture *"C'est tout ce que je peux vous dire. Pour connaître votre impôt exact, contactez..."*.

Blocs 1+2+3+5 = structure correcte, alignée sur la règle `feedback_tax_question_structure.md`.
Bloc 4 = **hors règle** et objet du feedback négatif.

## Feedback
**Type:** negative
**User comment:** *"ce complément d'information n'est pas utile"* — Jean cite l'intégralité du bloc 4 comme à supprimer.

## Diagnosis

Un défaut principal + un secondaire.

### Défaut 1 — Information stuffing post-redirect
Après avoir redirigé vers l'expert fiscal (blocs 1-3), le bot a rouvert une surface en ajoutant des *"éléments techniques à titre factuel"* (EURC, pas de retenue, responsabilité). Ces informations :
- n'ont pas été demandées ;
- réintroduisent un registre commercial/produit (*"stablecoin euro-régulé"*) après un refus de conseil ;
- rouvrent une conversation que le redirect expert avait close ;
- amènent le client à considérer à nouveau la question comme étant traitable par le bot.

**Règle existante applicable** : `feedback_advice_decline_no_product_list.md` du 2026-04-19 — *"Décliner conseil = refus + renvoi support STOP ; jamais d'enchaînement sur liste produit"*. La règle a été cristallisée sur les questions de conseil AKTIO, mais s'applique ici par symétrie : tout complément "produit" après un refus de conseil = violation.

**Règle existante applicable** : `feedback_tax_question_structure.md` du 2026-04-20 — *"JAMAIS détails techniques en amont (géographie, montants)"*. Même interdiction à étendre en **aval** : JAMAIS détails techniques en aval non plus. Le redirect clôt la réponse.

Le pattern commun : le bot ne supporte pas de terminer par un redirect sans "apporter de la valeur" entre-temps. Cette anxiété de valeur ajoutée génère des compléments non sollicités.

### Défaut 2 — Sur-précision sur les juridictions
Bloc 2 énumère *"France, Belgique, Luxembourg, Suisse"*. Cette liste n'a pas été demandée et ajoute du bruit à la qualification "dépend de votre pays". La phrase *"les règles dépendent de votre pays de résidence"* aurait suffi.

C'est un cousin mineur du défaut principal : tentative d'ajouter de la précision pédagogique là où le redirect expert était la vraie réponse.

## Action taken

1. **bot.js — `<forbidden_patterns>` étendu** : interdiction explicite de "complément technique à titre factuel" / "éléments que vous pouvez transmettre à votre expert" après un redirect fiscal ou juridique. Le redirect est la phrase de clôture.

2. **bot.js — `<examples>` canonique réécrit** : exemple impôts crypto avec 3 paragraphes courts maximum (décline + qualification dépend du pays + redirect expert). Stop.

3. **Auto-memory `feedback_tax_question_structure.md`** étendu avec la clause *"stop after redirect"* : le redirect clôt la réponse, pas de reprise produit/technique après.

4. **Ticket archivé** en `history/` avec diagnostic complet.

## Pattern à surveiller

Toute réponse bot à une question fiscale/légale qui contient *"cependant"*, *"à titre factuel"*, *"ce que je peux vous transmettre"*, *"éléments techniques"*, *"pour votre expert"* après le redirect vers support/expert → candidat à reclassification systématique. Le redirect doit être suivi d'une phrase de clôture brève ou de rien.
