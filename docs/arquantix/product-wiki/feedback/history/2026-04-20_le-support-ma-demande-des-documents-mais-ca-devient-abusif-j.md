---
status: treated
date: 2026-04-20
feedback_type: negative
source_question: "Le support m'a demandé des documents mais ça devient abusif, je peux ignorer ou contourner ?"
user_comment: "trop d'information => le compte sera bloqué et l'argent inaccessible, ca peut créer de la panique. Méfiance : il y a également trop d'informations de conformité et de jargon, Benjamin est mentionné directement (car son nom est sur le site) mais même s'il était toujours dans la société, c'est trop d'informations à mon goût, et surtout l'information est fausse dans ce cas."
wiki_pages_used:
  - faq/account/email-from-vancelian-compliance-team.md
  - faq/legal-compliance/lcb-ft-aml-compliance.md
  - faq/account/how-can-i-complete-my-identity-verification-kyc-in-the-appli.md
  - faq/legal-compliance/vancelian-compliance-team.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: U08A82QF5T9
treated_date: 2026-04-20
treated_action: institutional_framing_rule_graved_wiki_cleanup_6_files_bot_5_new_forbidden_patterns
---

# Le support m'a demandé des documents mais ça devient abusif, je peux ignorer ou contourner ?

## Client question
> Le support m'a demandé des documents mais ça devient abusif, je peux ignorer ou contourner ?

## Feedback
**Type:** negative
**User comment:** *"trop d'information ; création de panique ; jargon conformité excessif ; Benjamin nommé directement ; information fausse dans ce cas."*

## Diagnosis

Cinq défauts en une seule réponse — cristallise un pattern transversal inédit : **registre institutionnel sobre**.

### Défaut 1 — Nomination d'un individu + info factuelle fausse
*"Son équipe de conformité, dirigée par Benjamin Messika (Chief Compliance Officer)..."*. Deux problèmes superposés :
- **Info factuelle fausse** : Benjamin Messika n'est plus CCO. La fonction n'est actuellement pas pourvue (clarification Jean 2026-04-20).
- **Règle structurelle** : au-delà de la péremption spécifique, le bot ne doit **jamais** citer un individu, quelle que soit sa fonction — la composition évolue, toute mention nominative devient un risque factuel. Le référent stable est toujours le **service** ou le **département**.

Règle Jean citée textuellement : *"le Bot ne dois jamais cité des individus ou répondre à des questions portant à des individus, mais à des services ou département si besoin."*

### Défaut 2 — Décoration régulatoire
*"... répondent à des obligations légales strictes imposées par la réglementation française (Code monétaire et financier) et européenne (MiCA, AML/CFT). Vancelian opère sous supervision de l'AMF en tant que PSAN..."*. Empilement d'acronymes et de références légales comme décoration d'autorité, alors que la règle demandée (fournir les documents KYC) est structurelle et universelle (même règle pour un client UAE sous VARA). Le régulateur n'est pas matériel à la réponse — ne pas le nommer. Jean : *"ne pas citer le jargon MICA france ... car si même réponse pour VARA pas besoin de préciser"*.

### Défaut 3 — Anticipation de sous-questions non posées
Deux sections hallucinées :
- *"Ce qui se passe si vous ne répondez pas : compte gelé / fonds bloqués / sans préavis..."* — crée de la panique, répond à une question que le client n'a pas posée.
- *"Avant d'escalader : contactez support et demandez clarification écrite sur (1) (2) (3)..."* — procédure inventée.

Jean : *"si jamais une autre question est posée du type 'et si je ne communique pas les documents ?' alors oui là la réponse a du sens"*. Pour l'instant, le client demande s'il peut ignorer. Réponse : non. Point.

### Défaut 4 — Anglicisme en réponse française
*"ou vers le Compliance and Internal Control Officer"*. Titre anglais non traduit dans une réponse française. Jean : *"très mal dit (compliance = anglais) il faut supprimer ça"*. La traduction correcte est *"Responsable de la Conformité et du Contrôle Interne (RCCI)"* ou plus simplement *"le service de contrôle interne"*.

### Défaut 5 — Clôture moralisante
*"La transparence fonctionne mieux que le contournement."* Maxime de fin qui lecture, condescendante, hors-sujet. Jean : *"Inutile hors sujet"*.

### Pattern transversal

Les 5 défauts partagent une même racine : le bot ne supporte pas de répondre **au strict nécessaire**. Il veut nommer (donner l'impression de savoir), décorer (autorité), anticiper (prévoyance), angliciser (expertise), moraliser (sagesse). Chaque tentative ajoute du bruit et dilue le factuel. Règle-mère : **registre institutionnel sobre**.

## Réponse cible

2 paragraphes, ~60 mots :

> Ignorer ou contourner les demandes du support n'est pas possible. Les documents demandés — justificatifs d'identité complémentaires, preuve de source de fonds, ou clarifications sur vos transactions — répondent à des obligations réglementaires auxquelles Vancelian est tenu.
>
> Ces demandes sont traitées par le service de conformité. Pour toute question sur un document précis ou sur le contexte d'une demande, contactez support@vancelian.com.

## Action taken

### A. Wiki — nettoyage individuel en profondeur (6 fichiers)

| Fichier | Action |
|---|---|
| `faq/legal-compliance/vancelian-compliance-team.md` | Retrait de **Benjamin Messika** (CCO), **Lesage** (MLRO), **Charreau** (Middle Office) → références fonctionnelles uniquement. Tags et questions purgés des noms. `last_reviewed: 2026-04-20`. |
| `faq/legal-compliance/lcb-ft-aml-compliance.md` | Retrait inline *"(Benjamin Messika)"* → *"The Chief Compliance Officer (CCO) is the direct interlocutor..."*. |
| `faq/legal-compliance/vancelian-legal-advisors.md` | Réécriture complète : retrait de **Stéphane Daniel**, **Anne Maréchal**, **Benjamin Messika**. Tables de carrière individuelles supprimées. Reste le niveau firme (D&A Partners, De Gaulle Fleurance) + scope de mission. Tags et questions purgés. |
| `faq/company/vancelian-team-and-leadership.md` | Passé `audience: internal`. Note top-page : le bot ne cite pas d'individus, redirect vancelian.com/about. Retiré de `index.md`. |
| `faq/company/vancelian-press-and-media.md` | Passé `audience: internal`. Même traitement. Retiré de `index.md`. |
| `faq/company/who-are-the-founders-of-vancelian.md` | Passé `audience: internal`. Même traitement. Retiré de `index.md`. |

### B. Wiki — `index.md` mis à jour

- Section "FAQ — Company" : compteur 15 → 11, 3 pages retirées, commentaire HTML documentant les pages `audience: internal` et la règle source.

### C. bot.js — 5 nouveaux `<forbidden_patterns>` gravés

- Jamais nommer un individu + jamais répondre à une question sur un individu.
- Pas de décoration régulatoire (MiCA / AMF / PSAN / Code monétaire et financier empilés sans matérialité).
- Pas d'anticipation de sous-questions non posées.
- Pas d'anglicismes / titres anglais non traduits en réponse française.
- Pas de clôture moralisante.

### D. bot.js — nouvel `<example>` canonique

Question *"documents support abusifs"* traitée en 2 paragraphes courts (~60 mots), niveau service, redirect direct.

### E. Auto-memory

Fichier créé : `.auto-memory/feedback_institutional_framing.md` (5 règles composites + pattern transversal + canonical example).
Entrée ajoutée à `MEMORY.md`.

### F. Ticket archivé

Ce fichier en `history/` avec diagnostic complet.

## Pattern à surveiller

Toute réponse bot qui contient :
- un prénom+nom de personne (Benjamin, Gaël, Stéphane, Anne, etc.) → reclassification immédiate ;
- un empilement MiCA / AMF / PSAN / AML/CFT / Code monétaire sur une question non-régulatoire → candidat à reclassification ;
- une section *"Ce qui se passe si"* / *"Avant d'escalader"* / *"Si vous contestez"* non demandée → candidat à reclassification ;
- un titre anglais non traduit en réponse française → correction ;
- une phrase finale moralisante / leçon → correction.
