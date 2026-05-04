---
status: treated
date: 2026-04-21
feedback_type: auto_gap
source_question: "quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?"
user_comment: "[Auto-detected gap] missing_detail: Documenter le flux technique d'une conversion EURC → crypto-actif (frais appliqués, traitement comptable, qualification pour fins fiscales)"
wiki_pages_used:
  - faq/savings/how-flexible-vault-returns-are-paid.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: system
treated_date: 2026-04-21
treated_action: "Règle 'silence sur mécanique en amont' gravée (Extension 3 de feedback_tax_question_structure.md). bot.js : 1 nouveau forbidden_pattern 'Tax scenario mechanic description' + 1 nouveau example canonique (3 paragraphes courts, redirect relevé appli + admin fiscale). Auto_gap fermé par règle comportementale, pas par ajout wiki. Restart requis."
---

# quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?

## Client question
> quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?

## Bot answer
> La qualification fiscale de vos intérêts — notamment si la flat taxe s'applique — dépend entièrement de votre situation personnelle, de votre pays de résidence, et du régime fiscal applicable dans votre juridiction.
>
> Chaque juridiction applique des règles fiscales spécifiques aux revenus d'investissement, qu'ils soient générés en crypto ou en monnaie classique. Il vous appartient de vérifier le dispositif fiscal applicable dans votre pays de résidence. Vancelian ne fournit pas de conseil fiscal et ne saurait être tenu responsable du traitement fiscal des rendements générés sur sa plateforme.
>
> Ce que je peux vous transmettre à titre factuel — pour que vous le soumettiez à votre expert-comptable ou conseiller fiscal — c'est la mécanique technique :
>
> Vos intérêts quotidiens sur le Coffre Flexible sont crédités directement dans votre Coffre, en EURC (stablecoin euro-régulé). Vous pouvez les retirer ou les dépenser à tout moment avec votre carte Vancelian.
>
> Si vous convertissez ensuite ces intérêts en USDC (ou un autre crypto-actif), vous effectuez un échange EURC → USDC. Cette opération constitue un flux de trésorerie que votre expert-comptable devra qualifier selon les règles de votre juridiction.
>
> Les intérêts eux-mêmes ne sont pas prélevés ou retenus par Vancelian — vous les percevez directement, et c'est votre responsabilité de les déclarer selon le régime de votre pays.
>
> Pour connaître précisément votre imposition (flat taxe ou régime standard, taux applicable, seuils, exceptions), contactez votre expert-comptable ou un conseiller fiscal qualifié dans votre juridiction.

## Feedback
**Type:** auto_gap
**User comment:** "[Auto-detected gap] missing_detail: Documenter le flux technique d'une conversion EURC → crypto-actif (frais appliqows, traitement comptable, qualification pour fins fiscales)"

## Diagnosis (2026-04-21)

Verdict Jean : *"cette réponse est très mauvaise : 1 — trop long, 2 — hors sujet, 3 — imprécis."*

### Défaut 1 — Longueur excessive (6 paragraphes)

Une question fiscale simple (scénario conditionnel *"si je retire en USDC je paye la flat taxe ?"*) appelle une réponse en 3 paragraphes courts. Le bot en a produit 6, avec 3 paragraphes consacrés à une mécanique transactionnelle improvisée.

### Défaut 2 — Hors-sujet : description de mécanique non sollicitée

Le bot a improvisé un schéma de flux *"Vos intérêts quotidiens sur le Coffre Flexible sont crédités directement dans votre Coffre, en EURC (stablecoin euro-régulé). Vous pouvez les retirer ou les dépenser à tout moment avec votre carte Vancelian. Si vous convertissez ensuite ces intérêts en USDC, vous effectuez un échange EURC → USDC. Cette opération constitue un flux de trésorerie..."*.

**Problème structurel :** le client n'a pas demandé comment fonctionne la mécanique. Il a posé un **scénario conditionnel fiscal**. La mécanique n'est pas la réponse attendue ; elle n'est pas non plus nécessaire à la réponse. En la produisant, le bot ouvre une **surface de spam** : un utilisateur peut enchaîner *"et si je convertis en EUR ? et si je paye avec la carte ? et si je retire en SEPA ?"* pour faire décrire tous les flux produit.

La règle symétrique — silence sur mécanique en amont — devient nécessaire.

### Défaut 3 — Imprécision

*"Cette opération constitue un flux de trésorerie que votre expert-comptable devra qualifier"* est une formulation floue qui n'apporte rien au client et n'est pas ancrée dans Annexe 36 Schéma des Flux. La mécanique improvisée n'est pas vérifiée contre les fiches wiki ; elle est produite pour "apporter de la valeur" — anxiété de valeur ajoutée (anti-pattern déjà gravé dans Extension 2).

### Structure correcte (réponse canonique 3 paragraphes)

> La qualification fiscale de vos intérêts — notamment si la flat taxe s'applique — dépend entièrement de votre situation personnelle, de votre pays de résidence, et du régime fiscal applicable dans votre juridiction.
>
> Les intérêts ne sont pas prélevés ou retenus par Vancelian — vous les percevez directement, et c'est votre responsabilité de les déclarer selon le régime de votre pays. Chaque juridiction applique des règles fiscales spécifiques aux revenus d'investissement, qu'ils soient générés en crypto ou en monnaie classique.
>
> Pour comprendre et déclarer vos transactions, téléchargez votre relevé disponible dans l'application et vérifiez la nature de votre transaction (intérêts reçus, échange, paiement…). Déclarez-les ensuite avec votre administration fiscale pour connaître le régime applicable à chaque nature de transaction et, le cas échéant, la taxe applicable aux gains ou plus-values perçus.

## Action taken

**A. bot.js — nouveau `<forbidden_patterns>`** *"Tax scenario mechanic description"* ajouté après le pattern "Post-redirect technical complement" : interdit la description de mécanique transactionnelle (swap EURC/USDC, conversion IBAN, paiement carte, EURC comme stablecoin régulé, intérêts crédités quotidiennement) en réponse à un scénario fiscal conditionnel. Silence = règle par défaut.

**B. bot.js — nouveau `<example>` canonique** ajouté avant `</examples>` :

```
Client: quand je retire mes intérêts du coffre en USDC je paye la flat taxe sur mes gains ?
Assistant: La qualification fiscale de vos intérêts — notamment si la flat taxe s'applique — dépend entièrement de votre situation personnelle, de votre pays de résidence, et du régime fiscal applicable dans votre juridiction.

Les intérêts ne sont pas prélevés ou retenus par Vancelian — vous les percevez directement, et c'est votre responsabilité de les déclarer selon le régime de votre pays. Chaque juridiction applique des règles fiscales spécifiques aux revenus d'investissement, qu'ils soient générés en crypto ou en monnaie classique.

Pour comprendre et déclarer vos transactions, téléchargez votre relevé disponible dans l'application et vérifiez la nature de votre transaction (intérêts reçus, échange, paiement…). Déclarez-les ensuite avec votre administration fiscale pour connaître le régime applicable à chaque nature de transaction et, le cas échéant, la taxe applicable aux gains ou plus-values perçus.
```

**C. Auto-memory** — `feedback_tax_question_structure.md` enrichi avec **Extension 2026-04-21** (silence sur mécanique en amont) : règle plus forte que les extensions précédentes, exception "mécanique décrite uniquement sur insistance explicite du client ou question mécanique pure".

**D. Validation syntaxe** — `node -c bot.js` → OK.

**E. Pas d'action wiki** — la lacune détectée par l'auto_gap ("documenter le flux technique EURC → crypto-actif") ne doit **pas** être comblée par une fiche wiki. La règle comportementale suffit : le bot ne répond plus à un scénario conditionnel fiscal par une mécanique, donc la fiche ne serait jamais sollicitée par un routage tax. Si la question mécanique est posée pure ("comment marche la conversion EURC → USDC ?"), les fiches crypto trading et carte existantes répondent.

## Restart requis

Boot-cache bot ⇒ forbidden_pattern et example ne seront actifs qu'**après redémarrage du bot**.
