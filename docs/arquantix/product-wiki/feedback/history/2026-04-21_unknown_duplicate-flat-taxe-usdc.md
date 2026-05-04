---
status: treated
date: 2026-04-21
feedback_type: negative
source_question: "unknown"
user_comment: "Feedback Jean pointant la partie mécanique non nécessaire — doublon du ticket 2026-04-21 flat taxe USDC"
wiki_pages_used:
  - none
channel_id: unknown
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-21
treated_action: "Duplicate du ticket 2026-04-21_quqnd-je-retire-mes-interet-du-coffre-en-usdc-je-paye-la-fla.md. Même bot answer, même défaut (description mécanique EURC → USDC improvisée en réponse à scénario fiscal conditionnel), corrigé par la règle Extension 2026-04-21 silence sur mécanique en amont + forbidden_pattern 'Tax scenario mechanic description' + example canonique 3 paragraphes. Pas de fix additionnel."
---

# unknown — Duplicate ticket flat taxe USDC

## Nature du ticket

Feedback négatif Jean sur la réponse bot du 2026-04-21 (scénario *"quand je retire mes intérêts du coffre en USDC je paye la flat taxe sur mes gains ?"*). Le `user_comment` contient la réponse bot intégrale annotée : *"=> cette partie n'est pas nécessaire et elle n'est pas complète en plus"*, pointant la portion mécanique (3 paragraphes décrivant le flux EURC → USDC).

## Verdict

Duplicate direct du ticket `2026-04-21_quqnd-je-retire-mes-interet-du-coffre-en-usdc-je-paye-la-fla.md`. Même bot answer, même défaut, corrigé par :

- Règle Extension 2026-04-21 gravée dans `feedback_tax_question_structure.md` (silence sur mécanique en amont d'un scénario fiscal conditionnel)
- `<forbidden_patterns>` *"Tax scenario mechanic description"* dans bot.js
- `<example>` canonique 3 paragraphes dans bot.js

Aucune action additionnelle requise.
