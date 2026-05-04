---
status: treated
date: 2026-04-20
feedback_type: needs_improvement
source_question: "Pour ma déclaration fiscale 2025 en plus de la déclaration annexe 2086 (cessions imposables), dans l'attente de la réponse de mon rescrit fiscal, je déclare mes revenus passifs sous le régime des B.N.C annexe 2042 PRO C. WALTIO qui traite ma déclaration mentionne , peut-être par méconnaissance ou par généralité, les revenus de source Française. Mes revenus passifs (mining) sont-ils de source Française ou étrangère et de quels pays?"
user_comment: "Reclassified by Jean — 3 défauts : (1) 'Vancelian opère' attribution fausse (Vancelian = intermédiaire, Hearst opère), (2) structure inversée (détails techniques en amont alors que question fiscale → disclaimer + expert doivent ouvrir), (3) schéma de flux absent (contrepartie directe = Vancelian LTD ADGM, opérateur = Hearst)."
wiki_pages_used:
  - faq/exclusive-offers/cloud-mining-mining-sites-and-geography.md
  - faq/legal-compliance/lcb-ft-aml-compliance.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: system
treated_date: 2026-04-20
treated_action: bot_rule_added
---

# Pour ma déclaration fiscale 2025 — revenus passifs Cloud Mining (source française ou étrangère ?)

## Client question
> Pour ma déclaration fiscale 2025 en plus de la déclaration annexe 2086 (cessions imposables), dans l'attente de la réponse de mon rescrit fiscal, je déclare mes revenus passifs sous le régime des B.N.C annexe 2042 PRO C. WALTIO qui traite ma déclaration mentionne, peut-être par méconnaissance ou par généralité, les revenus de source Française. Mes revenus passifs (mining) sont-ils de source Française ou étrangère et de quels pays ?

## Bot answer
> Je comprends que vous prépariez votre déclaration fiscale 2025 et que vous ayez besoin de clarifier l'origine géographique de vos revenus de mining pour déterminer leur qualification fiscale.
>
> Sur la question de la source géographique de vos revenus Cloud Mining :
>
> Vancelian opère des sites de mining via **Hearst** dans **7 pays** (USA, Brésil, Éthiopie, Oman, Kazakhstan, Norvège, Émirats arabes unis). Votre capital spécifique est déployé sur trois sites principaux : **Éthiopie, États-Unis, et Kazakhstan**. Les revenus générés proviennent donc de ces trois juridictions — pas de France.
>
> Cependant, cette information technique ne répond qu'à une partie de votre question. La qualification fiscale complète de vos revenus (source étrangère vs. française, régime applicable, traitement sous BNC, interaction avec votre rescrit fiscal en cours) dépend de votre situation personnelle, de votre résidence fiscale, et des règles spécifiques de votre État.
>
> **Important** : Vancelian n'est pas un conseiller fiscal. [...]
>
> Votre rescrit fiscal en cours et votre expert-comptable ou conseiller fiscal sont les bons interlocuteurs pour déterminer la qualification exacte et le régime applicable à vos revenus Cloud Mining au regard de votre situation.

## Feedback
**Type:** needs_improvement (reclassifié)
**Correction Jean:** *"Si tu parles de Vancelian sois précis, Vancelian est TOUJOURS un intermédiaire, donc ici déjà il faut dire la contrepartie qui fournit le mining puis ensuite tu précises Vancelian LTD ADGM pour bien séparer. Ensuite tu le dis juste après 'cette information technique ne répond qu'à une partie de votre question' — donc pourquoi présenter en amont ??? La qualification fiscale complète dépend de votre situation... Oui il faut commencer par là (1) + (2) disclaimer tax + (3) rappeler le schéma de flux. Le client fait quoi avec qui ? Il achète de la puissance à un tier Vancelian LTD ADGM basé aux UAE. Il ne fait pas lui-même du mining. Donc pour toute question spécifique il faut demander à un spécialiste fiscal et juste communiquer ces transactions et les conditions du service utilisé, l'expert fiscal ensuite c'est lui de se prononcer, c'est pas à nous de donner un avis ou d'halluciner."*

## Diagnosis

Trois défauts structurels sur une même réponse.

### Défaut 1 — Attribution imprécise ("Vancelian opère")

Le bot écrit : *"Vancelian opère des sites de mining via Hearst"*. Cette formulation fusionne deux rôles distincts :
- **Opérateur** : Hearst Solution FZCO (UAE, FZCO Dubai) — exploite les fermes, installe les machines, gère l'énergie, assure le hashrate.
- **Intermédiaire** : Vancelian LTD ADGM (UAE, ADGM) — contrepartie directe du client, vend l'accès à la puissance, n'opère aucune machine.

Même la page wiki `cloud-mining-mining-sites-and-geography.md` ligne 28 dit correctement : *"Vancelian's Cloud Mining capacity is **operated by Hearst**"*. C'est le bot qui a simplifié de travers en écrivant *"Vancelian opère via Hearst"*.

Pourquoi c'est grave ici : dans un contexte fiscal, la fusion des rôles change radicalement la qualification de source. Si l'opérateur est Vancelian LTD ADGM (UAE), la source fiscale pointe vers une chaîne UAE → sites Hearst. Si le bot laisse entendre que Vancelian opère en France, la qualification fiscale potentielle bascule. Cette précision est load-bearing pour l'expert fiscal.

### Défaut 2 — Structure inversée

Le bot :
1. Présente en amont : "Vos revenus proviennent d'Éthiopie, USA, Kazakhstan — pas de France"
2. Ajoute ensuite : "Mais cette info ne répond qu'à une partie de votre question"
3. Puis disclaimer tax + redirect expert

Problème : présenter une réponse technique géographique en premier crée l'illusion que Vancelian répond à la question fiscale. Le *"cependant cette info ne répond qu'à une partie"* arrive trop tard — le client a déjà lu la "réponse". Sur une question fiscale, la structure correcte est l'inverse :

1. **(1) La qualification fiscale dépend de la situation personnelle → expert fiscal** (c'est LA réponse)
2. **(2) Disclaimer tax standard**
3. **(3) Schéma de flux factuel** (ce que l'expert exploitera — contreparties, jurisdictions, nature du contrat)
4. **(4) Redirect support + expert**

La géographie n'est pas une réponse, c'est un input pour l'expert.

### Défaut 3 — Schéma de flux absent

Le bot donne la géographie des sites (Éthiopie, USA, Kazakhstan) mais oublie la structure contractuelle qui est le véritable matériel pour l'expert fiscal :
- **Contrepartie directe du client** : Vancelian LTD ADGM (UAE).
- **Opérateur** : Hearst Solution FZCO.
- **Objet du contrat** : achat de puissance de calcul (hashrate). Le client n'opère pas de machine, ne détient pas de hardware, ne mine pas lui-même.

Sans ces trois éléments, l'expert fiscal ne peut pas qualifier : *BNC ? BIC ? Revenu de source étrangère ? Traité fiscal UAE-France applicable ? Rescrit fiscal en cours — qu'est-ce qu'il couvre ?* Toutes ces questions reposent sur la nature du contrat et l'identité de la contrepartie, pas sur la localisation physique des machines.

## Action taken

1. **bot.js — `<forbidden_patterns>` renforcé** : interdiction explicite de *"Vancelian opère / exploite / réalise / gère [activité sous-jacente]"*. Vancelian LTD ADGM est TOUJOURS intermédiaire. L'opérateur est la contrepartie nommée par produit (Hearst pour mining, Solaria pour Al Barari, etc.). Règle load-bearing pour toute question touchant à la responsabilité opérationnelle, la localisation de l'activité, le risque de contrepartie, ou la source fiscale.

2. **bot.js — `<factual_discipline>` étendu** : ajout d'une structure OBLIGATOIRE en 4 étapes pour les questions tax / legal / regulatory-interpretation :
   - (1) Qualification dépend de la situation personnelle + redirect expert — **en OUVERTURE**
   - (2) Disclaimer tax standard
   - (3) Schéma de flux (qui fait quoi avec qui)
   - (4) Redirect support + expert
   Interdiction explicite de commencer par des détails techniques (géographie, €40M déployés, etc.) — ce sont des inputs pour l'expert, pas des réponses.

3. **bot.js — nouvel `<example>` canonique** : question BNC source géographique traitée avec la structure correcte (disclaimer + expert → schéma de flux → redirect).

4. **Ticket archivé** : `history/` avec diagnostic complet + action taken. Status `needs_improvement` / `bot_rule_added`.

5. **Auto-memory** : deux règles gravées — *"Vancelian = intermédiaire, jamais opérateur"* et *"Tax question structure = expert-first, not technique-first"*.

Pattern à surveiller dans les prochains tickets : toute ouverture du bot par *"Vancelian opère X"*, *"Vancelian réalise Y"* ou par des détails techniques (géographie, capital déployé, hashrate) sur une question fiscale → candidat à reclassification.
