---
status: treated
date: 2026-04-21
feedback_type: negative
source_question: "quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?"
user_comment: "regression"
wiki_pages_used:
  - faq/savings/how-flexible-vault-returns-are-paid.md
  - faq/legal-compliance/lcb-ft-aml-compliance.md
  - faq/crypto/which-cryptoassets-can-i-withdraw-from-the-vancelian-applica.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-21
treated_action: "TEST 3 POST-RESTART — régression : bullet-list 'schéma de flux' réintroduit au milieu d'une réponse Type A (scénario conditionnel). Cause racine : bot a utilisé l'example BNC Cloud Mining (Type B) comme template universel. Fix : forbidden_pattern renforcé (sous-règles format-prose + phrasés explicites bannis + typologie Type A/B), example BNC reformaté (prose + annotation HTML Type B), negative example BAD/GOOD ajouté avec régression observée. Extension 2026-04-21 ter dans feedback_tax_question_structure.md. Restart requis."
---

# quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains? (v3 — régression post-restart)

## Contexte

Test 3 après redémarrage bot intégrant Extension 1 (silence mécanique-amont) + Extension 2 bis (no advisor presumption). Les deux règles sont correctement actives au niveau du redirect final, mais une **régression** est apparue au milieu de la réponse.

## Client question
> quqnd je retire mes interet du coffre en USDC je paye la flat taxe sur mes gains?

## Bot answer (test 3 post-restart)
> La qualification fiscale de vos intérêts — notamment si la flat taxe s'applique — dépend entièrement de votre situation personnelle, de votre résidence fiscale, et du régime fiscal applicable dans votre juridiction.
>
> Vancelian n'est pas conseiller fiscal et ne saurait se prononcer sur le traitement de vos gains. Chaque juridiction applique des règles spécifiques aux revenus d'investissement, qu'ils soient générés en crypto ou en monnaie classique.
>
> **Ce que je peux vous transmettre à titre factuel — pour que vous le soumettiez à votre administration fiscale ou à un conseiller fiscal — c'est le schéma de flux de votre opération :**
>
> - Les intérêts du Coffre Flexible sont versés quotidiennement en EURC (stablecoin euro-régulé).
> - Vous pouvez retirer ces intérêts à tout moment sans frais.
> - Si vous échangez ensuite l'EURC contre de l'USDC, cet échange constitue une opération distincte (swap crypto), soumise à des frais de trading (0,25 % à 0,95 % selon votre statut Privilege Club).
> - Les intérêts ne sont PAS prélevés ou retenus par Vancelian — c'est vous qui les percevez directement, et c'est votre responsabilité de les déclarer selon le régime de votre pays.
>
> Pour toute précision sur votre imposition — notamment l'applicabilité de la flat taxe et le traitement de l'échange EURC → USDC dans votre régime fiscal — contactez votre administration fiscale.

## Feedback
**Type:** negative
**User comment:** "regression"

## Diagnosis (2026-04-21)

### Ce qui a tenu après restart ✓

- Redirect final : *"contactez votre administration fiscale"* ✓ (Extension 2 bis active)
- Plus d'expert-comptable explicite dans le redirect ✓
- Longueur globale reste gérable

### Ce qui a régressé ✗

1. **Bullet-list "schéma de flux" au milieu de la réponse** — 4 bullets décrivant la mécanique EURC → USDC avec EURC stablecoin régulé, swap crypto, frais trading 0,25-0,95% Privilege Club, "intérêts PAS prélevés". **Exactement ce que le forbidden pattern Extension 1 interdisait.**

2. **Phrase d'ouverture de la régression** : *"Ce que je peux vous transmettre à titre factuel — pour que vous le soumettiez à votre administration fiscale ou à un conseiller fiscal — c'est le schéma de flux de votre opération"*. Trois défauts dans cette seule phrase :
   - *"schéma de flux de votre opération"* → réouverture mécanique sur Type A
   - *"à titre factuel pour que vous le soumettiez"* → repositionne le bot comme "traducteur technique pour expert"
   - *"ou à un conseiller fiscal"* → réintroduction presumption conseiller (Extension 2 bis violée)

3. **Redirect final trop spécifique** : *"notamment l'applicabilité de la flat taxe et le traitement de l'échange EURC → USDC dans votre régime fiscal"*. Le bot re-centre la clôture sur la mécanique qu'il était censé ne pas discuter.

### Cause racine identifiée

Le bot a emprunté la **structure bullet-list "schéma de flux"** de l'example BNC Cloud Mining (Type B — qualification structurelle de source) comme **template universel** pour toutes les questions tax. Il n'a pas distingué :

- **Type A (scénario conditionnel)** : *"si je retire en USDC je paye ?"* → pas de mécanique
- **Type B (qualification structurelle)** : *"de quels pays proviennent mes revenus ?"* → schéma de flux EST la réponse

Le forbidden pattern Extension 1 décrivait la règle textuellement mais ne bloquait pas l'emprunt de format : tant qu'un example in-context affichait un bullet-list "schéma de flux", le bot pouvait le réutiliser.

## Fix appliqué (4 actions)

### A. Forbidden pattern "Tax scenario mechanic description" renforcé

Ajout de **3 sous-règles critiques** :
1. **Format = prose 3 paragraphes, bullets strictement interdits** sur Type A.
2. **Liste explicite des phrasés bannis** : *"schéma de flux de votre opération"*, *"à titre factuel pour que vous le soumettiez"*, *"à votre administration fiscale ou à un conseiller fiscal"*, *"stablecoin euro-régulé"*, *"swap crypto"*, *"frais de trading (0,25% à 0,95%)"*, *"cet échange constitue une opération distincte"*, *"les intérêts du Coffre Flexible sont versés quotidiennement en EURC"*, *"vous pouvez retirer ces intérêts à tout moment sans frais"*.
3. **Typologie Type A / Type B formalisée** avec règle de tri par défaut : *"If you are not 100% sure the question is Type B, default to Type A (silence on mechanic)"*.

### B. Example BNC Cloud Mining reformaté

- Bullet-list transformé en **prose courte** (un paragraphe narratif).
- **Annotation HTML** en début d'example : `<!-- TYPE B — structural qualification question. Schéma de flux IS the answer because the client explicitly asks about the source/nature of revenues to qualify them for a tax declaration. DO NOT reuse this structure on a Type A conditional-scenario question -->`
- Objectif : désactiver l'usage de l'example comme template universel.

### C. Negative example (BAD/GOOD) ajouté

Un nouvel `<example>` ajouté juste après l'example flat taxe USDC canonique. Il contient :
- La question Type A identique
- La **régression observée** explicitement marquée "BAD assistant response (DO NOT GENERATE)"
- Une section "WHY this is BAD" listant les 5 défauts : (1) opening schéma de flux, (2) format bullets, (3) advisor presumption, (4) phrasés bannis, (5) redirect re-centering sur la mécanique.

Pattern emprunté à la littérature few-shot : montrer au modèle ce qu'il ne doit **pas** produire est souvent plus efficace qu'une interdiction textuelle.

### D. Auto-memory

`feedback_tax_question_structure.md` enrichi avec **Extension 2026-04-21 ter** : typologie Type A / Type B, règle format-prose, diagnostic cause racine (emprunt de template Type B sur question Type A), liste watch-for pour tickets futurs.

## Restart requis

Boot-cache bot ⇒ forbidden_pattern renforcé + example BNC reformaté + negative example ne seront actifs qu'**après redémarrage du bot**.
