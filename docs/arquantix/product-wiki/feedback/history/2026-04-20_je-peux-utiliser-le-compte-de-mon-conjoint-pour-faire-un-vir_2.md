---
status: treated
date: 2026-04-20
feedback_type: negative
source_question: "Je peux utiliser le compte de mon conjoint pour faire un virement vers mon compte Vancelian ?"
user_comment: "Cette réponse est fausse, elle est vraie uniquement dans le cas où il s'agit du premier versement pour la vérification du compte. Ensuite, il est possible de recevoir des virements d'un tiers, même si des vérifications supplémentaires peuvent exister."
wiki_pages_used:
  - faq/transfers-cards/how-can-i-make-a-deposit.md
  - faq/transfers-cards/how-to-make-a-bank-transfer-from-the-vancelian-app.md
  - faq/account/how-can-i-complete-my-identity-verification-kyc-in-the-appli.md
  - faq/legal-compliance/lcb-ft-aml-compliance.md
channel_id: C0ASFKQFY2V
feedback_user: U08A82QF5T9
treated_date: 2026-04-20
treated_action: wiki_fixed_and_bot_example_added
---

# Je peux utiliser le compte de mon conjoint pour faire un virement vers mon compte Vancelian ?

## Client question
> Je peux utiliser le compte de mon conjoint pour faire un virement vers mon compte Vancelian ?

## Bot answer (extrait)
> Non, vous ne pouvez pas utiliser le compte bancaire de votre conjoint pour faire un virement vers votre compte Vancelian.
>
> Vancelian applique une règle stricte de **correspondance des noms** [...]
>
> **Solution** : demandez à votre conjoint de faire un virement depuis son compte vers votre compte bancaire personnel d'abord. Une fois les fonds sur votre compte, vous pourrez effectuer un virement SEPA standard vers Vancelian sans friction.

## Feedback
**Type:** negative
**User correction:** *"Cette réponse est fausse, elle est vraie uniquement dans le cas où il s'agit du premier versement pour la vérification du compte. Ensuite, il est possible de recevoir des virements d'un tiers, même si des vérifications supplémentaires peuvent exister."*

## Diagnosis

Trois défauts.

### Défaut 1 — Yes/no en ouverture
*"Non, vous ne pouvez pas utiliser le compte bancaire de votre conjoint"*. Même famille que les autres yes/no déjà interdits. Sur une question de procédure bancaire, le bot doit exposer la règle selon le scope, pas poser un verdict binaire.

### Défaut 2 — Surgénéralisation (sur-affirmation par excès d'autorité)
Le bot affirme une *"règle stricte de correspondance des noms"* applicable à tous les virements. Cette règle existe bien dans le wiki, mais elle est **scope-limité** à la vérification initiale du compte.

Sources dans le wiki :
- `account-verification-by-bank-transfer.md` ligne 28 : *"Vancelian performs an account verification by bank transfer **when you register**"* — règle scope registration.
- `why-is-my-transfer-pending.md` ligne 45 : section titrée littéralement *"Why can my **first deposit** be pending?"* — la vérification de correspondance des noms est scopée sur le premier dépôt.

Pour les virements suivants, aucune page wiki ne documente de règle "strict name match universelle". Les transferts SEPA entrants sont traités normalement ; des contrôles de conformité (LCB-FT) peuvent être déclenchés ponctuellement mais ce n'est pas la même règle.

C'est le **symétrique inverse** de la *"fuite vers support par excès de prudence"* (gravée ce matin) : là le bot sous-estimait ce que le wiki dit ; ici le bot sur-étend la portée d'une règle. Même racine — absence de scope-check sur ce que la source affirme vraiment.

### Défaut 3 — Instruction pratique hallucinée
*"Solution : demandez à votre conjoint de faire un virement depuis son compte vers votre compte bancaire personnel d'abord..."*. Cette workaround n'est documentée nulle part. En plus, elle contourne la procédure officielle documentée pour les joint accounts (envoi du RIB en PDF au support Vancelian pour vérification manuelle). Le bot a inventé une solution pratique au lieu de renvoyer vers la procédure officielle.

### Défaut transversal — Longueur
220 mots, 5 paragraphes. La nouvelle règle de concision gravée ce matin (`<editorial_method>` DEPTH CONTROL + `<self_check>` point 10) aurait dû produire 3 paragraphes courts.

## Action taken

1. **Wiki — `how-can-i-make-a-deposit.md` enrichie**. Short_answer réécrit pour poser explicitement la distinction *premier dépôt* (strict name match + procédure joint account via RIB PDF au support) vs. *virements suivants* (possible depuis un tiers, contrôles de conformité éventuels). Nouvelle sous-section *"First deposit vs. subsequent deposits — different rules apply"* en tête de la section bank transfer. Sources enrichies (2 pages cross-linkées). Tags et questions élargis. `last_reviewed: 2026-04-20`.

2. **bot.js — nouvel `<example>` canonique** : question *"compte du conjoint"* traitée avec la structure correcte — distinction first deposit vs. suivants, procédure joint account mentionnée, redirect support. 4 paragraphes courts (~90 mots).

3. **Ticket archivé** en `history/` avec diagnostic complet.

4. **Auto-memory** : nouvelle règle *"Scope-check on strict rules — ne pas étendre une règle KYC/vérification au-delà de son scope documenté dans le wiki"*.

Pattern à surveiller : toute réponse bot qui pose une règle "stricte" / "systématique" / "applicable à tous les cas" sans avoir vérifié le scope précis dans la page source → candidat à reclassification. Symétrique inverse de la fuite vers support par excès de prudence.
